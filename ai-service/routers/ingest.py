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
    filename = file.filename.lower()

    db = get_db()
    doc_id = ObjectId()
    fragments = []
    all_response_html = []

    if filename.endswith(".txt"):
        # Split plain text into paragraphs
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

        import re
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 20]

        if not paragraphs:
            raise HTTPException(status_code=400, detail="No text content found in file.")

        for i, para in enumerate(paragraphs):
            redaction = ner_redactor.redact(para)
            frag_html = f'<p class="text-fragment">{para}</p>'
            all_response_html.append(frag_html)

            frag = {
                "_id": ObjectId(),
                "name": f"Paragraph {i + 1}",
                "docid": doc_id,
                "html": frag_html,
                "data": None,
                "type": "text",
                "coords": None,
                "tags": [],
                "redacted_text": redaction["redacted_text"],
                "embedding": None,
                "cluster_id": None,
                "cluster_label": None,
                "feedback_cluster_id": None,
            }
            fragments.append(frag)

    else:
        # CSV / XLSX
        try:
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                df = pd.read_excel(io.BytesIO(content), dtype=str)
            else:
                df = pd.read_csv(io.BytesIO(content), dtype=str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

        df = df.fillna("")
        question_cols = [c for c in df.columns if _is_question_col(c)]

        if not question_cols:
            raise HTTPException(status_code=400, detail="No question columns detected.")

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            row_dict = row.to_dict()

            for col in question_cols:
                answer = str(row_dict.get(col, "")).strip()
                if not answer or answer.lower() in ("nan", "none", ""):
                    continue

                redaction = ner_redactor.redact(answer)
                frag_html = html_builder.response_to_html({col: answer}, [col])
                all_response_html.append(frag_html)

                frag = {
                    "_id": ObjectId(),
                    "name": f"R{row_num} \u2014 {col}",
                    "docid": doc_id,
                    "html": frag_html,
                    "data": None,
                    "type": "survey",
                    "coords": None,
                    "tags": [],
                    "survey_question_key": col,
                    "row_data": row_dict,  # full CSV row — enables structured column filters
                    "row_num": row_num,
                    "redacted_text": redaction["redacted_text"],
                    "embedding": None,
                    "cluster_id": None,
                    "cluster_label": None,
                    "feedback_cluster_id": None,
                }
                fragments.append(frag)

    doc = {
        "_id": doc_id,
        "name": survey_name,
        "html": html_builder.full_document_html(survey_name, all_response_html),
        "data": None,
        "type": "text" if filename.endswith(".txt") else "survey",
        "tags": [],
        "created_at": datetime.now(timezone.utc),
        "fragment_count": len(fragments),
    }

    db["documents"].insert_one(doc)
    if fragments:
        db["fragments"].insert_many(fragments)

    return {"doc_id": str(doc_id), "fragment_count": len(fragments)}
