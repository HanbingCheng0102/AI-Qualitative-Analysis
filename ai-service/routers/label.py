"""
POST /label/clusters
For each cluster_id, sample up to 10 representative fragments
and call the LLM to generate a label and summary.
"""
import numpy as np
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routers.label_freeze import reject_if_labels_frozen
from services import labeller
from services.mongo_client import get_db

router = APIRouter()


class LabelRequest(BaseModel):
    cluster_ids: list[str]


@router.post("/clusters")
def label_clusters(req: LabelRequest):
    """
    Label a list of clusters using the configured LLM backend.
    Returns {labelled: [{cluster_id, label, summary}]}.
    """
    reject_if_labels_frozen("label_clusters")
    db = get_db()
    results = []

    for cid_str in req.cluster_ids:
        try:
            cid = ObjectId(cid_str)
        except Exception:
            continue

        cluster = db["clusters"].find_one({"_id": cid})
        if not cluster:
            continue

        # Fetch top-10 fragments closest to centroid (by cosine similarity)
        centroid = np.array(cluster.get("centroid", []), dtype=np.float32)
        fragments = list(
            db["fragments"].find(
                {"cluster_id": cid, "redacted_text": {"$ne": None}},
                {"_id": 1, "redacted_text": 1, "embedding": 1},
            )
        )

        if not fragments:
            continue

        # Sort by cosine similarity to centroid if embeddings available
        if centroid.size > 0:
            def cosine_sim(frag):
                emb = np.array(frag.get("embedding") or [], dtype=np.float32)
                if emb.size == 0:
                    return 0.0
                norm_e = np.linalg.norm(emb)
                norm_c = np.linalg.norm(centroid)
                if norm_e == 0 or norm_c == 0:
                    return 0.0
                return float(np.dot(emb, centroid) / (norm_e * norm_c))

            fragments.sort(key=cosine_sim, reverse=True)

        sample_texts = [f["redacted_text"] for f in fragments[:10]]
        result = labeller.label_cluster(sample_texts)

        db["clusters"].update_one(
            {"_id": cid},
            {"$set": {"label": result["label"], "summary": result["summary"]}},
        )

        # Also cache label on each fragment for convenience
        db["fragments"].update_many(
            {"cluster_id": cid},
            {"$set": {"cluster_label": result["label"]}},
        )

        results.append({
            "cluster_id": cid_str,
            "label": result["label"],
            "summary": result["summary"],
        })

    return {"labelled": results}
