from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi import HTTPException


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from routers import cluster, feedback, label, llm_cluster, suggest
from services import experiment_config


class LabelFreezeConfigurationTests(unittest.TestCase):
    def test_freeze_boolean_typo_is_rejected(self):
        with self.assertRaises(RuntimeError):
            experiment_config.read_bool_env(
                "FREEZE_LABELS",
                environ={"FREEZE_LABELS": "enabled"},
            )


class FrozenMutationRouteTests(unittest.TestCase):
    def _assert_locked(self, callback, get_db_mock, operation: str):
        with patch.object(experiment_config, "FREEZE_LABELS", True):
            with self.assertRaises(HTTPException) as raised:
                callback()

        self.assertEqual(423, raised.exception.status_code)
        self.assertEqual("labels_frozen", raised.exception.detail["error"])
        self.assertEqual(operation, raised.exception.detail["operation"])
        get_db_mock.assert_not_called()

    def test_cluster_run_is_locked_before_database_access(self):
        request = cluster.ClusterRequest(doc_id=str(ObjectId()))
        with patch.object(cluster, "get_db") as get_db_mock:
            self._assert_locked(
                lambda: cluster.run_clustering(request),
                get_db_mock,
                "cluster_run",
            )

    def test_label_clusters_is_locked_before_database_access(self):
        request = label.LabelRequest(cluster_ids=[])
        with patch.object(label, "get_db") as get_db_mock:
            self._assert_locked(
                lambda: label.label_clusters(request),
                get_db_mock,
                "label_clusters",
            )

    def test_save_manual_clusters_is_locked_before_database_access(self):
        request = suggest.SaveRequest(doc_id=str(ObjectId()), groups=[])
        with patch.object(suggest, "get_db") as get_db_mock:
            self._assert_locked(
                lambda: suggest.save_manual_clusters(request),
                get_db_mock,
                "save_manual_clusters",
            )

    def test_llm_cluster_run_remains_available_when_labels_are_frozen(self):
        doc_oid = ObjectId()
        run_oid = ObjectId()
        database = MagicMock()
        request = llm_cluster.LLMClusterRequest(
            doc_id=str(doc_oid),
            research_question="question",
        )

        with patch.object(
            experiment_config,
            "FREEZE_LABELS",
            True,
        ), patch.object(
            experiment_config,
            "LLM_STRICT_MODE",
            True,
        ), patch.object(
            llm_cluster,
            "get_db",
            return_value=database,
        ), patch.object(
            llm_cluster,
            "_start_pipeline_run",
            return_value=run_oid,
        ) as start_run, patch.object(
            experiment_config,
            "validate_active_backend_configuration",
        ), patch.object(
            llm_cluster,
            "_run_pipeline",
            return_value=iter(['{"event": "done"}\n']),
        ):
            response = llm_cluster.llm_cluster_run(request)

        self.assertEqual(200, response.status_code)
        start_run.assert_called_once_with(database, request, doc_oid, True)


class FrozenReclusterTests(unittest.TestCase):
    def _database(self):
        doc_oid = ObjectId()
        frag_oid = ObjectId()
        from_oid = ObjectId()
        to_oid = ObjectId()
        database = {
            "fragments": MagicMock(),
            "clusters": MagicMock(),
            "clusterFeedback": MagicMock(),
        }
        database["fragments"].find_one.return_value = {
            "_id": frag_oid,
            "docid": doc_oid,
            "cluster_id": from_oid,
        }
        database["clusters"].find_one.side_effect = [
            {"_id": from_oid, "survey_doc_id": doc_oid},
            {"_id": to_oid, "survey_doc_id": doc_oid},
        ]
        database["fragments"].find.return_value = []
        request = feedback.FeedbackRequest(
            fragment_id=str(frag_oid),
            from_cluster_id=str(from_oid),
            to_cluster_id=str(to_oid),
            participant_id="p1",
        )
        return database, request, frag_oid, from_oid, to_oid

    def test_frozen_recluster_moves_and_records_without_labelling(self):
        database, request, frag_oid, from_oid, to_oid = self._database()

        with patch.object(
            experiment_config,
            "FREEZE_LABELS",
            True,
        ), patch.object(
            feedback,
            "get_db",
            return_value=database,
        ), patch.object(
            feedback.labeller,
            "label_cluster",
        ) as label_cluster:
            response = feedback.record_feedback(request)

        self.assertEqual({"ok": True, "labels_frozen": True}, response)
        label_cluster.assert_not_called()
        database["clusterFeedback"].insert_one.assert_called_once()
        record = database["clusterFeedback"].insert_one.call_args.args[0]
        self.assertEqual("P1", record["participant_id"])
        self.assertEqual(frag_oid, record["fragment_id"])
        self.assertEqual(from_oid, record["from_cluster_id"])
        self.assertEqual(to_oid, record["to_cluster_id"])
        database["fragments"].update_one.assert_called_once_with(
            {"_id": frag_oid},
            {"$set": {"feedback_cluster_id": to_oid, "cluster_id": to_oid}},
        )
        self.assertEqual(2, database["clusters"].update_one.call_count)
        self.assertEqual(2, database["clusters"].find_one.call_count)
        for update_call in database["clusters"].update_one.call_args_list:
            changed_fields = update_call.args[1].get("$set", {})
            self.assertNotIn("label", changed_fields)
            self.assertNotIn("summary", changed_fields)

    def test_unfrozen_recluster_retains_runtime_labelling(self):
        database, request, _frag_oid, from_oid, to_oid = self._database()
        doc_oid = database["fragments"].find_one.return_value["docid"]
        database["clusters"].find_one.side_effect = [
            {"_id": from_oid, "survey_doc_id": doc_oid},
            {"_id": to_oid, "survey_doc_id": doc_oid},
            {"_id": from_oid, "survey_doc_id": doc_oid},
            {"_id": to_oid, "survey_doc_id": doc_oid},
        ]
        database["fragments"].find.side_effect = [
            [],
            [{"redacted_text": "from sample"}],
            [{"redacted_text": "to sample"}],
        ]

        with patch.object(
            experiment_config,
            "FREEZE_LABELS",
            False,
        ), patch.object(
            feedback,
            "get_db",
            return_value=database,
        ), patch.object(
            feedback.labeller,
            "label_cluster",
            side_effect=[
                {"label": "From", "summary": "From summary"},
                {"label": "To", "summary": "To summary"},
            ],
        ) as label_cluster:
            response = feedback.record_feedback(request)

        self.assertEqual({"ok": True, "labels_frozen": False}, response)
        self.assertEqual(2, label_cluster.call_count)
        self.assertEqual(4, database["clusters"].update_one.call_count)


if __name__ == "__main__":
    unittest.main()
