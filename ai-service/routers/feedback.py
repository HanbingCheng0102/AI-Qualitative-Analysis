"""
POST /feedback/recluster   — record a manual re-coding event, re-label affected clusters
POST /feedback/log         — record a non-mutating provenance event
GET  /feedback/count/{doc_id} — total manual placements for a survey
POST /feedback/suggest     — suggest cluster assignments for uncategorised fragments
"""
import numpy as np
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import labeller
from services.mongo_client import get_db

router = APIRouter()


class FeedbackRequest(BaseModel):
    fragment_id: str
    from_cluster_id: str
    to_cluster_id: str
    action: str = "move"
    participant_id: str | None = "TEST"
    suggested_cluster_id: str | None = None
    suggestion_score: float | None = None
    user_note: str = ""


class FeedbackLogRequest(BaseModel):
    doc_id: str
    fragment_id: str
    action: str
    participant_id: str | None = "TEST"
    from_cluster_id: str | None = None
    to_cluster_id: str | None = None
    suggested_cluster_id: str | None = None
    suggestion_score: float | None = None
    user_note: str | None = None


class SuggestRequest(BaseModel):
    doc_id: str


def _object_id(value: str, field_name: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}.")


def _participant_id(value: str | None) -> str:
    return (value or "TEST").strip().upper() or "TEST"


