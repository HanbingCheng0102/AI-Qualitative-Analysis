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
from datetime import datetime, timezone
from typing import Iterator

import numpy as np
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import labeller, llm_clusterer
from services.mongo_client import get_db

router = APIRouter()

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


def _run_pipeline(req: LLMClusterRequest) -> Iterator[str]:
    db = get_db()

    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        yield _event({"event": "error", "detail": "Invalid doc_id"})
        return

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
