"""
Sentence embedding using sentence-transformers.
Model: all-MiniLM-L6-v2 (384 dims, fast, good for short texts)
"""
from sentence_transformers import SentenceTransformer

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings. Returns a list of 384-dim float vectors.
    Empty/None strings are embedded as zero vectors.
    """
    model = _get_model()
    safe_texts = [t if t and t.strip() else " " for t in texts]
    vectors = model.encode(safe_texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()


def embed_single(text: str) -> list[float]:
    return embed([text])[0]