def _cosine_sim(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@router.post("/log")
def log_feedback(req: FeedbackLogRequest):
    """
    Record a non-mutating provenance event.

    This endpoint is deliberately limited to actions that do not change fragment
    placement. Mutating actions are recorded by /feedback/recluster instead.
    """
    action = req.action.strip()
    if action not in {"confirm", "reject_suggestion"}:
        raise HTTPException(
            status_code=422,
            detail="/feedback/log only accepts confirm or reject_suggestion.",
        )

    if action == "confirm" and not req.from_cluster_id:
        raise HTTPException(status_code=422, detail="confirm requires from_cluster_id.")

    if action == "reject_suggestion" and not req.suggested_cluster_id:
        raise HTTPException(status_code=422, detail="reject_suggestion requires suggested_cluster_id.")

    doc_oid = _object_id(req.doc_id, "doc_id")
    frag_oid = _object_id(req.fragment_id, "fragment_id")

    record = {
        "doc_id": doc_oid,
        "fragment_id": frag_oid,
        "action": action,
        "participant_id": _participant_id(req.participant_id),
        "timestamp": datetime.now(timezone.utc),
        "user_note": req.user_note or "",
    }

    if req.from_cluster_id:
        record["from_cluster_id"] = _object_id(req.from_cluster_id, "from_cluster_id")
    if req.to_cluster_id:
        record["to_cluster_id"] = _object_id(req.to_cluster_id, "to_cluster_id")
    if req.suggested_cluster_id:
        record["suggested_cluster_id"] = _object_id(
            req.suggested_cluster_id,
            "suggested_cluster_id",
        )
    if req.suggestion_score is not None:
        record["suggestion_score"] = req.suggestion_score

    result = get_db()["clusterFeedback"].insert_one(record)
    return {"ok": True, "feedback_id": str(result.inserted_id)}


@router.get("/latest-state/{doc_id}")
def get_latest_feedback_state(doc_id: str, participant: str = "TEST"):
    """
    Return the latest provenance action for each fragment for one participant.

    The adjudication key is timestamp descending, then _id descending. This keeps
    restore behaviour deterministic when two events are recorded very close
    together.
    """
    db = get_db()
    doc_oid = _object_id(doc_id, "doc_id")
    participant_id = _participant_id(participant)

    pipeline = [
        {"$match": {"doc_id": doc_oid, "participant_id": participant_id}},
        {"$sort": {"timestamp": -1, "_id": -1}},
        {"$group": {"_id": "$fragment_id", "record": {"$first": "$$ROOT"}}},
    ]

    states = []
    for row in db["clusterFeedback"].aggregate(pipeline):
        record = row["record"]
        state = {
            "fragment_id": str(row["_id"]),
            "feedback_id": str(record["_id"]),
            "latest_action": record.get("action", "move"),
            "participant_id": participant_id,
        }

        timestamp = record.get("timestamp")
        if timestamp:
            state["timestamp"] = timestamp.isoformat()
        if record.get("from_cluster_id"):
            state["from_cluster_id"] = str(record["from_cluster_id"])
        if record.get("to_cluster_id"):
            state["to_cluster_id"] = str(record["to_cluster_id"])
        if record.get("suggested_cluster_id"):
            state["suggested_cluster_id"] = str(record["suggested_cluster_id"])

        states.append(state)

    return {"participant_id": participant_id, "states": states}


@router.post("/recluster")
def record_feedback(req: FeedbackRequest):
    """
    Record a re-coding event and re-label the two affected clusters.
    """
    db = get_db()

    action = req.action.strip()
    if action not in {"move", "accept_suggestion"}:
        raise HTTPException(
            status_code=422,
            detail="/feedback/recluster only accepts move or accept_suggestion.",
        )

    if action == "accept_suggestion" and not req.suggested_cluster_id:
        raise HTTPException(status_code=422, detail="accept_suggestion requires suggested_cluster_id.")

    try:
        frag_oid = ObjectId(req.fragment_id)
        from_oid = ObjectId(req.from_cluster_id)
        to_oid = ObjectId(req.to_cluster_id)
        suggested_oid = ObjectId(req.suggested_cluster_id) if req.suggested_cluster_id else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId in request.")

    if action == "accept_suggestion" and suggested_oid != to_oid:
        raise HTTPException(
            status_code=422,
            detail="accept_suggestion requires suggested_cluster_id to match to_cluster_id.",
        )

    frag = db["fragments"].find_one({"_id": frag_oid})
    if not frag:
        raise HTTPException(status_code=404, detail="Fragment not found.")

    # Store doc_id on the feedback record so we can count per-survey
    doc_id = frag.get("docid")

    record = {
        "fragment_id": frag_oid,
        "doc_id": doc_id,
        "from_cluster_id": from_oid,
        "to_cluster_id": to_oid,
        "action": action,
        "participant_id": _participant_id(req.participant_id),
        "timestamp": datetime.now(timezone.utc),
        "user_note": req.user_note,
    }
    if suggested_oid:
        record["suggested_cluster_id"] = suggested_oid
    if req.suggestion_score is not None:
        record["suggestion_score"] = req.suggestion_score

    db["clusterFeedback"].insert_one(record)

    # Move fragment to new cluster
    db["fragments"].update_one(
        {"_id": frag_oid},
        {"$set": {"feedback_cluster_id": to_oid, "cluster_id": to_oid}},
    )

    # Update fragment_ids on both clusters
    db["clusters"].update_one({"_id": from_oid}, {"$pull": {"fragment_ids": frag_oid}})
    db["clusters"].update_one({"_id": to_oid}, {"$addToSet": {"fragment_ids": frag_oid}})

    # Recompute centroid for the destination cluster
    all_frags = list(db["fragments"].find(
        {"cluster_id": to_oid, "embedding": {"$ne": None}},
        {"embedding": 1}
    ))
    if all_frags:
        embs = np.array([f["embedding"] for f in all_frags], dtype=np.float32)
        new_centroid = embs.mean(axis=0).tolist()
        db["clusters"].update_one({"_id": to_oid}, {"$set": {"centroid": new_centroid}})

    # Re-label both affected clusters
    for cluster_oid in (from_oid, to_oid):
        cluster = db["clusters"].find_one({"_id": cluster_oid})
        if not cluster:
            continue
        frags = list(db["fragments"].find(
            {"cluster_id": cluster_oid, "redacted_text": {"$ne": None}},
            {"redacted_text": 1},
            limit=10,
        ))
        if not frags:
            continue
        sample_texts = [f["redacted_text"] for f in frags]
        result = labeller.label_cluster(sample_texts)
        db["clusters"].update_one(
            {"_id": cluster_oid},
            {"$set": {"label": result["label"], "summary": result["summary"]}},
        )

    return {"ok": True}


@router.get("/count/{doc_id}")
def get_feedback_count(doc_id: str):
    """
    Return the number of manual placement events recorded for a survey doc.
    """
    db = get_db()
    try:
        doc_oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    count = db["clusterFeedback"].count_documents({
        "doc_id": doc_oid,
        "$or": [
            {"action": {"$exists": False}},  # legacy records are historical moves
            {"action": {"$in": ["move", "accept_suggestion"]}},
        ],
    })
    return {"count": count}


@router.post("/suggest")
def suggest_placements(req: SuggestRequest):
    """
    Suggest cluster assignments for uncategorised fragments.
    Uses cosine similarity between fragment embeddings and updated cluster centroids.
    Only called after >= 20 manual placements (enforced by frontend).
    """
    db = get_db()
    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    # Find uncategorised clusters for this doc
    noise_clusters = list(db["clusters"].find(
        {"survey_doc_id": doc_oid, "label": "Uncategorised"}
    ))
    noise_ids = [c["_id"] for c in noise_clusters]

    if not noise_ids:
        return {"suggestions": []}

    # Fragments in noise clusters that have embeddings
    noise_frags = list(db["fragments"].find(
        {"cluster_id": {"$in": noise_ids}, "embedding": {"$ne": None}},
        {"_id": 1, "name": 1, "redacted_text": 1, "embedding": 1}
    ))

    if not noise_frags:
        return {"suggestions": []}

    # Real clusters with centroids
    real_clusters = list(db["clusters"].find(
        {"survey_doc_id": doc_oid, "label": {"$ne": "Uncategorised"}, "centroid": {"$ne": None}}
    ))

    if not real_clusters:
        return {"suggestions": []}

    suggestions = []
    for frag in noise_frags[:25]:
        emb = frag["embedding"]
        best_cluster = None
        best_score = -1.0

        for cluster in real_clusters:
            score = _cosine_sim(emb, cluster["centroid"])
            if score > best_score:
                best_score = score
                best_cluster = cluster

        # Only suggest if confidence is reasonable
        if best_cluster and best_score > 0.25:
            suggestions.append({
                "fragment_id": str(frag["_id"]),
                "fragment_name": frag.get("name", "Response"),
                "fragment_text": (frag.get("redacted_text") or "")[:200],
                "suggested_cluster_id": str(best_cluster["_id"]),
                "suggested_cluster_label": best_cluster.get("label", "Cluster"),
                "suggested_cluster_color": best_cluster.get("color", "#94a3b8"),
                "confidence": round(best_score, 3),
            })

    return {
        "suggestions": sorted(suggestions, key=lambda x: x["confidence"], reverse=True)
    }
