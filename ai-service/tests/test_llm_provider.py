from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import BadRequestError


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from services import labeller, llm_clusterer, llm_provider, llm_schemas
from routers import llm_cluster


class LLMProviderConfigurationTests(unittest.TestCase):
    def test_ollama_configuration_preserves_legacy_timeout(self):
        config = llm_provider.get_active_backend_config({
            "LLM_BACKEND": "ollama",
            "OLLAMA_MODEL": "llama3.2:3b",
            "OLLAMA_BASE_URL": "http://localhost:11434/",
        })

        self.assertEqual("ollama", config.backend)
        self.assertEqual("llama3.2:3b", config.model_name)
        self.assertEqual("http://localhost:11434", config.base_url)
        self.assertEqual(60, config.timeout_seconds)

    def test_openai_configuration_uses_shared_timeout(self):
        config = llm_provider.get_active_backend_config({
            "LLM_BACKEND": "openai",
            "OPENAI_MODEL": "test-model",
            "OPENAI_API_KEY": "test-key",
            "LLM_TIMEOUT_SECONDS": "60",
        })

        self.assertEqual("openai", config.backend)
        self.assertEqual("test-model", config.model_name)
        self.assertEqual(60, config.timeout_seconds)

    def test_azure_configuration_keeps_deployment_provenance(self):
        config = llm_provider.get_active_backend_config({
            "LLM_BACKEND": "azure",
            "AZURE_OPENAI_MODEL": "Mistral-Large-3",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_BASE_URL": (
                "https://example.services.ai.azure.com/openai/v1/"
            ),
            "AZURE_OPENAI_MODEL_VERSION": "1",
            "AZURE_OPENAI_DEPLOYMENT_TYPE": "GlobalStandard",
            "LLM_TIMEOUT_SECONDS": "60",
            "LLM_TEMPERATURE": "0",
            "LLM_SEED": "42",
            "LLM_MAX_TOKENS": "1024",
        })

        self.assertEqual("azure", config.backend)
        self.assertEqual("Mistral-Large-3", config.model_name)
        self.assertEqual("1", config.model_version)
        self.assertEqual("GlobalStandard", config.deployment_type)
        self.assertEqual(60, config.timeout_seconds)
        self.assertEqual(0, config.temperature)
        self.assertEqual(42, config.seed)
        self.assertEqual(1024, config.max_tokens)

    def test_call_text_dispatches_to_selected_backend(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="test-model",
            base_url="http://localhost:11434",
            timeout_seconds=60,
        )
        with patch.object(
            llm_provider,
            "get_active_backend_config",
            return_value=config,
        ), patch.object(
            llm_provider,
            "_call_ollama",
            return_value="result",
        ) as call:
            result = llm_provider.call_text("prompt", purpose="clustering")

        self.assertEqual("result", result)
        call.assert_called_once_with(
            "prompt",
            config,
            "clustering",
            response_schema=None,
            schema_name=None,
        )

    def test_openai_client_disables_hidden_retries(self):
        config = llm_provider.LLMBackendConfig(
            backend="openai",
            model_name="test-model",
            api_key="test-key",
            timeout_seconds=60,
        )
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="response"))
            ]
        )

        with patch("openai.OpenAI", return_value=client) as constructor:
            result = llm_provider._call_openai(
                "prompt",
                config,
                "clustering",
            )

        self.assertEqual("response", result)
        constructor.assert_called_once_with(
            api_key="test-key",
            timeout=60,
            max_retries=0,
        )
        client.chat.completions.create.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0.2,
        )

    def test_anthropic_client_uses_shared_timeout_without_retries(self):
        config = llm_provider.LLMBackendConfig(
            backend="anthropic",
            model_name="test-model",
            api_key="test-key",
            timeout_seconds=60,
        )
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="response")]
        )

        with patch("anthropic.Anthropic", return_value=client) as constructor:
            result = llm_provider._call_anthropic(
                "prompt",
                config,
                "clustering",
            )

        self.assertEqual("response", result)
        constructor.assert_called_once_with(
            api_key="test-key",
            timeout=60,
            max_retries=0,
        )
        client.messages.create.assert_called_once_with(
            model="test-model",
            max_tokens=512,
            messages=[{"role": "user", "content": "prompt"}],
        )

    def test_azure_uses_openai_v1_base_url_and_deployment_name(self):
        config = llm_provider.LLMBackendConfig(
            backend="azure",
            model_name="Mistral-Large-3",
            api_key="test-key",
            base_url="https://example.services.ai.azure.com/openai/v1/",
            timeout_seconds=60,
            model_version="1",
            deployment_type="GlobalStandard",
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content="response"),
            )]
        )

        with patch("openai.OpenAI", return_value=client) as constructor:
            result = llm_provider._call_azure(
                "prompt",
                config,
                "clustering",
            )

        self.assertEqual("response", result)
        constructor.assert_called_once_with(
            api_key="test-key",
            base_url="https://example.services.ai.azure.com/openai/v1/",
            timeout=60,
            max_retries=0,
        )
        client.chat.completions.create.assert_called_once_with(
            model="Mistral-Large-3",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0,
            seed=42,
            max_tokens=1024,
        )

    def test_azure_structured_output_uses_strict_json_schema(self):
        config = llm_provider.LLMBackendConfig(
            backend="azure",
            model_name="Mistral-Large-3",
            api_key="test-key",
            base_url="https://example.services.ai.azure.com/openai/v1/",
            timeout_seconds=60,
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        spec = llm_schemas.build_assignment_spec([0])
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content="response"),
            )]
        )

        with patch("openai.OpenAI", return_value=client):
            result = llm_provider._call_azure(
                "prompt",
                config,
                "clustering",
                response_schema=spec.schema,
                schema_name=spec.name,
            )

        self.assertEqual("response", result)
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual({
            "type": "json_schema",
            "json_schema": {
                "name": spec.name,
                "strict": True,
                "schema": spec.schema,
            },
        }, request["response_format"])

    def test_ollama_receives_the_frozen_sampling_profile(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="llama3.2:3b",
            base_url="http://localhost:11434",
            timeout_seconds=60,
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        response = MagicMock()
        response.json.return_value = {"response": "result"}
        client = MagicMock()
        client.post.return_value = response
        context = MagicMock()
        context.__enter__.return_value = client

        with patch("httpx.Client", return_value=context) as constructor:
            result = llm_provider._call_ollama(
                "prompt",
                config,
                "clustering",
            )

        self.assertEqual("result", result)
        constructor.assert_called_once_with(timeout=60)
        client.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": "prompt",
                "stream": False,
                "options": {
                    "temperature": 0,
                    "seed": 42,
                    "num_predict": 1024,
                },
            },
        )
        response.raise_for_status.assert_called_once_with()

    def test_ollama_structured_output_uses_format(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="llama3.2:3b",
            base_url="http://localhost:11434",
            timeout_seconds=60,
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        spec = llm_schemas.build_assignment_spec([0])
        response = MagicMock()
        response.json.return_value = {"response": "result"}
        client = MagicMock()
        client.post.return_value = response
        context = MagicMock()
        context.__enter__.return_value = client

        with patch("httpx.Client", return_value=context):
            result = llm_provider._call_ollama(
                "prompt",
                config,
                "clustering",
                response_schema=spec.schema,
                schema_name=spec.name,
            )

        self.assertEqual("result", result)
        request_body = client.post.call_args.kwargs["json"]
        self.assertEqual(spec.schema, request_body["format"])

    def test_call_text_requires_schema_and_name_together(self):
        with self.assertRaises(ValueError):
            llm_provider.call_text(
                "prompt",
                purpose="clustering",
                response_schema={"type": "object"},
            )

    def test_anthropic_rejects_required_schema(self):
        config = llm_provider.LLMBackendConfig(
            backend="anthropic",
            model_name="test-model",
        )
        with self.assertRaises(llm_provider.LLMProviderError) as raised:
            llm_provider._call_anthropic(
                "prompt",
                config,
                "clustering",
                response_schema={"type": "object"},
                schema_name="test_schema",
            )

        self.assertEqual("SCHEMA_UNSUPPORTED", raised.exception.code)

    def test_ollama_without_sampling_profile_preserves_legacy_request(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="llama3.2:3b",
            base_url="http://localhost:11434",
            timeout_seconds=60,
        )
        response = MagicMock()
        response.json.return_value = {"response": "result"}
        client = MagicMock()
        client.post.return_value = response
        context = MagicMock()
        context.__enter__.return_value = client

        with patch("httpx.Client", return_value=context):
            result = llm_provider._call_ollama(
                "prompt",
                config,
                "clustering",
            )

        self.assertEqual("result", result)
        client.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": "prompt",
                "stream": False,
            },
        )
        response.raise_for_status.assert_called_once_with()

    def test_azure_http_400_content_filter_has_safe_error_code(self):
        config = llm_provider.LLMBackendConfig(
            backend="azure",
            model_name="Mistral-Large-3",
            api_key="test-key",
            base_url="https://example.services.ai.azure.com/openai/v1/",
            timeout_seconds=60,
        )
        request = httpx.Request(
            "POST",
            "https://example.services.ai.azure.com/openai/v1/chat/completions",
        )
        response = httpx.Response(400, request=request)
        provider_error = BadRequestError(
            "sensitive provider response",
            response=response,
            body={
                "error": {
                    "code": "content_filter",
                    "innererror": {
                        "code": "ResponsibleAIPolicyViolation"
                    },
                }
            },
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = provider_error

        with patch("openai.OpenAI", return_value=client):
            with self.assertRaises(llm_provider.LLMProviderError) as raised:
                llm_provider._call_azure("prompt", config, "clustering")

        self.assertEqual("CONTENT_FILTERED", raised.exception.code)
        self.assertNotIn("sensitive", str(raised.exception))

    def test_azure_http_200_content_filter_has_safe_error_code(self):
        config = llm_provider.LLMBackendConfig(
            backend="azure",
            model_name="Mistral-Large-3",
            api_key="test-key",
            base_url="https://example.services.ai.azure.com/openai/v1/",
            timeout_seconds=60,
        )
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="content_filter",
                message=SimpleNamespace(content=None),
            )]
        )

        with patch("openai.OpenAI", return_value=client):
            with self.assertRaises(llm_provider.LLMProviderError) as raised:
                llm_provider._call_azure("prompt", config, "clustering")

        self.assertEqual("CONTENT_FILTERED", raised.exception.code)

    def test_content_filter_code_is_preserved_by_strict_mode(self):
        provider_error = llm_provider.LLMProviderError(
            "CONTENT_FILTERED",
            "Azure content filtering blocked the request or response.",
        )

        strict_error = llm_clusterer._strict_call_error(
            "relevance filtering",
            provider_error,
        )

        self.assertEqual("CONTENT_FILTERED", strict_error.code)
        self.assertNotIn("prompt", str(strict_error))

    def test_azure_run_parameters_include_deployment_provenance(self):
        config = llm_provider.LLMBackendConfig(
            backend="azure",
            model_name="Mistral-Large-3",
            timeout_seconds=60,
            model_version="1",
            deployment_type="GlobalStandard",
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        with patch.object(
            llm_provider,
            "get_active_backend_config",
            return_value=config,
        ):
            parameters = llm_provider.get_run_parameters(
                schema_enforced=True,
            )

        self.assertEqual(60, parameters["timeout_seconds"])
        self.assertEqual(0, parameters["max_retries"])
        self.assertEqual(0, parameters["temperature"])
        self.assertEqual(42, parameters["seed"])
        self.assertEqual("best_effort_beta", parameters["seed_semantics"])
        self.assertEqual(1024, parameters["max_tokens"])
        self.assertEqual("openai_v1", parameters["provider_protocol"])
        self.assertEqual("1", parameters["model_version"])
        self.assertEqual("GlobalStandard", parameters["deployment_type"])
        self.assertTrue(parameters["schema_enforced"])
        self.assertEqual(
            llm_schemas.SCHEMA_VERSION,
            parameters["schema_version"],
        )
        self.assertEqual(
            "openai_chat_completions_response_format_json_schema",
            parameters["schema_transport"],
        )
        self.assertTrue(parameters["schema_dynamic_cluster_id_enum"])

    def test_ollama_run_parameters_record_provider_seed_semantics(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="llama3.2:3b",
            timeout_seconds=60,
            temperature=0,
            seed=42,
            max_tokens=1024,
        )
        with patch.object(
            llm_provider,
            "get_active_backend_config",
            return_value=config,
        ):
            parameters = llm_provider.get_run_parameters(
                schema_enforced=True,
            )

        self.assertEqual(0, parameters["temperature"])
        self.assertEqual(42, parameters["seed"])
        self.assertEqual("provider_supported", parameters["seed_semantics"])
        self.assertEqual(1024, parameters["max_tokens"])
        self.assertTrue(parameters["schema_enforced"])
        self.assertEqual(
            "ollama_api_generate_format",
            parameters["schema_transport"],
        )

    def test_non_schema_run_parameters_are_explicitly_disabled(self):
        config = llm_provider.LLMBackendConfig(
            backend="ollama",
            model_name="llama3.2:3b",
            timeout_seconds=60,
        )
        with patch.object(
            llm_provider,
            "get_active_backend_config",
            return_value=config,
        ):
            parameters = llm_provider.get_run_parameters(
                schema_enforced=False,
            )

        self.assertFalse(parameters["schema_enforced"])
        self.assertIsNone(parameters["schema_version"])
        self.assertIsNone(parameters["schema_transport"])
        self.assertFalse(parameters["schema_dynamic_cluster_id_enum"])


class SharedProviderCallSiteTests(unittest.TestCase):
    def test_clusterer_uses_shared_provider(self):
        with patch.object(
            llm_provider,
            "call_text",
            return_value="response",
        ) as call:
            result = llm_clusterer._call_llm("prompt")

        self.assertEqual("response", result)
        call.assert_called_once_with("prompt", purpose="clustering")

    def test_labeller_uses_shared_provider(self):
        with patch.object(
            llm_provider,
            "call_text",
            return_value='{"label": "Theme", "summary": "Summary"}',
        ) as call:
            result = labeller.label_cluster(["response"])

        self.assertEqual({"label": "Theme", "summary": "Summary"}, result)
        call.assert_called_once_with(
            labeller._build_prompt(["response"]),
            purpose="labelling",
        )

    def test_pipeline_metadata_uses_shared_provider(self):
        with patch.object(
            llm_provider,
            "get_model_metadata",
            return_value=("ollama", "llama3.2:3b"),
        ) as metadata:
            result = llm_cluster._get_model_metadata()

        self.assertEqual(("ollama", "llama3.2:3b"), result)
        metadata.assert_called_once_with()

    def test_pipeline_failure_message_redacts_provider_secret(self):
        with patch.object(
            llm_provider,
            "get_sensitive_values",
            return_value=("secret-value",),
        ):
            result = llm_cluster._safe_failure_message(
                RuntimeError("request failed for secret-value")
            )

        self.assertEqual("request failed for [REDACTED]", result)


class PromptFreezeTests(unittest.TestCase):
    G_ERA_BOUNDARY_COMMIT = (
        "f7421cf44cdbc075cde1fd9e7904c81a345f0519"
    )
    G_ERA_EXPECTED_HASHES = {
        "relevance": "189d583cbd52e0839250fafe3cf0e73f22cf27b7cc13344178bf10435b4ab1a4",
        "initial_assignment": "d8ca347ba17007747c8ca0783edde2e2983dc70f19d6e0749474511972bef06b",
        "existing_assignment": "7bb5a5d9f0a70965314a1bc3a642f97c5410dc37c8ccab52b04926e134f7343d",
        "labelling": "f3c5e4b0e97cbfe06e90b7b83d28cd0c2fb50d00ec9fb181515e9467bc395536",
    }
    # Replaced after the first implementation commit so the final G2
    # candidate records the exact commit at which this prompt era begins.
    G2_ERA_BOUNDARY_COMMIT = "PENDING_IMPLEMENTATION_COMMIT"
    G2_ERA_EXPECTED_HASHES = {
        "relevance": "189d583cbd52e0839250fafe3cf0e73f22cf27b7cc13344178bf10435b4ab1a4",
        "initial_assignment": "d8ca347ba17007747c8ca0783edde2e2983dc70f19d6e0749474511972bef06b",
        "existing_assignment": "992487fd59b21235eea7cc96ea6d539b4ff06706e22fab3208afd6862093664f",
        "labelling": "f3c5e4b0e97cbfe06e90b7b83d28cd0c2fb50d00ec9fb181515e9467bc395536",
    }

    @staticmethod
    def _digest(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def _capture_prompt(call, response: str) -> str:
        prompts: list[str] = []
        with patch.object(
            llm_clusterer,
            "_call_llm",
            side_effect=lambda prompt, **_kwargs: (
                prompts.append(prompt) or response
            ),
        ):
            call()
        return prompts[0]

    def test_current_prompts_match_g2_byte_hashes(self):
        prompts = {
            "relevance": self._capture_prompt(
                lambda: llm_clusterer.is_relevant("response", "question"),
                '{"relevant": true}',
            ),
            "initial_assignment": self._capture_prompt(
                lambda: llm_clusterer.assign_fragment(
                    "response", [], "question"
                ),
                '{"label": "Theme", "summary": "Summary"}',
            ),
            "existing_assignment": self._capture_prompt(
                lambda: llm_clusterer.assign_fragment(
                    "response",
                    [{"id": 0, "label": "Theme", "summary": "Summary"}],
                    "question",
                ),
                '{"decision": {"action": "assign", "cluster_id": 0}}',
            ),
            "labelling": labeller._build_prompt(["response 1", "response 2"]),
        }

        actual = {
            name: self._digest(prompt)
            for name, prompt in prompts.items()
        }
        self.assertEqual(self.G2_ERA_EXPECTED_HASHES, actual)

    def test_g_era_prompt_hash_record_is_preserved(self):
        self.assertEqual(
            "7bb5a5d9f0a70965314a1bc3a642f97c5410dc37c8ccab52b04926e134f7343d",
            self.G_ERA_EXPECTED_HASHES["existing_assignment"],
        )
        self.assertNotEqual(
            self.G_ERA_EXPECTED_HASHES["existing_assignment"],
            self.G2_ERA_EXPECTED_HASHES["existing_assignment"],
        )
        self.assertEqual(40, len(self.G_ERA_BOUNDARY_COMMIT))


if __name__ == "__main__":
    unittest.main()
