"""
POST /llm-cluster/run

Full LLM-driven pipeline:
  1. Load embedded fragments for a doc
  2. Apply structured column filters (e.g. Gender=Female)
  3. Apply semantic relevance filter (LLM scores each fragment against research_question)
  4. Iteratively assign each surviving fragment to a cluster via LLM
  5. Persist clusters + fragment assignments to MongoDB
  6. Re-label clusters with the same LLM labeller used elsewhere

Streams NDJSON progress events so the UI can show a live log:
  {"event": "filter",  "fragment_id": "...", "name": "...", "kept": true/false, "reason": "..."}
  {"event": "assign",  "fragment_id": "...", "name": "...", "cluster_label": "...", "action": "assign"|"new"}
  {"event": "done",    "cluster_count": N, "fragment_count": M, "cluster_ids": [...]}
  {"event": "error",   "detail": "..."}
"""
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import labeller, llm_clusterer
from services.mongo_client import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

_BATCH_LABEL_RE = re.compile(
    r"(?:^|[_\s-])batch[_\s-]*([ABC])(?:$|[_\s-])",
    flags=re.IGNORECASE,
)
_REPO_ROOT = Path(__file__).resolve().parents[2]

_PALETTE = [
    "#4CAF50", "#2196F3", "#FF5722", "#9C27B0", "#FF9800",
    "#00BCD4", "#E91E63", "#3F51B5", "#8BC34A", "#FFC107",
    "#009688", "#F44336", "#673AB7", "#03A9F4", "#CDDC39",
]


class LLMClusterRequest(BaseModel):
    doc_id: str
    research_question: str = ""
    column_filters: dict[str, str] = {}   # {column_name: required_value}


def _event(obj: dict) -> str:
    return json.dumps(obj) + "\n"


def _get_model_metadata() -> tuple[str, str]:
    configured_backend = str(llm_clusterer.LLM_BACKEND)
    if configured_backend == "anthropic":
        backend = "anthropic"
        model_name = llm_clusterer.ANTHROPIC_MODEL
    elif configured_backend == "ollama":
        backend = "ollama"
        model_name = llm_clusterer.OLLAMA_MODEL
    else:
        # llm_clusterer uses OpenAI as its fallback for every other value.
        backend = "openai"
        model_name = llm_clusterer.OPENAI_MODEL
        if configured_backend != "openai":
            logger.warning(
                "Unsupported LLM_BACKEND=%r; runtime falls back to OpenAI",
                configured_backend,
            )

    if not model_name:
        logger.warning(
            "Could not resolve model_name for effective LLM backend=%r; using UNKNOWN",
            backend,
        )
        return backend, "UNKNOWN"
    return backend, str(model_name)


def _parse_batch_label(survey_name: str | None, doc_oid: ObjectId) -> str:
    matches = _BATCH_LABEL_RE.findall(survey_name or "")
    if len(matches) == 1:
        return matches[0].upper()

    logger.warning(
        "Could not parse a unique batch label for doc_id=%s survey_name=%r; using UNKNOWN",
        doc_oid,
        survey_name,
    )
    return "UNKNOWN"


