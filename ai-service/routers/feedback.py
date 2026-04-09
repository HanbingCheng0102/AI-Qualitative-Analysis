"""
POST /feedback/recluster
Records a manual re-coding event (user dragged a fragment to a different cluster)
and re-labels the two affected clusters.
"""
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


@router.post("/recluster")
def record_feedback(req: FeedbackRequest):
    """
    Record a re-coding event and re-label the two affected clusters.
    Returns {ok: true}.
    """
    db = get_db()

    try:
        frag_oid = ObjectId(req.fragment_id)
        from_oid = ObjectId(req.from_cluster_id)
        to_oid = ObjectId(req.to_cluster_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId in request.")

    # Verify fragment exists
    frag = db["fragments"].find_one({"_id": frag_oid})
    if not frag:
        raise HTTPException(status_code=404, detail="Fragment not found.")

    # Record in clusterFeedback collection
    db["clusterFeedback"].insert_one({
        "fragment_id": frag_oid,
        "from_cluster_id": from_oid,
        "to_cluster_id": to_oid,
        "timestamp": datetime.now(timezone.utc),
        "user_note": req.user_note,
    })

    # Move fragment to new cluster
    db["fragments"].update_one(
        {"_id": frag_oid},
        {"$set": {"feedback_cluster_id": to_oid}},
    )

    # Update fragment_ids lists on both clusters
    db["clusters"].update_one(
        {"_id": from_oid},
        {"$pull": {"fragment_ids": frag_oid}},
    )
    db["clusters"].update_one(
        {"_id": to_oid},
        {"$addToSet": {"fragment_ids": frag_oid}},
    )

    # Re-label both affected clusters
    for cluster_oid in (from_oid, to_oid):
        cluster = db["clusters"].find_one({"_id": cluster_oid})
        if not cluster:
            continue
        fragments = list(
            db["fragments"].find(
                {"cluster_id": cluster_oid, "redacted_text": {"$ne": None}},
                {"redacted_text": 1},
                limit=10,
            )
        )
        if not fragments:
            continue
        sample_texts = [f["redacted_text"] for f in fragments]
        result = labeller.label_cluster(sample_texts)
        db["clusters"].update_one(
            {"_id": cluster_oid},
            {"$set": {"label": result["label"], "summary": result["summary"]}},
        )

    return {"ok": True}
