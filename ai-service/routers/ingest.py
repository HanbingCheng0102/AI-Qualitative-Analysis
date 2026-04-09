"""
POST /ingest/survey
Parses a CSV or XLSX file, runs NER redaction on each response,
builds NIE HTML fragments and writes them to MongoDB.
"""
import io
from datetime import datetime, timezone

import pandas as pd
from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services import ner_redactor, html_builder
from services.mongo_client import get_db

router = APIRouter()

# Columns that are metadata, not free-text survey responses
_META_COLS = {"id", "respondent_id", "timestamp", "date", "time", "site", "ward"}


def _is_question_col(col: str) -> bool:
    return col.strip().lower() not in _META_COLS


@router.post("/survey")
async def ingest_survey(
    file: UploadFile = File(...),
    survey_name: str = Form(...),
):
    """
    Upload a CSV or XLSX survey file.
    Returns {doc_id, fragment_count}.
    """
    content = await file.read()

    # Parse
    try:
        if file.filename.endswith(".xlsx") or file.filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(content), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    df = df.fillna("")
    question_cols = [c for c in df.columns if _is_question_col(c)]

    if not question_cols:
        raise HTTPException(status_code=400, detail="No question columns detected.")

    db = get_db()
    doc_id = ObjectId()

    # Build and insert fragments
    fragments = []
    all_response_html = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()

        # Concatenate all answers for embedding later
        combined_text = " ".join(
            str(row_dict.get(col, "")) for col in question_cols
        ).strip()

        redaction = ner_redactor.redact(combined_text)
        frag_html = html_builder.response_to_html(row_dict, question_cols)
        all_response_html.append(frag_html)

        frag = {
            "_id": ObjectId(),
            "name": f"Response {len(fragments) + 1}",
            "docid": doc_id,
            "html": frag_html,
            "data": None,
            "type": "survey",
            "coords": None,
            "tags": [],
            "survey_question_key": ",".join(question_cols),
            "redacted_text": redaction["redacted_text"],
            "embedding": None,
            "cluster_id": None,
            "cluster_label": None,
            "feedback_cluster_id": None,
        }
        fragments.append(frag)

    # Build parent document
    doc = {
        "_id": doc_id,
        "name": survey_name,
        "html": html_builder.full_document_html(survey_name, all_response_html),
        "data": None,
        "type": "survey",
        "tags": [],
        "created_at": datetime.now(timezone.utc),
        "fragment_count": len(fragments),
    }

    db["documents"].insert_one(doc)
    if fragments:
        db["fragments"].insert_many(fragments)

    return {"doc_id": str(doc_id), "fragment_count": len(fragments)}
