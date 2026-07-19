"""Shared backend configuration and text generation for LLM services."""
from __future__ import annotations

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


def get_active_backend_config(
    environ: dict[str, str] | None = None,
) -> LLMBackendConfig:
    source = os.environ if environ is None else environ
    backend = experiment_config.validate_backend_name(
        source.get("LLM_BACKEND", experiment_config.LLM_BACKEND)
    )

    if backend == "anthropic":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get(
                "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
            ),
            api_key=source.get("ANTHROPIC_API_KEY", ""),
        )
    if backend == "openai":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=source.get("OPENAI_API_KEY", ""),
            timeout_seconds=30,
        )
    if backend == "ollama":
        return LLMBackendConfig(
            backend=backend,
            model_name=source.get("OLLAMA_MODEL", "llama3"),
            base_url=source.get(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            ).rstrip("/"),
            timeout_seconds=60,
        )

    raise RuntimeError(f"Unsupported LLM_BACKEND={backend!r}.")


def get_model_metadata() -> tuple[str, str]:
    config = get_active_backend_config()
    return config.backend, config.model_name


def get_sensitive_values() -> tuple[str, ...]:
    api_key = get_active_backend_config().api_key
    return (api_key,) if api_key else ()


def _call_anthropic(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    import anthropic

    max_tokens = 512 if purpose == "clustering" else 256
    client = anthropic.Anthropic(api_key=config.api_key)
    message = client.messages.create(
        model=config.model_name,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai(
    prompt: str,
    config: LLMBackendConfig,
    purpose: LLMPurpose,
) -> str:
    from openai import OpenAI

    temperature = 0.2 if purpose == "clustering" else 0.3
    client = OpenAI(
        api_key=config.api_key,
        timeout=config.timeout_seconds,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=config.model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError("OpenAI response did not contain text content.")
    return content


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
