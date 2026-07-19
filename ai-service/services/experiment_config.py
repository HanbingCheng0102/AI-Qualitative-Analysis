"""Fail-loud runtime configuration for provenance-sensitive LLM runs."""
from __future__ import annotations

import math
import os
from collections.abc import Mapping
from urllib.parse import urlparse


SUPPORTED_LLM_BACKENDS = frozenset({"anthropic", "azure", "openai", "ollama"})
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


def read_positive_float_env(
    name: str,
    default: float,
    environ: Mapping[str, str] | None = None,
) -> float:
    source = os.environ if environ is None else environ
    raw_value = source.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value.strip())
    except (AttributeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be a positive number.") from exc
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"{name} must be a positive number.")
    return value


def read_temperature_env(
    name: str,
    default: float | None = None,
    environ: Mapping[str, str] | None = None,
) -> float | None:
    source = os.environ if environ is None else environ
    raw_value = source.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value.strip())
    except (AttributeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be a number from 0 to 2.") from exc
    if not math.isfinite(value) or not 0 <= value <= 2:
        raise RuntimeError(f"{name} must be a number from 0 to 2.")
    return value


def read_integer_env(
    name: str,
    default: int | None = None,
    environ: Mapping[str, str] | None = None,
    *,
    minimum: int = 0,
) -> int | None:
    source = os.environ if environ is None else environ
    raw_value = source.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value.strip())
    except (AttributeError, ValueError) as exc:
        raise RuntimeError(
            f"{name} must be an integer greater than or equal to {minimum}."
        ) from exc
    if value < minimum:
        raise RuntimeError(
            f"{name} must be an integer greater than or equal to {minimum}."
        )
    return value


def validate_azure_base_url(base_url: str) -> str:
    value = base_url.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must be an HTTPS Foundry v1 base URL."
        )
    hostname = parsed.hostname.lower()
    if not hostname.endswith((
        ".services.ai.azure.com",
        ".openai.azure.com",
    )):
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must use an Azure Foundry hostname."
        )
    if parsed.username or parsed.password:
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must not contain credentials."
        )
    if parsed.query or parsed.fragment:
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must not include a query or fragment."
        )
    if parsed.path.rstrip("/") == "/openai/v1/chat/completions":
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must end at /openai/v1/, not "
            "/chat/completions."
        )
    if parsed.path.rstrip("/") != "/openai/v1":
        raise RuntimeError(
            "AZURE_OPENAI_BASE_URL must end with /openai/v1/."
        )
    return value.rstrip("/") + "/"


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
        "anthropic": (
            "ANTHROPIC_MODEL",
            "ANTHROPIC_API_KEY",
            "LLM_TIMEOUT_SECONDS",
            "LLM_TEMPERATURE",
            "LLM_MAX_TOKENS",
        ),
        "azure": (
            "AZURE_OPENAI_MODEL",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_BASE_URL",
            "AZURE_OPENAI_MODEL_VERSION",
            "AZURE_OPENAI_DEPLOYMENT_TYPE",
            "LLM_TIMEOUT_SECONDS",
            "LLM_TEMPERATURE",
            "LLM_SEED",
            "LLM_MAX_TOKENS",
        ),
        "openai": (
            "OPENAI_MODEL",
            "OPENAI_API_KEY",
            "LLM_TIMEOUT_SECONDS",
            "LLM_TEMPERATURE",
            "LLM_SEED",
            "LLM_MAX_TOKENS",
        ),
        "ollama": (
            "OLLAMA_MODEL",
            "OLLAMA_BASE_URL",
            "LLM_TIMEOUT_SECONDS",
            "LLM_TEMPERATURE",
            "LLM_SEED",
            "LLM_MAX_TOKENS",
        ),
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
    read_positive_float_env(
        "LLM_TIMEOUT_SECONDS",
        default=60,
        environ=source,
    )
    read_temperature_env(
        "LLM_TEMPERATURE",
        environ=source,
    )
    read_integer_env(
        "LLM_MAX_TOKENS",
        environ=source,
        minimum=1,
    )
    if backend in {"azure", "openai", "ollama"}:
        read_integer_env(
            "LLM_SEED",
            environ=source,
        )
    if backend == "azure":
        validate_azure_base_url(source["AZURE_OPENAI_BASE_URL"])


LLM_BACKEND = validate_backend_name(os.environ.get("LLM_BACKEND", "anthropic"))
LLM_STRICT_MODE = read_bool_env("LLM_STRICT_MODE", default=False)
FREEZE_LABELS = read_bool_env("FREEZE_LABELS", default=False)
LLM_TIMEOUT_SECONDS = read_positive_float_env(
    "LLM_TIMEOUT_SECONDS",
    default=60,
)
LLM_TEMPERATURE = read_temperature_env("LLM_TEMPERATURE")
LLM_SEED = read_integer_env("LLM_SEED")
LLM_MAX_TOKENS = read_integer_env("LLM_MAX_TOKENS", minimum=1)
validate_active_backend_configuration(LLM_BACKEND, LLM_STRICT_MODE)
