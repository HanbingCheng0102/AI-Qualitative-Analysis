"""
LLM-based cluster labelling through the shared backend provider.
"""
import json

from services import llm_provider


def _build_prompt(sample_texts: list[str]) -> str:
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(sample_texts))
    return f"""You are analysing NHS patient survey responses. Below are up to 10 responses that belong to the same theme cluster.

{numbered}

Reply with valid JSON only — no markdown, no explanation:
{{"label": "<short theme label, max 6 words>", "summary": "<one sentence describing the common theme>"}}"""


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap JSON in."""
    import re
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def label_cluster(sample_texts: list[str]) -> dict:
    """
    Args:
        sample_texts: Up to 10 representative response texts for the cluster

    Returns:
        {"label": str, "summary": str}
    """
    prompt = _build_prompt(sample_texts[:10])
    try:
        content = llm_provider.call_text(prompt, purpose="labelling")
        return json.loads(_strip_markdown(content))
    except (json.JSONDecodeError, KeyError):
        return {"label": "Unlabelled Cluster", "summary": "Could not generate label."}
    except Exception as e:
        return {"label": "Unlabelled Cluster", "summary": f"LLM error: {str(e)}"}
