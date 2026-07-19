from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from routers import llm_cluster
from services import experiment_config, llm_clusterer


class ExperimentConfigTests(unittest.TestCase):
    def test_boolean_typo_is_rejected(self):
        with self.assertRaises(RuntimeError):
            experiment_config.read_bool_env(
                "LLM_STRICT_MODE",
                environ={"LLM_STRICT_MODE": "tru"},
            )

    def test_backend_name_is_case_sensitive(self):
        with self.assertRaises(RuntimeError):
            experiment_config.validate_backend_name("OLLAMA")

    def test_strict_ollama_does_not_require_cloud_keys(self):
        environ = {
            "LLM_BACKEND": "ollama",
            "OLLAMA_MODEL": "llama3.2:3b",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "LLM_TIMEOUT_SECONDS": "60",
        }
        experiment_config.validate_active_backend_configuration(
            "ollama",
            True,
            environ=environ,
        )

    def test_strict_mode_checks_only_active_backend(self):
        environ = {
            "LLM_BACKEND": "openai",
            "OPENAI_MODEL": "test-model",
            "LLM_TIMEOUT_SECONDS": "60",
        }
        with self.assertRaises(RuntimeError) as raised:
            experiment_config.validate_active_backend_configuration(
                "openai",
                True,
                environ=environ,
            )
        self.assertIn("OPENAI_API_KEY", str(raised.exception))
        self.assertNotIn("ANTHROPIC_API_KEY", str(raised.exception))

    def test_strict_azure_checks_only_azure_configuration(self):
        environ = {
            "LLM_BACKEND": "azure",
            "AZURE_OPENAI_MODEL": "Mistral-Large-3",
            "AZURE_OPENAI_BASE_URL": (
                "https://example.services.ai.azure.com/openai/v1/"
            ),
            "AZURE_OPENAI_MODEL_VERSION": "1",
            "AZURE_OPENAI_DEPLOYMENT_TYPE": "GlobalStandard",
            "LLM_TIMEOUT_SECONDS": "60",
        }
        with self.assertRaises(RuntimeError) as raised:
            experiment_config.validate_active_backend_configuration(
                "azure",
                True,
                environ=environ,
            )

        message = str(raised.exception)
        self.assertTrue(message.endswith("AZURE_OPENAI_API_KEY."))
        self.assertEqual(1, message.count("API_KEY"))
        self.assertNotIn("OLLAMA_MODEL", message)
        self.assertNotIn("ANTHROPIC_API_KEY", message)

    def test_azure_full_chat_completions_url_is_rejected(self):
        with self.assertRaises(RuntimeError) as raised:
            experiment_config.validate_azure_base_url(
                "https://example.services.ai.azure.com/openai/v1/"
                "chat/completions"
            )

        self.assertIn("not /chat/completions", str(raised.exception))

    def test_azure_non_foundry_hostname_is_rejected(self):
        with self.assertRaises(RuntimeError) as raised:
            experiment_config.validate_azure_base_url(
                "https://example.invalid/openai/v1/"
            )

        self.assertIn("Azure Foundry hostname", str(raised.exception))

    def test_timeout_must_be_positive_and_finite(self):
        for value in ("0", "-1", "nan", "infinity", "sixty"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                experiment_config.read_positive_float_env(
                    "LLM_TIMEOUT_SECONDS",
                    default=60,
                    environ={"LLM_TIMEOUT_SECONDS": value},
                )


class LLMClustererStrictTests(unittest.TestCase):
    def test_relevance_request_failure_raises_in_strict_mode(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            side_effect=ConnectionError("offline"),
        ):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.is_relevant("response", "question", strict=True)

        self.assertEqual("LLM_REQUEST_FAILED", raised.exception.code)
        self.assertIsInstance(raised.exception.__cause__, ConnectionError)

    def test_relevance_failure_keeps_fragment_outside_strict_mode(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            side_effect=ConnectionError("offline"),
        ):
            self.assertTrue(
                llm_clusterer.is_relevant("response", "question", strict=False)
            )

    def test_relevance_requires_a_real_boolean(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"relevant": "false"}',
        ):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.is_relevant("response", "question", strict=True)

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)

    def test_relevance_rejects_a_non_object_json_value(self):
        with patch.object(llm_clusterer, "_call_llm", return_value="[]"):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.is_relevant("response", "question", strict=True)

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)

    def test_initial_cluster_does_not_fall_back_to_theme_one(self):
        with patch.object(llm_clusterer, "_call_llm", return_value="not-json"):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.assign_fragment(
                    "response",
                    [],
                    "question",
                    strict=True,
                )

        self.assertEqual("INVALID_LLM_JSON", raised.exception.code)

    def test_new_cluster_requires_label_and_summary(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "new", "label": "Theme"}',
        ):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.assign_fragment(
                    "response",
                    [{"id": 0, "label": "Existing", "summary": "Summary"}],
                    "question",
                    strict=True,
                )

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)

    def test_assignment_prompt_enumerates_valid_integer_ids(self):
        captured_prompt = ""

        def respond(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return '{"action": "assign", "cluster_id": 3}'

        with patch.object(llm_clusterer, "_call_llm", side_effect=respond):
            result = llm_clusterer.assign_fragment(
                "response",
                [
                    {"id": 3, "label": "First", "summary": "Summary"},
                    {"id": 7, "label": "Second", "summary": "Summary"},
                ],
                "question",
                strict=True,
            )

        self.assertEqual({"action": "assign", "cluster_id": 3}, result)
        self.assertIn("Valid existing cluster IDs: [3, 7]", captured_prompt)
        self.assertIn(
            'cluster_id must be exactly one integer from the valid existing cluster IDs',
            captured_prompt,
        )
        self.assertIn("Never invent, infer, or increment a cluster ID", captured_prompt)
        self.assertIn('return action "new"', captured_prompt)
        self.assertIn("do not include cluster_id", captured_prompt)

    def test_assignment_rejects_unknown_cluster_id(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "assign", "cluster_id": 99}',
        ), self.assertLogs(llm_clusterer.logger, level="WARNING") as captured:
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.assign_fragment(
                    "response",
                    [{"id": 0, "label": "Existing", "summary": "Summary"}],
                    "question",
                    strict=True,
                )

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)
        self.assertIn("cluster_id=99", str(raised.exception))
        self.assertIn("valid_cluster_ids=[0]", str(raised.exception))
        self.assertIn("raw_response", captured.output[0])
        self.assertIn("cluster_id\": 99", captured.output[0])

    def test_assignment_rejects_a_float_cluster_id(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "assign", "cluster_id": 0.5}',
        ):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.assign_fragment(
                    "response",
                    [{"id": 0, "label": "Existing", "summary": "Summary"}],
                    "question",
                    strict=True,
                )

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)

    def test_assignment_accepts_a_decimal_string_cluster_id(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "assign", "cluster_id": "0"}',
        ):
            result = llm_clusterer.assign_fragment(
                "response",
                [{"id": 0, "label": "Existing", "summary": "Summary"}],
                "question",
                strict=True,
            )

        self.assertEqual({"action": "assign", "cluster_id": 0}, result)

    def test_assignment_accepts_lossless_decimal_cluster_ids(self):
        cluster = [{"id": 0, "label": "Existing", "summary": "Summary"}]
        for cluster_id in ("0.0", 0.0):
            with self.subTest(cluster_id=cluster_id), patch.object(
                llm_clusterer,
                "_call_llm",
                return_value=json.dumps({"action": "assign", "cluster_id": cluster_id}),
            ):
                result = llm_clusterer.assign_fragment(
                    "response",
                    cluster,
                    "question",
                    strict=True,
                )
                self.assertEqual({"action": "assign", "cluster_id": 0}, result)

    def test_assignment_accepts_a_singleton_cluster_id_list(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "assign", "cluster_id": [0]}',
        ):
            result = llm_clusterer.assign_fragment(
                "response",
                [{"id": 0, "label": "Existing", "summary": "Summary"}],
                "question",
                strict=True,
            )

        self.assertEqual({"action": "assign", "cluster_id": 0}, result)

    def test_assignment_rejects_an_ambiguous_cluster_id_list(self):
        with patch.object(
            llm_clusterer,
            "_call_llm",
            return_value='{"action": "assign", "cluster_id": [0, 1]}',
        ):
            with self.assertRaises(llm_clusterer.LLMStrictModeError) as raised:
                llm_clusterer.assign_fragment(
                    "response",
                    [
                        {"id": 0, "label": "First", "summary": "Summary"},
                        {"id": 1, "label": "Second", "summary": "Summary"},
                    ],
                    "question",
                    strict=True,
                )

        self.assertEqual("INVALID_LLM_RESPONSE", raised.exception.code)
        self.assertIn("2 items", str(raised.exception))

    def test_non_strict_assignment_retains_legacy_cluster_zero_fallback(self):
        with patch.object(llm_clusterer, "_call_llm", return_value="not-json"):
            result = llm_clusterer.assign_fragment(
                "response",
                [{"id": 7, "label": "Existing", "summary": "Summary"}],
                "question",
                strict=False,
            )

        self.assertEqual({"action": "assign", "cluster_id": 7}, result)


