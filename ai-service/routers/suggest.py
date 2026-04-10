"""
POST /suggest/placement  — given current manual groups + a fragment, suggest which group it fits
POST /suggest/save       — persist manual groups as labelled cluster documents in MongoDB
"""
import numpy as np
from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import labeller
from services.mongo_client import get_db

router = APIRouter()

_PALETTE = [
    "#4CAF50", "#2196F3", "#FF5722", "#9C27B0", "#FF9800",
    "#00BCD4", "#E91E63", "#3F51B5", "#8BC34A", "#FFC107",
    "#009688", "#F44336", "#673AB7", "#03A9F4", "#CDDC39",
]


def _cosine_sim(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── Placement suggestion ──────────────────────────────────────────────────────

class GroupSpec(BaseModel):
    group_id: str
    fragment_ids: List[str]


class PlacementRequest(BaseModel):
    doc_id: str
    fragment_id: str
    groups: List[GroupSpec]


@router.post("/placement")
def suggest_placement(req: PlacementRequest):
    """
    Given the current proximity groups on the manual canvas and a queued fragment,
    return the group_id it most likely belongs to, or indicate a new cluster is needed.
    Only called after >= 20 fragments have been placed (enforced by frontend).
    """
    db = get_db()

    try:
        frag_oid = ObjectId(req.fragment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fragment_id")

    frag = db["fragments"].find_one({"_id": frag_oid}, {"embedding": 1})
    if not frag or not frag.get("embedding"):
        return {"suggestion": None, "reason": "no embedding"}

    frag_emb = np.array(frag["embedding"], dtype=np.float32)

    best_group_id = None
    best_confidence = 0.0

    for group in req.groups:
        if not group.fragment_ids:
            continue

        try:
            oids = [ObjectId(fid) for fid in group.fragment_ids]
        except Exception:
            continue

        frags = list(db["fragments"].find(
            {"_id": {"$in": oids}, "embedding": {"$ne": None}},
            {"embedding": 1},
        ))
        if not frags:
            continue

        embs = np.array([f["embedding"] for f in frags], dtype=np.float32)
        centroid = embs.mean(axis=0)
        sim = _cosine_sim(frag_emb, centroid)

        if sim > best_confidence:
            best_confidence = sim
            best_group_id = group.group_id

    THRESHOLD = 0.35
    if best_confidence >= THRESHOLD and best_group_id is not None:
        return {
            "suggestion": {
                "group_id": best_group_id,
                "confidence": round(best_confidence, 3),
                "new_cluster": False,
            }
        }
    return {
        "suggestion": {
            "group_id": None,
            "confidence": round(best_confidence, 3),
            "new_cluster": True,
        }
    }


# ── Save manual clusters ──────────────────────────────────────────────────────

class SaveGroupSpec(BaseModel):
    fragment_ids: List[str]


class SaveRequest(BaseModel):
    doc_id: str
    groups: List[SaveGroupSpec]


@router.post("/save")
def save_manual_clusters(req: SaveRequest):
    """
    Persist manual proximity groups as labelled cluster documents.
    Removes any existing clusters for the doc first, then creates one cluster
    per group, computes centroids, and labels each via LLM.
    """
    db = get_db()

    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    # Clear existing clusters for this doc
    db["clusters"].delete_many({"survey_doc_id": doc_oid})
    db["fragments"].update_many(
        {"docid": doc_oid},
        {"$unset": {"cluster_id": "", "feedback_cluster_id": ""}},
    )

    cluster_ids: list[str] = []
    labelled: list[dict] = []

    for i, group in enumerate(req.groups):
        if not group.fragment_ids:
            continue

        try:
            frag_oids = [ObjectId(fid) for fid in group.fragment_ids]
        except Exception:
            continue

        frags = list(db["fragments"].find(
            {"_id": {"$in": frag_oids}},
            {"_id": 1, "embedding": 1, "redacted_text": 1},
        ))

        # Centroid in embedding space
        emb_frags = [f for f in frags if f.get("embedding")]
        centroid = None
        if emb_frags:
            embs = np.array([f["embedding"] for f in emb_frags], dtype=np.float32)
            centroid = embs.mean(axis=0).tolist()

        color = _PALETTE[i % len(_PALETTE)]
        cluster_oid = ObjectId()

        db["clusters"].insert_one({
            "_id": cluster_oid,
            "label": "TBD",
            "summary": "",
            "color": color,
            "survey_doc_id": doc_oid,
            "fragment_ids": frag_oids,
            "centroid": centroid,
            "size": len(frag_oids),
            "created_at": datetime.now(timezone.utc),
        })

        db["fragments"].update_many(
            {"_id": {"$in": frag_oids}},
            {"$set": {"cluster_id": cluster_oid}},
        )

        # LLM labelling
        text_frags = [f for f in frags if f.get("redacted_text")][:10]
        if text_frags:
            result = labeller.label_cluster([f["redacted_text"] for f in text_frags])
            db["clusters"].update_one(
                {"_id": cluster_oid},
                {"$set": {"label": result["label"], "summary": result["summary"]}},
            )
            labelled.append({"cluster_id": str(cluster_oid), "label": result["label"]})

        cluster_ids.append(str(cluster_oid))

    return {"cluster_ids": cluster_ids, "labelled": labelled}
