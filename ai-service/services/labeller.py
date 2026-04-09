"""
LLM-based cluster labelling.
Supports three backends: Anthropic, OpenAI, and Ollama (local).
Set LLM_BACKEND=anthropic, openai, or ollama in .env
"""
import os
import json
import httpx

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
LLM_BACKEND = os.environ.get("LLM_BACKEND", "anthropic")


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


def _call_anthropic(prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    content = _strip_markdown(message.content[0].text)
    return json.loads(content)


def _call_openai(prompt: str) -> dict:
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        content = _strip_markdown(resp.json()["choices"][0]["message"]["content"])
        return json.loads(content)


def _call_ollama(prompt: str) -> dict:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        content = _strip_markdown(resp.json()["response"])
        return json.loads(content)


def label_cluster(sample_texts: list[str]) -> dict:
    """
    Args:
        sample_texts: Up to 10 representative response texts for the cluster

    Returns:
        {"label": str, "summary": str}
    """
    prompt = _build_prompt(sample_texts[:10])
    try:
        if LLM_BACKEND == "anthropic":
            return _call_anthropic(prompt)
        elif LLM_BACKEND == "ollama":
            return _call_ollama(prompt)
        else:
            return _call_openai(prompt)
    except (json.JSONDecodeError, KeyError):
        return {"label": "Unlabelled Cluster", "summary": "Could not generate label."}
    except Exception as e:
        return {"label": "Unlabelled Cluster", "summary": f"LLM error: {str(e)}"}
