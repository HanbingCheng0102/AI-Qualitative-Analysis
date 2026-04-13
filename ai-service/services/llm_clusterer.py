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
import os
import re
from typing import Generator

import numpy as np

# ---------------------------------------------------------------------------
# LLM backend config (mirrors labeller.py)
# ---------------------------------------------------------------------------

LLM_BACKEND      = os.environ.get("LLM_BACKEND", "anthropic")
ANTHROPIC_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL  = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
OPENAI_KEY       = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL     = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE      = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.environ.get("OLLAMA_MODEL", "llama3")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _call_llm(prompt: str) -> str:
    """Call the configured LLM and return raw text."""
    if LLM_BACKEND == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    if LLM_BACKEND == "ollama":
        import httpx
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{OLLAMA_BASE}/api/generate",
                       json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status()
            return r.json()["response"]

    # openai
    import httpx
    with httpx.Client(timeout=30) as c:
        r = c.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={"model": OPENAI_MODEL,
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _parse_json(text: str) -> dict:
    return json.loads(_strip_markdown(text))


# ---------------------------------------------------------------------------
# Phase 1 — Relevance filter
# ---------------------------------------------------------------------------

def is_relevant(fragment_text: str, research_question: str) -> bool:
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
        return bool(result.get("relevant", True))
    except Exception:
        return True  # fail open — keep the fragment


# ---------------------------------------------------------------------------
# Phase 2 — Iterative cluster assignment
# ---------------------------------------------------------------------------

def assign_fragment(
    fragment_text: str,
    clusters: list[dict],
    research_question: str,
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
        try:
            result = _parse_json(_call_llm(prompt))
            return {"action": "new", "label": result["label"], "summary": result["summary"]}
        except Exception:
            return {"action": "new", "label": "Theme 1", "summary": fragment_text[:80]}

    cluster_list_text = "\n".join(
        f"  [{c['id']}] {c['label']} — {c['summary']}" for c in clusters
    )

    prompt = f"""You are a qualitative researcher clustering NHS survey responses.
Research focus: {research_question}

Existing clusters:
{cluster_list_text}

New response to place:
\"\"\"{fragment_text}\"\"\"

Decide: does this response belong to one of the existing clusters, or does it represent a new theme?

Rules:
- Assign to an existing cluster if the response clearly fits its theme.
- Create a new cluster only if the response introduces a genuinely distinct theme not covered above.
- Keep cluster labels short (max 6 words).

Reply with JSON only — no markdown, no explanation.
To assign:  {{"action": "assign", "cluster_id": <number>}}
To create:  {{"action": "new", "label": "<label>", "summary": "<one sentence>"}}"""

    try:
        result = _parse_json(_call_llm(prompt))
        if result.get("action") == "assign":
            return {"action": "assign", "cluster_id": int(result["cluster_id"])}
        else:
            return {
                "action": "new",
                "label": result.get("label", "New Theme"),
                "summary": result.get("summary", ""),
            }
    except Exception:
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
