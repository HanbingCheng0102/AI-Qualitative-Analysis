"""
LLM-driven semantic clustering pipeline.

Two phases:
  1. filter_fragments  — given a research question, decide per-fragment whether it is
                         relevant.  Runs concurrently (one LLM call per fragment).
  2. assign_fragment   — given one fragment and the current cluster list, decide which
                         cluster it belongs to (or create a new one).  Called sequentially
                         so each decision sees the up-to-date cluster list.

Both phases share the same LLM backend as labeller.py.
"""
from __future__ import annotations

import json
import logging
import math
import re
from typing import Generator

import numpy as np

from services import llm_provider

logger = logging.getLogger(__name__)

class LLMStrictModeError(RuntimeError):
    """An LLM request or response that makes an experimental run invalid."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _strict_call_error(stage: str, exc: Exception) -> LLMStrictModeError:
    if isinstance(exc, llm_provider.LLMProviderError):
        return LLMStrictModeError(exc.code, str(exc))
    code = "INVALID_LLM_JSON" if isinstance(exc, json.JSONDecodeError) else "LLM_REQUEST_FAILED"
    return LLMStrictModeError(code, f"LLM {stage} failed.")


def _required_text(result: dict, field_name: str) -> str:
    value = result.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise LLMStrictModeError(
            "INVALID_LLM_RESPONSE",
            f"LLM response requires a non-empty {field_name}.",
        )
    return value.strip()


def _strict_cluster_id(value: object) -> int:
    if isinstance(value, list):
        if len(value) != 1:
            raise LLMStrictModeError(
                "INVALID_LLM_RESPONSE",
                (
                    "LLM assign response returned an ambiguous cluster_id list; "
                    f"received {len(value)} items."
                ),
            )
        value = value[0]

    if type(value) is int and value >= 0:
        return value
    if isinstance(value, float) and math.isfinite(value) and value >= 0 and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d+", text):
            return int(text)
        if re.fullmatch(r"\d+\.0+", text):
            return int(text.split(".", 1)[0])
    raise LLMStrictModeError(
        "INVALID_LLM_RESPONSE",
        (
            "LLM assign response requires a losslessly integer cluster_id; "
            f"received type {type(value).__name__}."
        ),
    )


def _log_strict_assignment_rejection(
    stage: str,
    raw_response: str | None,
    clusters: list[dict],
    exc: LLMStrictModeError,
) -> None:
    logger.warning(
        "Strict LLM assignment response rejected stage=%s code=%s "
        "valid_cluster_ids=%s raw_response=%r",
        stage,
        exc.code,
        sorted(cluster["id"] for cluster in clusters),
        raw_response,
    )


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _call_llm(prompt: str) -> str:
    """Call the configured LLM and return raw text."""
    return llm_provider.call_text(prompt, purpose="clustering")


def _parse_json(text: str) -> dict:
    return json.loads(_strip_markdown(text))


# ---------------------------------------------------------------------------
# Phase 1 — Relevance filter
# ---------------------------------------------------------------------------

def is_relevant(
    fragment_text: str,
    research_question: str,
    *,
    strict: bool = False,
) -> bool:
    """
    Ask the LLM whether fragment_text is relevant to the research_question.
    Returns True (keep) or False (discard).
    Falls back to True on parse error so we never silently drop data.
    """
    prompt = f"""You are a research assistant helping filter survey responses.

Research question / filter: {research_question}

Survey response:
\"\"\"{fragment_text}\"\"\"

Does this response contain information that is relevant to the research question or filter above?
Reply with JSON only — no markdown, no explanation:
{{"relevant": true}} or {{"relevant": false}}"""

    try:
        result = _parse_json(_call_llm(prompt))
        if strict and not isinstance(result, dict):
            raise LLMStrictModeError(
                "INVALID_LLM_RESPONSE",
                "LLM relevance response must be a JSON object.",
            )
        if strict and type(result.get("relevant")) is not bool:
            raise LLMStrictModeError(
                "INVALID_LLM_RESPONSE",
                "LLM relevance response requires a boolean relevant field.",
            )
        return bool(result.get("relevant", True))
    except LLMStrictModeError:
        raise
    except Exception as exc:
        if strict:
            raise _strict_call_error("relevance filtering", exc) from exc
        return True  # fail open — keep the fragment


# ---------------------------------------------------------------------------
# Phase 2 — Iterative cluster assignment
# ---------------------------------------------------------------------------

def assign_fragment(
    fragment_text: str,
    clusters: list[dict],
    research_question: str,
    *,
    strict: bool = False,
) -> dict:
    """
    Given the current cluster list, decide where fragment_text belongs.

    clusters = [{"id": int, "label": str, "summary": str}, ...]

    Returns one of:
      {"action": "assign", "cluster_id": <int>}
      {"action": "new",    "label": <str>, "summary": <str>}
    """
    if not clusters:
        # First fragment always seeds a new cluster
        prompt = f"""You are a qualitative researcher clustering NHS survey responses.
Research focus: {research_question}

This is the very first response being placed. Create an appropriate cluster for it.

Response:
\"\"\"{fragment_text}\"\"\"