def _get_code_version() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        code_version = result.stdout.strip()
        if not code_version:
            raise ValueError("git returned an empty commit hash")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.warning("Could not determine code_version: %s", exc)
        return None

    try:
        dirty_result = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if dirty_result.stdout.strip():
            logger.warning(
                "Working tree is dirty; code_version=%s does not include uncommitted changes",
                code_version,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not determine whether the working tree is dirty: %s", exc)

    return code_version


def _start_pipeline_run(db, req: LLMClusterRequest, doc_oid: ObjectId) -> ObjectId | None:
    started_at = datetime.now(timezone.utc)
    try:
        document = db["documents"].find_one({"_id": doc_oid}, {"name": 1})
        survey_name = document.get("name") if document else None
        llm_backend, model_name = _get_model_metadata()
        record = {
            "doc_id": doc_oid,
            "pipeline": "llm_semantic",
            "llm_backend": llm_backend,
            "model_name": model_name,
            "research_question": req.research_question,
            "params": {"column_filters": dict(req.column_filters)},
            "batch_label": _parse_batch_label(survey_name, doc_oid),
            "started_at": started_at,
            "code_version": _get_code_version(),
        }
        return db["pipelineRuns"].insert_one(record).inserted_id
    except Exception as exc:
        logger.warning("Could not record pipeline run start for doc_id=%s: %s", doc_oid, exc)
        return None


def _finish_pipeline_run(db, run_id: ObjectId | None, doc_oid: ObjectId) -> None:
    if run_id is None:
        return

    try:
        result = db["pipelineRuns"].update_one(
            {"_id": run_id},
            {"$set": {"finished_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count != 1:
            logger.warning(
                "Could not find pipelineRuns record %s to finish for doc_id=%s",
                run_id,
                doc_oid,
            )
    except Exception as exc:
        logger.warning(
            "Could not record pipeline run finish for doc_id=%s run_id=%s: %s",
            doc_oid,
            run_id,
            exc,
        )


def _run_pipeline(req: LLMClusterRequest) -> Iterator[str]:
    db = get_db()

    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        yield _event({"event": "error", "detail": "Invalid doc_id"})
        return

    pipeline_run_id = _start_pipeline_run(db, req, doc_oid)

    # Load all fragments that have been embedded
    fragments = list(db["fragments"].find(
        {"docid": doc_oid, "embedding": {"$ne": None}},
        {"_id": 1, "name": 1, "redacted_text": 1, "embedding": 1, "row_data": 1},
    ))

    if not fragments:
        yield _event({"event": "error", "detail": "No embedded fragments found. Run embedding first."})
        return

    # ------------------------------------------------------------------
    # Phase 1 — Structured column filter
    # ------------------------------------------------------------------
    if req.column_filters:
        fragments = [
            f for f in fragments
            if llm_clusterer.passes_column_filters(
                f.get("row_data") or {}, req.column_filters
            )
        ]

    if not fragments:
        yield _event({"event": "error", "detail": "All fragments were removed by the column filters. Try broader filter values."})
        return

    # ------------------------------------------------------------------
    # Phase 2 — Semantic relevance filter (skip if no research question)
    # ------------------------------------------------------------------
    surviving: list[dict] = []

    if req.research_question.strip():
        for frag in fragments:
            text = frag.get("redacted_text") or ""
            if not text.strip():
                continue
            kept = llm_clusterer.is_relevant(text, req.research_question)
            yield _event({
                "event": "filter",
                "fragment_id": str(frag["_id"]),
                "name": frag.get("name", "Response"),
                "kept": kept,
            })
            if kept:
                surviving.append(frag)
    else:
        # No research question — keep everything that passed column filter
        surviving = [f for f in fragments if (f.get("redacted_text") or "").strip()]
        for frag in surviving:
            yield _event({
                "event": "filter",
                "fragment_id": str(frag["_id"]),
                "name": frag.get("name", "Response"),
                "kept": True,
            })

    if not surviving:
        yield _event({"event": "error", "detail": "No fragments survived the relevance filter. Try a broader research question."})
        return

    # ------------------------------------------------------------------
    # Phase 3 — Iterative LLM cluster assignment
    # ------------------------------------------------------------------
    # clusters: [{id, label, summary, fragment_ids, embeddings}]
    clusters: list[dict] = []
    next_cluster_id = 0

    for frag in surviving:
        text = frag.get("redacted_text", "")
        cluster_specs = [
            {"id": c["id"], "label": c["label"], "summary": c["summary"]}
            for c in clusters
        ]

        decision = llm_clusterer.assign_fragment(text, cluster_specs, req.research_question)

        if decision["action"] == "new":
            new_cluster = {
                "id": next_cluster_id,
                "label": decision["label"],
                "summary": decision["summary"],
                "fragment_ids": [frag["_id"]],
                "embeddings": [frag["embedding"]],
            }
            clusters.append(new_cluster)
            next_cluster_id += 1
            yield _event({
                "event": "assign",
                "fragment_id": str(frag["_id"]),
                "name": frag.get("name", "Response"),
                "action": "new",
                "cluster_label": decision["label"],
            })

        else:
            cid = decision["cluster_id"]
            matched = next((c for c in clusters if c["id"] == cid), None)
            if matched is None:
                matched = clusters[0]  # safe fallback
            matched["fragment_ids"].append(frag["_id"])
            matched["embeddings"].append(frag["embedding"])
            yield _event({
                "event": "assign",
                "fragment_id": str(frag["_id"]),
                "name": frag.get("name", "Response"),
                "action": "assign",
                "cluster_label": matched["label"],
            })

    # ------------------------------------------------------------------
    # Phase 4 — Persist to MongoDB
    # ------------------------------------------------------------------
    # Remove existing clusters for this doc
    db["clusters"].delete_many({"survey_doc_id": doc_oid})
    db["fragments"].update_many(
        {"docid": doc_oid},
        {"$unset": {"cluster_id": "", "cluster_label": "", "feedback_cluster_id": ""}},
    )

    cluster_ids: list[str] = []

    for i, cl in enumerate(clusters):
        cluster_oid = ObjectId()
        color = _PALETTE[i % len(_PALETTE)]
        centroid = llm_clusterer.compute_centroid(cl["embeddings"])

        db["clusters"].insert_one({
            "_id": cluster_oid,
            "label": cl["label"],
            "summary": cl["summary"],
            "color": color,
            "survey_doc_id": doc_oid,
            "fragment_ids": cl["fragment_ids"],
            "centroid": centroid,
            "size": len(cl["fragment_ids"]),
            "created_at": datetime.now(timezone.utc),
        })

        db["fragments"].update_many(
            {"_id": {"$in": cl["fragment_ids"]}},
            {"$set": {"cluster_id": cluster_oid, "cluster_label": cl["label"]}},
        )

        cluster_ids.append(str(cluster_oid))

    _finish_pipeline_run(db, pipeline_run_id, doc_oid)

    yield _event({
        "event": "done",
        "cluster_count": len(clusters),
        "fragment_count": len(surviving),
        "cluster_ids": cluster_ids,
    })


@router.post("/run")
def llm_cluster_run(req: LLMClusterRequest):
    return StreamingResponse(
        _run_pipeline(req),
        media_type="application/x-ndjson",
    )
