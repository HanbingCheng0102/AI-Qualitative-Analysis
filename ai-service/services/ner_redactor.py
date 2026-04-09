"""
PII redaction using spaCy NER.
Redacts PERSON and DATE entities, replacing them with typed placeholders.
"""
import spacy

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def redact(text: str) -> dict:
    """
    Returns:
        {
            "redacted_text": str,        # text with entities replaced
            "entities_removed": list     # list of {text, label} dicts
        }
    """
    if not text or not text.strip():
        return {"redacted_text": text, "entities_removed": []}

    nlp = _get_nlp()
    doc = nlp(text)

    entities_removed = []
    redacted = text

    # Process in reverse order so character offsets stay valid
    for ent in reversed(doc.ents):
        if ent.label_ in ("PERSON", "DATE"):
            placeholder = f"[{ent.label_}]"
            entities_removed.append({"text": ent.text, "label": ent.label_})
            redacted = redacted[: ent.start_char] + placeholder + redacted[ent.end_char :]

    return {
        "redacted_text": redacted,
        "entities_removed": list(reversed(entities_removed)),
    }
