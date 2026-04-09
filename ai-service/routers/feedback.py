"""
POST /feedback/recluster   — record a manual re-coding event, re-label affected clusters
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
    user_note: str = ""


class SuggestRequest(BaseModel):
    doc_id: str


def _cosine_sim(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@router.post("/recluster")
def record_feedback(req: FeedbackRequest):
    """
    Record a re-coding event and re-label the two affected clusters.
    """
    db = get_db()

    try:
        frag_oid = ObjectId(req.fragment_id)
        from_oid = ObjectId(req.from_cluster_id)
        to_oid = ObjectId(req.to_cluster_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId in request.")

    frag = db["fragments"].find_one({"_id": frag_oid})
    if not frag:
        raise HTTPException(status_code=404, detail="Fragment not found.")

    # Store doc_id on the feedback record so we can count per-survey
    doc_id = frag.get("docid")

    db["clusterFeedback"].insert_one({
        "fragment_id": frag_oid,
        "doc_id": doc_id,
        "from_cluster_id": from_oid,
        "to_cluster_id": to_oid,
        "timestamp": datetime.now(timezone.utc),
        "user_note": req.user_note,
    })

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

    count = db["clusterFeedback"].count_documents({"doc_id": doc_oid})
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
