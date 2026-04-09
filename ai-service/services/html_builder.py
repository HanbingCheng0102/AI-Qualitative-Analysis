"""
Converts a survey row (dict of question→answer) to NIE HTML fragment format.
Must match the output of content-scripts/surveyConverter.js exactly so that
existing NIE functions (survey_AnswersToASpecificQuestion) work unchanged.

Output format:
  <li class="qna q_COLUMN_NAME">
    <p class="question">Column Name</p>
    <p class="answer">Answer text</p>
  </li>
"""
import re


def _safe_class_name(col: str) -> str:
    """Convert column name to a valid CSS class name."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", col).strip("_")


def response_to_html(row: dict, question_columns: list[str]) -> str:
    """
    Build a full HTML fragment for one survey response row.

    Args:
        row: dict mapping column name → cell value
        question_columns: ordered list of columns to include

    Returns:
        HTML string — a <ul> containing one <li class="qna"> per question
    """
    items = []
    for col in question_columns:
        answer = str(row.get(col, "")).strip()
        if not answer or answer.lower() in ("nan", "none", ""):
            continue
        cls = _safe_class_name(col)
        items.append(
            f'  <li class="qna q_{cls}">\n'
            f'    <p class="question">{col}</p>\n'
            f'    <p class="answer">{answer}</p>\n'
            f"  </li>"
        )
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def full_document_html(survey_name: str, responses_html: list[str]) -> str:
    """Wraps all response fragments into a single document HTML."""
    items = "\n".join(f"<li>{html}</li>" for html in responses_html)
    return f"<html><body><h1>{survey_name}</h1><ol>{items}</ol></body></html>"
