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

from services import labeller, llm_clusterer
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


# ── LLM-based placement suggestion ───────────────────────────────────────────

class LLMPlacementRequest(BaseModel):
    doc_id: str
    fragment_id: str
    groups: List[GroupSpec]
    research_question: str = ""


@router.post("/llm-placement")
def suggest_llm_placement(req: LLMPlacementRequest):
    """
    Like /suggest/placement but uses the LLM instead of cosine similarity.
    For each group, fetches up to 4 sample texts so the LLM can read them
    directly and judge semantic fit — no embeddings involved.
    Only called after >= 20 fragments have been placed (enforced by frontend).
    """
    db = get_db()

    try:
        frag_oid = ObjectId(req.fragment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fragment_id")

    frag = db["fragments"].find_one({"_id": frag_oid}, {"redacted_text": 1})
    if not frag or not frag.get("redacted_text"):
        return {"suggestion": None, "reason": "no text"}

    frag_text = frag["redacted_text"]

    # Build a list of groups with sample texts for the LLM prompt
    group_samples: list[dict] = []
    for group in req.groups:
        if not group.fragment_ids:
            continue
        try:
            oids = [ObjectId(fid) for fid in group.fragment_ids]
        except Exception:
            continue

        samples = list(db["fragments"].find(
            {"_id": {"$in": oids}, "redacted_text": {"$ne": None}},
            {"redacted_text": 1},
            limit=4,
        ))
        if not samples:
            continue

        group_samples.append({
            "group_id": group.group_id,
            "texts": [s["redacted_text"] for s in samples],
            "total": len(group.fragment_ids),
        })

    if not group_samples:
        return {"suggestion": {"group_id": None, "confidence": 0.0, "new_cluster": True}}

    # Build the prompt
    rq_line = f"Research focus: {req.research_question}\n\n" if req.research_question.strip() else ""

    groups_text = ""
    for g in group_samples:
        bullet_texts = "\n".join(f'    - "{t}"' for t in g["texts"])
        extra = f" (+ {g['total'] - len(g['texts'])} more)" if g["total"] > len(g["texts"]) else ""
        groups_text += f"Group {g['group_id']} ({g['total']} responses{extra}):\n{bullet_texts}\n\n"

    prompt = f"""{rq_line}You are helping a researcher sort survey responses into groups on a whiteboard.

Current groups and their sample responses:
{groups_text}New response to place:
\"\"\"{frag_text}\"\"\"

Decide which group this response fits best, or whether it needs a new group.
- Assign to an existing group if the response clearly shares the same theme as its samples.
- Suggest a new group only if the response is genuinely different from all existing groups.

Reply with JSON only — no markdown, no explanation.
To assign to a group:  {{"action": "assign", "group_id": "<group id string>", "confidence": <0.0-1.0>}}
To create a new group: {{"action": "new", "confidence": <0.0-1.0>}}"""

    try:
        raw = llm_clusterer._call_llm(prompt)
        result = llm_clusterer._parse_json(raw)
        confidence = float(result.get("confidence", 0.5))

        if result.get("action") == "assign":
            gid = str(result.get("group_id", ""))
            # Validate it's actually one of our groups
            valid_ids = {g["group_id"] for g in group_samples}
            if gid in valid_ids:
                return {"suggestion": {"group_id": gid, "confidence": confidence, "new_cluster": False}}

        # "new" or unrecognised group_id — suggest new cluster
        return {"suggestion": {"group_id": None, "confidence": confidence, "new_cluster": True}}

    except Exception:
        return {"suggestion": None, "reason": "llm_error"}


# ── Sanity check ─────────────────────────────────────────────────────────────

class SanityCheckRequest(BaseModel):
    doc_id: str
    fragment_id: str
    placed_in_group_id: str
    groups: List[GroupSpec]
    research_question: str = ""


@router.post("/sanity-check")
def sanity_check(req: SanityCheckRequest):
    """
    After a user places a fragment, check whether the placement makes sense.
    Uses the LLM to read sample texts from each group and judge fit.
    Returns {"ok": true} if the placement is reasonable, or
    {"ok": false, "suggested_group_id": "X", "reason": "..."} if a better
    group clearly exists.
    """
    db = get_db()

    try:
        frag_oid = ObjectId(req.fragment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fragment_id")

    frag = db["fragments"].find_one({"_id": frag_oid}, {"redacted_text": 1})
    if not frag or not frag.get("redacted_text"):
        return {"ok": True}

    frag_text = frag["redacted_text"]

    # Fetch up to 3 sample texts per group (excluding the fragment itself)
    group_samples: list[dict] = []
    for group in req.groups:
        try:
            oids = [ObjectId(fid) for fid in group.fragment_ids if fid != req.fragment_id]
        except Exception:
            continue
        if not oids:
            continue
        samples = list(db["fragments"].find(
            {"_id": {"$in": oids}, "redacted_text": {"$ne": None}},
            {"redacted_text": 1},
            limit=3,
        ))
        group_samples.append({
            "group_id": group.group_id,
            "texts": [s["redacted_text"] for s in samples],
            "is_placed": group.group_id == req.placed_in_group_id,
        })

    # Need at least the placed group + one other with samples to compare
    other_groups = [g for g in group_samples if not g["is_placed"] and g["texts"]]
    if not other_groups:
        return {"ok": True}

    placed_group = next((g for g in group_samples if g["is_placed"]), None)

    # Build prompt
    rq_line = f"Research focus: {req.research_question}\n\n" if req.research_question.strip() else ""

    if placed_group and placed_group["texts"]:
        placed_bullets = "\n".join(f'    - "{t}"' for t in placed_group["texts"])
        placed_section = f"Group {req.placed_in_group_id} — where the user placed it:\n{placed_bullets}\n\n"
    else:
        placed_section = f"Group {req.placed_in_group_id} — where the user placed it (no other members yet).\n\n"

    other_section = ""
    for g in other_groups:
        bullets = "\n".join(f'    - "{t}"' for t in g["texts"])
        other_section += f"Group {g['group_id']}:\n{bullets}\n\n"

    prompt = f"""{rq_line}You are reviewing a researcher's placement of a survey response on a clustering whiteboard.

{placed_section}Other groups:
{other_section}Response being reviewed:
\"\"\"{frag_text}\"\"\"

The researcher placed this response in Group {req.placed_in_group_id}.

Your default answer is {{"ok": true}}. Only override this if the placement is an obvious, clear-cut mistake — meaning the response has essentially nothing in common with the group it was placed in, AND it unambiguously belongs in one of the other groups instead.

Do NOT flag:
- Borderline cases or minor differences in tone
- Responses that loosely fit multiple groups
- Placements that are reasonable even if not perfect
- Cases where you are uncertain

ONLY flag when you are highly confident the placement is wrong AND a specific other group is a far better match.

Reply with JSON only — no markdown, no explanation.
{{"ok": true}} — placement is fine (use this in most cases)
{{"ok": false, "suggested_group_id": "<id>", "reason": "<one concise sentence>"}} — only if placement is clearly wrong"""

    try:
        raw = llm_clusterer._call_llm(prompt)
        result = llm_clusterer._parse_json(raw)

        if result.get("ok") is not False:
            return {"ok": True}

        suggested = str(result.get("suggested_group_id", ""))
        valid_ids = {g["group_id"] for g in group_samples}

        if suggested not in valid_ids or suggested == req.placed_in_group_id:
            return {"ok": True}

        return {
            "ok": False,
            "suggested_group_id": suggested,
            "reason": result.get("reason", "This response may fit better in another group."),
        }
    except Exception:
        return {"ok": True}  # fail open — never block the user


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
