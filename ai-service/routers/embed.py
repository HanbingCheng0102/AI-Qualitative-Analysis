"""
POST /embed/fragments
Loads fragments for a doc_id, embeds their redacted_text,
and writes the embedding back to MongoDB.
"""
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import embedder
from services.mongo_client import get_db

router = APIRouter()


class EmbedRequest(BaseModel):
    doc_id: str


@router.post("/fragments")
def embed_fragments(req: EmbedRequest):
    """
    Embed all fragments for a given doc_id.
    Returns {embedded_count}.
    """
    db = get_db()

    try:
        doc_oid = ObjectId(req.doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doc_id")

    fragments = list(
        db["fragments"].find(
            {"docid": doc_oid, "redacted_text": {"$ne": None}},
            {"_id": 1, "redacted_text": 1},
        )
    )

    if not fragments:
        raise HTTPException(
            status_code=404,
            detail="No fragments with redacted_text found for this doc_id.",
        )

    texts = [f["redacted_text"] for f in fragments]
    vectors = embedder.embed(texts)

    # Bulk update
    from pymongo import UpdateOne
    ops = [
        UpdateOne({"_id": f["_id"]}, {"$set": {"embedding": v}})
        for f, v in zip(fragments, vectors)
    ]
    db["fragments"].bulk_write(ops)

    return {"embedded_count": len(ops)}
