"""Manual, secret-safe G2 structured-output capability probe.

Daily tests do not call live providers. Run explicitly with ``--live`` to
exercise the same ``llm_provider.call_text`` path used by the pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from dotenv import find_dotenv, load_dotenv


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from services import llm_provider, llm_schemas  # noqa: E402


EXPECTED_DIGESTS = {
    "llama": (
        "llama3.2:3b",
        "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72",
    ),
    "qwen": (
        "qwen2.5:3b",
        "357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b",
    ),
}
SYNTHETIC_PROMPT = (
    "Return an assignment decision. You must assign to cluster_id 1 and "
    "must not create a new cluster."
)


def validate_probe_response(instance: object) -> str:
    if not isinstance(instance, dict) or set(instance) != {"decision"}:
        raise ValueError("ROOT_SHAPE")
    decision = instance["decision"]
    if not isinstance(decision, dict):
        raise ValueError("DECISION_TYPE")
    if decision.get("action") == "assign":
        if set(decision) != {"action", "cluster_id"}:
            raise ValueError("ASSIGN_SHAPE")
        if type(decision["cluster_id"]) is not int:
            raise ValueError("ASSIGN_TYPE")
        if decision["cluster_id"] != 0:
            raise ValueError("ASSIGN_ENUM")
        return "ASSIGN_VALID"
    if decision.get("action") == "new":
        if set(decision) != {"action", "label", "summary"}:
            raise ValueError("NEW_SHAPE")
        if not isinstance(decision["label"], str):
            raise ValueError("NEW_LABEL_TYPE")
        if not isinstance(decision["summary"], str):
            raise ValueError("NEW_SUMMARY_TYPE")
        return "NEW_VALID"
    raise ValueError("ACTION_ENUM")


def _safe_error(exc: Exception) -> dict[str, object]:
    return {
        "exception_type": type(exc).__name__,
        "status_code": getattr(exc, "status_code", None),
        "provider_code": getattr(exc, "code", None),
    }


def _probe_environment(model_key: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update({
        "LLM_TIMEOUT_SECONDS": "60",
        "LLM_TEMPERATURE": "0",
        "LLM_SEED": "42",
        "LLM_MAX_TOKENS": "1024",
    })
    if model_key in EXPECTED_DIGESTS:
        model_name, _ = EXPECTED_DIGESTS[model_key]
        environment.update({
            "LLM_BACKEND": "ollama",
            "OLLAMA_MODEL": model_name,
            "OLLAMA_BASE_URL": "http://localhost:11434",
        })
    else:
        environment.update({
            "LLM_BACKEND": "azure",
            "AZURE_OPENAI_MODEL": "Mistral-Large-3",
        })
    return environment


def _verify_ollama_digest(model_key: str, environment: dict[str, str]) -> bool:
    import httpx

    model_name, expected_digest = EXPECTED_DIGESTS[model_key]
    base_url = environment["OLLAMA_BASE_URL"].rstrip("/")
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{base_url}/api/tags")
        response.raise_for_status()
    digest = next(
        (
            model.get("digest")
            for model in response.json().get("models", [])
            if model.get("name") == model_name
        ),
        None,
    )
    return digest == expected_digest


def run_live_probe(model_key: str) -> dict[str, object]:
    spec = llm_schemas.build_assignment_spec([0])
    result: dict[str, object] = {
        "model_key": model_key,
        "schema_version": llm_schemas.SCHEMA_VERSION,
        "schema_hash": llm_schemas.canonical_schema_sha256(spec.schema),
        "synthetic_only": True,
        "database_writes": False,
        "retry_count": 0,
    }
    try:
        environment = _probe_environment(model_key)
        if model_key in EXPECTED_DIGESTS:
            result["digest_matches"] = _verify_ollama_digest(
                model_key,
                environment,
            )
            if not result["digest_matches"]:
                result["outcome"] = "FAIL_DIGEST"
                return result
        with patch.dict(os.environ, environment, clear=True):
            content = llm_provider.call_text(
                SYNTHETIC_PROMPT,
                purpose="clustering",
                response_schema=spec.schema,
                schema_name=spec.name,
            )
        instance = json.loads(content)
        result["local_validation"] = validate_probe_response(instance)
        result["outcome"] = "PASS"
    except Exception as exc:
        result.update(_safe_error(exc))
        result["outcome"] = "FAIL"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send live provider requests. Omit for the safe default.",
    )
    parser.add_argument(
        "--model",
        choices=("azure", "llama", "qwen", "all"),
        default="all",
    )
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({
            "live": False,
            "outcome": "SKIPPED",
            "reason": "Pass --live to send provider requests.",
        }, sort_keys=True))
        return 0

    load_dotenv(find_dotenv(filename=".env", usecwd=True), override=False)
    model_keys = ("azure", "llama", "qwen") if args.model == "all" else (args.model,)
    results = [run_live_probe(model_key) for model_key in model_keys]
    print(json.dumps({
        "live": True,
        "results": results,
    }, indent=2, sort_keys=True))
    return 0 if all(item["outcome"] == "PASS" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