class PipelineRunStateTests(unittest.TestCase):
    def _database(self):
        return {
            "documents": MagicMock(),
            "fragments": MagicMock(),
            "clusters": MagicMock(),
            "pipelineRuns": MagicMock(),
        }

    def test_start_and_finish_record_explicit_states(self):
        db = self._database()
        doc_oid = ObjectId()
        run_oid = ObjectId()
        db["documents"].find_one.return_value = {"name": "P1_task1_batchA"}
        db["pipelineRuns"].insert_one.return_value = SimpleNamespace(
            inserted_id=run_oid
        )
        db["pipelineRuns"].update_one.return_value = SimpleNamespace(
            matched_count=1
        )
        request = llm_cluster.LLMClusterRequest(
            doc_id=str(doc_oid),
            research_question="question",
        )

        with patch.object(llm_cluster, "_get_code_version", return_value="abc123"):
            actual_run_oid = llm_cluster._start_pipeline_run(
                db,
                request,
                doc_oid,
                True,
            )

        self.assertEqual(run_oid, actual_run_oid)
        inserted = db["pipelineRuns"].insert_one.call_args.args[0]
        self.assertEqual("running", inserted["status"])
        self.assertTrue(inserted["strict_mode"])

        llm_cluster._finish_pipeline_run(db, run_oid, doc_oid, True)
        completed = db["pipelineRuns"].update_one.call_args.args[1]["$set"]
        self.assertEqual("completed", completed["status"])
        self.assertIn("finished_at", completed)

    def test_start_records_azure_deployment_metadata_and_parameters(self):
        db = self._database()
        doc_oid = ObjectId()
        run_oid = ObjectId()
        db["documents"].find_one.return_value = {"name": "P1_task1_batchA"}
        db["pipelineRuns"].insert_one.return_value = SimpleNamespace(
            inserted_id=run_oid
        )
        request = llm_cluster.LLMClusterRequest(
            doc_id=str(doc_oid),
            research_question="question",
        )
        run_parameters = {
            "timeout_seconds": 60,
            "max_retries": 0,
            "temperature": 0.2,
            "max_tokens": None,
            "provider_protocol": "openai_v1",
            "model_version": "1",
            "deployment_type": "GlobalStandard",
        }

        with patch.object(
            llm_cluster,
            "_get_code_version",
            return_value="abc123",
        ), patch.object(
            llm_cluster.llm_provider,
            "get_model_metadata",
            return_value=("azure", "Mistral-Large-3"),
        ), patch.object(
            llm_cluster.llm_provider,
            "get_run_parameters",
            return_value=run_parameters,
        ):
            llm_cluster._start_pipeline_run(
                db,
                request,
                doc_oid,
                True,
            )

        inserted = db["pipelineRuns"].insert_one.call_args.args[0]
        self.assertEqual("azure", inserted["llm_backend"])
        self.assertEqual("Mistral-Large-3", inserted["model_name"])
        self.assertEqual(
            {"column_filters": {}, **run_parameters},
            inserted["params"],
        )

    def test_mid_run_llm_failure_does_not_enter_persistence(self):
        db = self._database()
        doc_oid = ObjectId()
        run_oid = ObjectId()
        fragments = [
            {
                "_id": ObjectId(),
                "name": f"R{i + 1}",
                "redacted_text": f"response {i + 1}",
                "embedding": [float(i + 1)],
                "row_data": {},
            }
            for i in range(12)
        ]
        db["fragments"].find.return_value = fragments
        db["pipelineRuns"].update_one.return_value = SimpleNamespace(
            matched_count=1
        )
        request = llm_cluster.LLMClusterRequest(
            doc_id=str(doc_oid),
            research_question="question",
        )
        call_count = 0

        def relevance_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 11:
                error = llm_clusterer.LLMStrictModeError(
                    "LLM_REQUEST_FAILED",
                    "LLM relevance filtering failed.",
                )
                error.__cause__ = ConnectionError("offline")
                raise error
            return True

        with patch.object(
            llm_clusterer,
            "is_relevant",
            side_effect=relevance_side_effect,
        ), patch.object(llm_cluster.logger, "exception"):
            events = [
                json.loads(line)
                for line in llm_cluster._run_pipeline(
                    request,
                    db,
                    doc_oid,
                    run_oid,
                    True,
                )
            ]

        self.assertEqual(11, call_count)
        self.assertEqual(10, sum(event["event"] == "filter" for event in events))
        self.assertEqual("error", events[-1]["event"])
        db["clusters"].delete_many.assert_not_called()
        db["clusters"].insert_one.assert_not_called()
        db["fragments"].update_many.assert_not_called()

        failed_update = db["pipelineRuns"].update_one.call_args.args[1]
        failed = failed_update["$set"]
        self.assertEqual("failed", failed["status"])
        self.assertEqual("relevance_filter", failed["failure_stage"])
        self.assertEqual("LLM_REQUEST_FAILED", failed["failure_code"])
        self.assertEqual("ConnectionError", failed["failure_type"])
        self.assertEqual(fragments[10]["_id"], failed["failure_fragment_id"])
        self.assertIn("failed_at", failed)
        self.assertNotIn("finished_at", failed)

    def test_content_filter_failure_is_recorded_without_persistence(self):
        db = self._database()
        doc_oid = ObjectId()
        run_oid = ObjectId()
        fragment = {
            "_id": ObjectId(),
            "name": "R1",
            "redacted_text": "response",
            "embedding": [1.0],
            "row_data": {},
        }
        db["fragments"].find.return_value = [fragment]
        db["pipelineRuns"].update_one.return_value = SimpleNamespace(
            matched_count=1
        )
        request = llm_cluster.LLMClusterRequest(
            doc_id=str(doc_oid),
            research_question="question",
        )
        error = llm_clusterer.LLMStrictModeError(
            "CONTENT_FILTERED",
            "Azure content filtering blocked the request or response.",
        )

        with patch.object(
            llm_clusterer,
            "is_relevant",
            side_effect=error,
        ), patch.object(llm_cluster.logger, "exception"):
            events = [
                json.loads(line)
                for line in llm_cluster._run_pipeline(
                    request,
                    db,
                    doc_oid,
                    run_oid,
                    True,
                )
            ]

        self.assertEqual("error", events[-1]["event"])
        db["clusters"].delete_many.assert_not_called()
        db["clusters"].insert_one.assert_not_called()
        db["fragments"].update_many.assert_not_called()
        failed = db["pipelineRuns"].update_one.call_args.args[1]["$set"]
        self.assertEqual("failed", failed["status"])
        self.assertEqual("CONTENT_FILTERED", failed["failure_code"])
        self.assertEqual("relevance_filter", failed["failure_stage"])
        self.assertEqual(fragment["_id"], failed["failure_fragment_id"])
        self.assertNotIn("finished_at", failed)


if __name__ == "__main__":
    unittest.main()
