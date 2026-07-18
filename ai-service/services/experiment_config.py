"""Fail-loud runtime configuration for provenance-sensitive LLM runs."""
from __future__ import annotations

import os
from collections.abc import Mapping


SUPPORTED_LLM_BACKENDS = frozenset({"anthropic", "openai", "ollama"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def read_bool_env(
    name: str,
    default: bool = False,
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    raw_value = source.get(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise RuntimeError(
        f"{name} must be one of: "
        "true, false, 1, 0, yes, no, on, off."
    )


def validate_backend_name(backend: str) -> str:
    value = backend.strip()
    if value not in SUPPORTED_LLM_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_LLM_BACKENDS))
        raise RuntimeError(
            f"Unsupported LLM_BACKEND={backend!r}; expected one of: {supported}."
        )
    return value


def validate_active_backend_configuration(
    backend: str,
    strict_mode: bool,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Validate only the selected backend; unused cloud keys may be absent."""
    backend = validate_backend_name(backend)
    if not strict_mode:
        return

    source = os.environ if environ is None else environ
    required_by_backend = {
        "anthropic": ("ANTHROPIC_MODEL", "ANTHROPIC_API_KEY"),
        "openai": ("OPENAI_MODEL", "OPENAI_API_KEY"),
        "ollama": ("OLLAMA_MODEL", "OLLAMA_BASE_URL"),
    }
    missing = [
        name
        for name in required_by_backend[backend]
        if not str(source.get(name, "")).strip()
    ]
    if missing:
        raise RuntimeError(
            f"Missing required configuration for LLM_BACKEND={backend!r}: "
            f"{', '.join(missing)}."
        )


LLM_BACKEND = validate_backend_name(os.environ.get("LLM_BACKEND", "anthropic"))
LLM_STRICT_MODE = read_bool_env("LLM_STRICT_MODE", default=False)
FREEZE_LABELS = read_bool_env("FREEZE_LABELS", default=False)
validate_active_backend_configuration(LLM_BACKEND, LLM_STRICT_MODE)
