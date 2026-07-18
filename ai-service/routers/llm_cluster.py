"""
POST /llm-cluster/run

Full LLM-driven pipeline:
  1. Load embedded fragments for a doc
  2. Apply structured column filters (e.g. Gender=Female)
  3. Apply semantic relevance filter (LLM scores each fragment against research_question)
  4. Iteratively assign each surviving fragment to a cluster via LLM
  5. Persist clusters + fragment assignments to MongoDB

Cluster labels and summaries are created inline when assign_fragment creates a
cluster. There is no independent post-clustering labelling pass in this route.

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

from services import experiment_config, llm_clusterer
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


class PipelineRunAbort(RuntimeError):
    def __init__(self, code: str, stage: str, public_detail: str):
        super().__init__(public_detail)
        self.code = code
        self.stage = stage
        self.public_detail = public_detail


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
    elif configured_backend == "openai":
        backend = "openai"
        model_name = llm_clusterer.OPENAI_MODEL
    else:
        raise RuntimeError(f"Unsupported LLM_BACKEND={configured_backend!r}.")

    if not model_name:
        logger.warning(
            "Could not resolve model_name for effective LLM backend=%r; using UNKNOWN",
            backend,
        )
        return backend, "UNKNOWN"
    return backend, str(model_name)


def _safe_failure_message(exc: Exception) -> str:
    message = " ".join(str(exc).split()) or exc.__class__.__name__
    message = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", message)
    for secret in (llm_clusterer.ANTHROPIC_KEY, llm_clusterer.OPENAI_KEY):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message[:500]


def _root_exception_type(exc: Exception) -> str:
    root = exc
    while isinstance(root.__cause__, Exception):
        root = root.__cause__
    return root.__class__.__name__


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


def _start_pipeline_run(
    db,
    req: LLMClusterRequest,
    doc_oid: ObjectId,
    strict_mode: bool,
) -> ObjectId | None:
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
            "status": "running",
            "strict_mode": strict_mode,
            "code_version": _get_code_version(),
        }
        return db["pipelineRuns"].insert_one(record).inserted_id
    except Exception as exc:
        logger.error("Could not record pipeline run start for doc_id=%s: %s", doc_oid, exc)
        if strict_mode:
            raise RuntimeError("Could not record required pipeline run provenance.") from exc
        return None


def _finish_pipeline_run(
    db,
    run_id: ObjectId | None,
    doc_oid: ObjectId,
    strict_mode: bool,
) -> None:
    if run_id is None:
        return

    try:
        result = db["pipelineRuns"].update_one(
            {"_id": run_id, "status": "running"},
            {
                "$set": {
                    "status": "completed",
                    "finished_at": datetime.now(timezone.utc),
                }
            },
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Could not find running pipelineRuns record {run_id} to complete."
            )
    except Exception as exc:
        logger.error(
            "Could not record pipeline run finish for doc_id=%s run_id=%s: %s",
            doc_oid,
            run_id,
            exc,
        )
        if strict_mode:
            raise RuntimeError("Could not record required pipeline run completion.") from exc


def _fail_pipeline_run(
    db,
    run_id: ObjectId | None,
    doc_oid: ObjectId,
    *,
    stage: str,
    code: str,
    exc: Exception,
    fragment_id: ObjectId | None = None,
) -> None:
    if run_id is None:
        logger.error(
            "Pipeline failed without a pipelineRuns record for doc_id=%s stage=%s code=%s",
            doc_oid,
            stage,
            code,
        )
        return

    failure = {
        "status": "failed",
        "failed_at": datetime.now(timezone.utc),
        "failure_stage": stage,
        "failure_code": code,
        "failure_type": _root_exception_type(exc),
        "failure_message": _safe_failure_message(exc),
    }
    if fragment_id is not None:
        failure["failure_fragment_id"] = fragment_id

    try:
        result = db["pipelineRuns"].update_one(
            {"_id": run_id, "status": "running"},
            {
                "$set": failure,
                "$unset": {"finished_at": ""},
            },
        )
        if result.matched_count != 1:
            logger.error(
                "Could not find running pipelineRuns record %s to fail for doc_id=%s",
                run_id,
                doc_oid,
            )
    except Exception as record_exc:
        logger.error(
            "Could not record pipeline failure for doc_id=%s run_id=%s: %s",
            doc_oid,
            run_id,
            record_exc,
        )


def _run_pipeline(
    req: LLMClusterRequest,
    db,
    doc_oid: ObjectId,
    pipeline_run_id: ObjectId | None,
    strict_mode: bool,
) -> Iterator[str]:
    current_stage = "load_fragments"
    current_fragment_id: ObjectId | None = None

    try:
        fragments = list(db["fragments"].find(
            {"docid": doc_oid, "embedding": {"$ne": None}},
            {"_id": 1, "name": 1, "redacted_text": 1, "embedding": 1, "row_data": 1},
        ))

        if not fragments:
            raise PipelineRunAbort(
                "NO_EMBEDDED_FRAGMENTS",
                current_stage,
                "No embedded fragments found. Run embedding first.",
            )

        # ------------------------------------------------------------------
        # Phase 1 — Structured column filter
        # ------------------------------------------------------------------
        current_stage = "column_filter"
        if req.column_filters:
            fragments = [
                f for f in fragments
                if llm_clusterer.passes_column_filters(
                    f.get("row_data") or {}, req.column_filters
                )
            ]

        if not fragments:
            raise PipelineRunAbort(
                "NO_FRAGMENTS_AFTER_COLUMN_FILTER",
                current_stage,
                "All fragments were removed by the column filters. Try broader filter values.",
            )

        # ------------------------------------------------------------------
        # Phase 2 — Semantic relevance filter (skip if no research question)
        # ------------------------------------------------------------------
        current_stage = "relevance_filter"
        surviving: list[dict] = []

        if req.research_question.strip():
            for frag in fragments:
                text = frag.get("redacted_text") or ""
                if not text.strip():
                    continue
                current_fragment_id = frag["_id"]
                kept = llm_clusterer.is_relevant(
                    text,
                    req.research_question,
                    strict=strict_mode,
                )
                yield _event({
                    "event": "filter",
                    "fragment_id": str(frag["_id"]),
                    "name": frag.get("name", "Response"),
                    "kept": kept,
                })
                if kept:
                    surviving.append(frag)
        else:
            surviving = [f for f in fragments if (f.get("redacted_text") or "").strip()]
            for frag in surviving:
                yield _event({
                    "event": "filter",
                    "fragment_id": str(frag["_id"]),
                    "name": frag.get("name", "Response"),
                    "kept": True,
                })

        current_fragment_id = None
        if not surviving:
            raise PipelineRunAbort(
                "NO_RELEVANT_FRAGMENTS",
                current_stage,
                "No fragments survived the relevance filter. Try a broader research question.",
            )

        # ------------------------------------------------------------------
        # Phase 3 — Iterative LLM cluster assignment
        # ------------------------------------------------------------------
        current_stage = "cluster_assignment"
        clusters: list[dict] = []
        next_cluster_id = 0

        for frag in surviving:
            current_fragment_id = frag["_id"]
            text = frag.get("redacted_text", "")
            cluster_specs = [
                {"id": c["id"], "label": c["label"], "summary": c["summary"]}
                for c in clusters
            ]

            decision = llm_clusterer.assign_fragment(
                text,
                cluster_specs,
                req.research_question,
                strict=strict_mode,
            )

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
                    if strict_mode:
                        raise llm_clusterer.LLMStrictModeError(
                            "INVALID_LLM_RESPONSE",
                            "LLM assignment response references an unknown cluster_id.",
                        )
                    matched = clusters[0]
                matched["fragment_ids"].append(frag["_id"])
                matched["embeddings"].append(frag["embedding"])
                yield _event({
                    "event": "assign",
                    "fragment_id": str(frag["_id"]),
                    "name": frag.get("name", "Response"),
                    "action": "assign",
                    "cluster_label": matched["label"],
                })

        current_fragment_id = None

        # ------------------------------------------------------------------
        # Phase 4 — Persist to MongoDB
        # ------------------------------------------------------------------
        current_stage = "persistence"
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

        current_stage = "completion_metadata"
        _finish_pipeline_run(
            db,
            pipeline_run_id,
            doc_oid,
            strict_mode,
        )

        yield _event({
            "event": "done",
            "cluster_count": len(clusters),
            "fragment_count": len(surviving),
            "cluster_ids": cluster_ids,
        })

    except PipelineRunAbort as exc:
        _fail_pipeline_run(
            db,
            pipeline_run_id,
            doc_oid,
            stage=exc.stage,
            code=exc.code,
            exc=exc,
            fragment_id=current_fragment_id,
        )
        yield _event({"event": "error", "detail": exc.public_detail})
    except llm_clusterer.LLMStrictModeError as exc:
        logger.exception(
            "Strict LLM run failed for doc_id=%s stage=%s fragment_id=%s",
            doc_oid,
            current_stage,
            current_fragment_id,
        )
        _fail_pipeline_run(
            db,
            pipeline_run_id,
            doc_oid,
            stage=current_stage,
            code=exc.code,
            exc=exc,
            fragment_id=current_fragment_id,
        )
        yield _event({
            "event": "error",
            "detail": (
                f"Strict LLM mode stopped the run during {current_stage}. "
                "No new cluster projection was persisted."
            ),
        })
    except Exception as exc:
        logger.exception(
            "Pipeline failed for doc_id=%s stage=%s fragment_id=%s",
            doc_oid,
            current_stage,
            current_fragment_id,
        )
        _fail_pipeline_run(
            db,
            pipeline_run_id,
            doc_oid,
            stage=current_stage,
            code="PIPELINE_ERROR",
            exc=exc,
            fragment_id=current_fragment_id,
        )
        yield _event({
            "event": "error",
            "detail": f"Pipeline failed during {current_stage}. Check the ai-service log.",
        })


@router.post("/run")
def llm_cluster_run(req: LLMClusterRequest):
    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    db = get_db()
    strict_mode = experiment_config.LLM_STRICT_MODE
    try:
        pipeline_run_id = _start_pipeline_run(db, req, doc_oid, strict_mode)
    except Exception as exc:
        logger.exception("Strict pipeline provenance start failed for doc_id=%s", doc_oid)
        raise HTTPException(
            status_code=503,
            detail="Could not start required pipeline provenance record.",
        ) from exc

    try:
        experiment_config.validate_active_backend_configuration(
            llm_clusterer.LLM_BACKEND,
            strict_mode,
        )
    except Exception as exc:
        _fail_pipeline_run(
            db,
            pipeline_run_id,
            doc_oid,
            stage="configuration",
            code="INVALID_CONFIGURATION",
            exc=exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Invalid active LLM backend configuration.",
        ) from exc

    return StreamingResponse(
        _run_pipeline(req, db, doc_oid, pipeline_run_id, strict_mode),
        media_type="application/x-ndjson",
    )
