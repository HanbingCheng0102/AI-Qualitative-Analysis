"""Shared backend configuration and text generation for LLM services."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Literal

from services import experiment_config


LLMPurpose = Literal["clustering", "labelling"]


@dataclass(frozen=True)
class LLMBackendConfig:
    backend: str
    model_name: str
    api_key: str = field(default="", repr=False)
    base_url: str = ""
    timeout_seconds: float | None = None
    model_version: str | None = None
    deployment_type: str | None = None


class LLMProviderError(RuntimeError):
    """A provider failure with a safe, experiment-facing error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def get_active_backend_config(
    environ: dict[str, str] | None = None,
) -> LLMBackendConfig:
    source = os.environ if environ is None else environ
    backend = experiment_config.validate_backend_name(
        source.get("LLM_BACKEND", experiment_config.LLM_BACKEND)
    )
    timeout_seconds = experiment_config.read_positive_float_env(
        "LLM_TIMEOUT_SECONDS",
        default=experiment_config.LLM_TIMEOUT_SECONDS,
        environ=source,
    )

    if backend == "anthropic":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get(
                "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
            ),
            api_key=source.get("ANTHROPIC_API_KEY", ""),
            timeout_seconds=timeout_seconds,
        )
    if backend == "azure":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get("AZURE_OPENAI_MODEL", ""),
            api_key=source.get("AZURE_OPENAI_API_KEY", ""),
            base_url=experiment_config.validate_azure_base_url(
                source.get("AZURE_OPENAI_BASE_URL", "")
            ),
            timeout_seconds=timeout_seconds,
            model_version=source.get("AZURE_OPENAI_MODEL_VERSION", ""),
            deployment_type=source.get(
                "AZURE_OPENAI_DEPLOYMENT_TYPE", ""
            ),
        )
    if backend == "openai":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=source.get("OPENAI_API_KEY", ""),
            timeout_seconds=timeout_seconds,
        )
    if backend == "ollama":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get("OLLAMA_MODEL", "llama3"),
            base_url=source.get(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            ).rstrip("/"),
            timeout_seconds=timeout_seconds,
        )

    raise RuntimeError(f"Unsupported LLM_BACKEND={backend!r}.")


def get_model_metadata() -> tuple[str, str]:
    config = get_active_backend_config()
    return config.backend, config.model_name


def get_sensitive_values() -> tuple[str, ...]:
    api_key = get_active_backend_config().api_key
    return (api_key,) if api_key else ()


def get_run_parameters() -> dict[str, object]:
    config = get_active_backend_config()
    parameters: dict[str, object] = {
        "timeout_seconds": config.timeout_seconds,
        "max_retries": 0,
        "temperature": (
            0.2 if config.backend in {"azure", "openai"} else None
        ),
        "max_tokens": 512 if config.backend == "anthropic" else None,
    }
    if config.backend == "azure":
        parameters.update({
            "provider_protocol": "openai_v1",
            "model_version": config.model_version,
            "deployment_type": config.deployment_type,
        })
    return parameters


def _call_anthropic(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    import anthropic

    max_tokens = 512 if purpose == "clustering" else 256
    client = anthropic.Anthropic(
        api_key=config.api_key,
        timeout=config.timeout_seconds,
        max_retries=0,
    )
    message = client.messages.create(
        model=config.model_name,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _normalise_error_code(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _collect_error_codes(value: object) -> set[str]:
    if isinstance(value, str):
        try:
            return _collect_error_codes(json.loads(value))
        except (json.JSONDecodeError, TypeError):
            return {_normalise_error_code(value)}
    if isinstance(value, dict):
        codes: set[str] = set()
        for key, item in value.items():
            if str(key).lower() in {"code", "type"}:
                codes.add(_normalise_error_code(item))
            codes.update(_collect_error_codes(item))
        return codes
    if isinstance(value, (list, tuple)):
        codes: set[str] = set()
        for item in value:
            codes.update(_collect_error_codes(item))
        return codes
    return set()


def _is_azure_content_filter_error(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) != 400:
        return False
    codes = _collect_error_codes(getattr(exc, "body", None))
    direct_code = getattr(exc, "code", None)
    if direct_code:
        codes.add(_normalise_error_code(direct_code))
    return bool(codes & {
        "contentfilter",
        "contentpolicyviolation",
        "responsibleaipolicyviolation",
    })


def _call_openai_compatible(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    from openai import OpenAI

    temperature = 0.2 if purpose == "clustering" else 0.3
    client_options: dict[str, object] = {
        "api_key": config.api_key,
        "timeout": config.timeout_seconds,
        "max_retries": 0,
    }
    if config.base_url:
        client_options["base_url"] = config.base_url
    client = OpenAI(
        **client_options,
    )
    try:
        response = client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
    except Exception as exc:
        if config.backend == "azure" and _is_azure_content_filter_error(exc):
            raise LLMProviderError(
                "CONTENT_FILTERED",
                "Azure content filtering blocked the request or response.",
            ) from exc
        raise

    choice = response.choices[0]
    if (
        config.backend == "azure"
        and getattr(choice, "finish_reason", None) == "content_filter"
    ):
        raise LLMProviderError(
            "CONTENT_FILTERED",
            "Azure content filtering blocked the request or response.",
        )
    content = choice.message.content
    if not isinstance(content, str):
        raise LLMProviderError(
            "INVALID_LLM_RESPONSE",
            "LLM response did not contain text content.",
        )
    return content


def _call_openai(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    return _call_openai_compatible(prompt, config, purpose)


def _call_azure(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    return _call_openai_compatible(prompt, config, purpose)


def _call_ollama(
    prompt: str,
    config: LLMBackendConfig,
    _purpose: LLMPurpose,
) -> str:
    import httpx

    with httpx.Client(timeout=config.timeout_seconds) as client:
        response = client.post(
            f"{config.base_url}/api/generate",
            json={
                "model": config.model_name,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["response"]


def call_text(prompt: str, *, purpose: LLMPurpose) -> str:
    config = get_active_backend_config()
    callers = {
        "anthropic": _call_anthropic,
        "azure": _call_azure,
        "openai": _call_openai,
        "ollama": _call_ollama,
    }
    try:
        caller = callers[config.backend]
    except KeyError as exc:
        raise RuntimeError(
            f"Unsupported LLM_BACKEND={config.backend!r}."
        ) from exc
    return caller(prompt, config, purpose)
