from pydantic import BaseModel
from typing import Any


class FragmentCreate(BaseModel):
    name: str
    docid: str
    html: str | None = None
    data: Any = None
    type: str = "survey"
    coords: Any = None
    tags: list[str] = []
    survey_question_key: str | None = None
    redacted_text: str | None = None


class FragmentOut(BaseModel):
    id: str
    name: str
    type: str
    cluster_id: str | None = None
    cluster_label: str | None = None
    survey_question_key: str | None = None
    redacted_text: str | None = None
    umap_x: float | None = None
    umap_y: float | None = None
