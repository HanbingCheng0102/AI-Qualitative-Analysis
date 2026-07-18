"""
POST /cluster/run      — run UMAP + HDBSCAN on a survey's fragments
GET  /cluster/{id}/graph-data — return Sigma.js-ready graph data
"""
import random
from datetime import datetime, timezone

import numpy as np
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routers.label_freeze import reject_if_labels_frozen
from services import clusterer
from services.mongo_client import get_db
from models.cluster_schema import GraphData, GraphEdge, GraphNode

router = APIRouter()

# Colour palette for clusters
_PALETTE = [
    "#4CAF50", "#2196F3", "#FF5722", "#9C27B0", "#FF9800",
    "#00BCD4", "#E91E63", "#3F51B5", "#8BC34A", "#FFC107",
    "#009688", "#F44336", "#673AB7", "#03A9F4", "#CDDC39",
]


class ClusterRequest(BaseModel):
    doc_id: str
    min_cluster_size: int = 5


@router.post("/run")
def run_clustering(req: ClusterRequest):
    """
    Run clustering on all embedded fragments for a doc_id.
    Creates cluster documents and updates fragment.cluster_id.
    Returns {cluster_count, noise_count, cluster_ids}.
    """
    reject_if_labels_frozen("cluster_run")
    db = get_db()

    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    fragments = list(
        db["fragments"].find(
            {"docid": doc_oid, "embedding": {"$ne": None}},
            {"_id": 1, "embedding": 1},
        )
    )

    if len(fragments) < req.min_cluster_size:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {req.min_cluster_size} embedded fragments to cluster.",
        )

    embeddings = [f["embedding"] for f in fragments]
    result = clusterer.run(embeddings, min_cluster_size=req.min_cluster_size)
    labels = result["labels"]
    xs = result["umap_x"]
    ys = result["umap_y"]

    unique_labels = sorted(set(labels))
    noise_count = labels.count(-1)

    # Remove any existing clusters for this doc
    db["clusters"].delete_many({"survey_doc_id": doc_oid})

    cluster_id_map: dict[int, ObjectId] = {}
    cluster_docs = []

    for i, lbl in enumerate(unique_labels):
        indices = [j for j, l in enumerate(labels) if l == lbl]
        fragment_ids = [fragments[j]["_id"] for j in indices]

        # Centroid in original embedding space
        emb_matrix = np.array([embeddings[j] for j in indices])
        centroid = emb_matrix.mean(axis=0).tolist()

        # Mean UMAP position for the cluster node
        cx = float(np.mean([xs[j] for j in indices]))
        cy = float(np.mean([ys[j] for j in indices]))

        color = _PALETTE[i % len(_PALETTE)] if lbl != -1 else "#9E9E9E"
        cluster_oid = ObjectId()
        cluster_id_map[lbl] = cluster_oid

        cluster_docs.append({
            "_id": cluster_oid,
            "label": "Uncategorised" if lbl == -1 else "TBD",
            "summary": "",
            "color": color,
            "survey_doc_id": doc_oid,
            "fragment_ids": fragment_ids,
            "centroid": centroid,
            "umap_x": cx,
            "umap_y": cy,
            "size": len(fragment_ids),
            "created_at": datetime.now(timezone.utc),
        })

    if cluster_docs:
        db["clusters"].insert_many(cluster_docs)

    # Update each fragment with cluster_id and umap coords
    from pymongo import UpdateOne
    ops = []
    for j, frag in enumerate(fragments):
        lbl = labels[j]
        ops.append(
            UpdateOne(
                {"_id": frag["_id"]},
                {"$set": {
                    "cluster_id": cluster_id_map[lbl],
                    "umap_x": xs[j],
                    "umap_y": ys[j],
                }},
            )
        )
    db["fragments"].bulk_write(ops)

    non_noise = [d for d in cluster_docs if d["label"] != "Uncategorised"]
    return {
        "cluster_count": len(non_noise),
        "noise_count": noise_count,
        "cluster_ids": [str(d["_id"]) for d in non_noise],
    }


@router.get("/{cluster_id}/graph-data", response_model=GraphData)
def get_graph_data(cluster_id: str):
    """
    Returns Sigma.js-ready graph data for a single cluster:
    one theme node + one response node per fragment, with edges.
    """
    db = get_db()

    try:
        oid = ObjectId(cluster_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cluster_id")

    cluster = db["clusters"].find_one({"_id": oid})
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    fragments = list(
        db["fragments"].find(
            {"cluster_id": oid},
            {"_id": 1, "name": 1, "umap_x": 1, "umap_y": 1},
        )
    )

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    color = cluster.get("color", "#2196F3")

    # Theme node (the cluster centroid)
    theme_id = str(cluster["_id"])
    nodes.append(GraphNode(
        id=theme_id,
        label=cluster.get("label", "Cluster"),
        type="theme",
        x=cluster.get("umap_x", 0.0),
        y=cluster.get("umap_y", 0.0),
        size=20.0,
        color=color,
    ))

    # Response nodes
    for frag in fragments:
        frag_id = str(frag["_id"])
        nodes.append(GraphNode(
            id=frag_id,
            label=frag.get("name", "Response"),
            type="response",
            x=frag.get("umap_x", 0.0),
            y=frag.get("umap_y", 0.0),
            size=5.0,
            color=color,
        ))
        edges.append(GraphEdge(source=theme_id, target=frag_id))

    return GraphData(nodes=nodes, edges=edges)