Reply with JSON only:
{{"label": "<short theme label, max 6 words>", "summary": "<one sentence describing the theme>"}}"""
        raw_response: str | None = None
        try:
            raw_response = _call_llm(prompt)
            result = _parse_json(raw_response)
            if strict:
                if not isinstance(result, dict):
                    raise LLMStrictModeError(
                        "INVALID_LLM_RESPONSE",
                        "LLM initial cluster response must be a JSON object.",
                    )
                label = _required_text(result, "label")
                summary = _required_text(result, "summary")
                return {"action": "new", "label": label, "summary": summary}
            return {"action": "new", "label": result["label"], "summary": result["summary"]}
        except LLMStrictModeError as exc:
            if strict:
                _log_strict_assignment_rejection(
                    "initial_cluster_assignment",
                    raw_response,
                    clusters,
                    exc,
                )
            raise
        except Exception as exc:
            if strict:
                strict_exc = _strict_call_error("initial cluster assignment", exc)
                _log_strict_assignment_rejection(
                    "initial_cluster_assignment",
                    raw_response,
                    clusters,
                    strict_exc,
                )
                raise strict_exc from exc
            return {"action": "new", "label": "Theme 1", "summary": fragment_text[:80]}

    valid_cluster_ids = sorted(c["id"] for c in clusters)
    cluster_list_text = "\n".join(
        f"  [{c['id']}] {c['label']} — {c['summary']}" for c in clusters
    )

    prompt = f"""You are a qualitative researcher clustering NHS survey responses.
Research focus: {research_question}

Existing clusters:
{cluster_list_text}

Valid existing cluster IDs: {valid_cluster_ids}

New response to place:
\"\"\"{fragment_text}\"\"\"

Decide: does this response belong to one of the existing clusters, or does it represent a new theme?

Rules:
- Assign to an existing cluster if the response clearly fits its theme.
- Create a new cluster only if the response introduces a genuinely distinct theme not covered above.
- For action "assign", cluster_id must be exactly one integer from the valid existing cluster IDs above.
- Never invent, infer, or increment a cluster ID.
- If no existing cluster fits, return action "new" with label and summary, and do not include cluster_id.
- Keep cluster labels short (max 6 words).

Reply with JSON only — no markdown, no explanation.
For assign, return only action and a valid integer cluster_id.
For new, return only action, label, and summary."""

    raw_response = None
    try:
        raw_response = _call_llm(prompt)
        result = _parse_json(raw_response)
        if strict and not isinstance(result, dict):
            raise LLMStrictModeError(
                "INVALID_LLM_RESPONSE",
                "LLM assignment response must be a JSON object.",
            )
        if result.get("action") == "assign":
            if strict:
                cluster_id = _strict_cluster_id(result.get("cluster_id"))
            else:
                cluster_id = int(result["cluster_id"])
            if strict and cluster_id not in valid_cluster_ids:
                raise LLMStrictModeError(
                    "INVALID_LLM_RESPONSE",
                    (
                        f"LLM assign response references unknown cluster_id={cluster_id}; "
                        f"valid_cluster_ids={valid_cluster_ids}."
                    ),
                )
            return {"action": "assign", "cluster_id": cluster_id}

        if result.get("action") == "new":
            if strict:
                label = _required_text(result, "label")
                summary = _required_text(result, "summary")
                return {"action": "new", "label": label, "summary": summary}
            return {
                "action": "new",
                "label": result.get("label", "New Theme"),
                "summary": result.get("summary", ""),
            }

        if strict:
            raise LLMStrictModeError(
                "INVALID_LLM_RESPONSE",
                "LLM assignment response requires action assign or new.",
            )
        return {
            "action": "new",
            "label": result.get("label", "New Theme"),
            "summary": result.get("summary", ""),
        }
    except LLMStrictModeError as exc:
        if strict:
            _log_strict_assignment_rejection(
                "cluster_assignment",
                raw_response,
                clusters,
                exc,
            )
        raise
    except Exception as exc:
        if strict:
            strict_exc = _strict_call_error("cluster assignment", exc)
            _log_strict_assignment_rejection(
                "cluster_assignment",
                raw_response,
                clusters,
                strict_exc,
            )
            raise strict_exc from exc
        # On parse failure, assign to cluster 0 as a safe fallback
        return {"action": "assign", "cluster_id": clusters[0]["id"]}


# ---------------------------------------------------------------------------
# Structured column filter
# ---------------------------------------------------------------------------

def passes_column_filters(row_data: dict, column_filters: dict[str, str]) -> bool:
    """
    column_filters: {column_name: required_value}
    All filters must match (case-insensitive, partial match) for the fragment to pass.
    Empty column_filters always passes.
    """
    for col, required in column_filters.items():
        if not required:
            continue
        actual = str(row_data.get(col, "")).strip().lower()
        if required.strip().lower() not in actual:
            return False
    return True


# ---------------------------------------------------------------------------
# Centroid helpers (used after clustering to compute cluster centroids)
# ---------------------------------------------------------------------------

def compute_centroid(embeddings: list[list[float]]) -> list[float]:
    if not embeddings:
        return []
    return np.array(embeddings, dtype=np.float32).mean(axis=0).tolist()
