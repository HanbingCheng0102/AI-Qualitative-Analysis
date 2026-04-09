from pydantic import BaseModel


class ClusterOut(BaseModel):
    id: str
    label: str
    summary: str
    color: str
    survey_doc_id: str
    size: int
    umap_x: float | None = None
    umap_y: float | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str          # "theme" or "response"
    x: float
    y: float
    size: float
    color: str


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
