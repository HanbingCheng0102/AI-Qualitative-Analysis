"""Canonical structured-output schemas for Stage D G2 clustering."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


SCHEMA_VERSION = "stage_d_structured_output_v1"

RELEVANCE_SCHEMA_NAME = "stage_d_relevance_v1"
INITIAL_CLUSTER_SCHEMA_NAME = "stage_d_initial_cluster_v1"
ASSIGNMENT_SCHEMA_NAME = "stage_d_assignment_v1"


@dataclass(frozen=True)
class StructuredOutputSpec:
    """A provider-neutral schema name and JSON Schema object."""

    name: str
    schema: dict[str, object]


def canonical_schema_sha256(schema: dict[str, object]) -> str:
    encoded = json.dumps(
        schema,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_relevance_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        name=RELEVANCE_SCHEMA_NAME,
        schema={
            "type": "object",
            "properties": {
                "relevant": {"type": "boolean"},
            },
            "required": ["relevant"],
            "additionalProperties": False,
        },
    )


def build_initial_cluster_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        name=INITIAL_CLUSTER_SCHEMA_NAME,
        schema={
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["label", "summary"],
            "additionalProperties": False,
        },
    )


def _normalise_cluster_ids(valid_cluster_ids: list[int]) -> list[int]:
    if not valid_cluster_ids:
        raise ValueError(
            "Assignment schema requires at least one valid cluster ID."
        )
    if any(type(cluster_id) is not int or cluster_id < 0 for cluster_id in valid_cluster_ids):
        raise ValueError(
            "Assignment schema cluster IDs must be non-negative integers."
        )
    return sorted(set(valid_cluster_ids))


def build_assignment_spec(
    valid_cluster_ids: list[int],
) -> StructuredOutputSpec:
    legal_ids = _normalise_cluster_ids(valid_cluster_ids)
    return StructuredOutputSpec(
        name=ASSIGNMENT_SCHEMA_NAME,
        schema={
            "type": "object",
            "properties": {
                "decision": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["assign"],
                                },
                                "cluster_id": {
                                    "type": "integer",
                                    "enum": legal_ids,
                                },
                            },
                            "required": ["action", "cluster_id"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["new"],
                                },
                                "label": {"type": "string"},
                                "summary": {"type": "string"},
                            },
                            "required": ["action", "label", "summary"],
                            "additionalProperties": False,
                        },
                    ]
                }
            },
            "required": ["decision"],
            "additionalProperties": False,
        },
    )


def schema_transport_for_backend(backend: str) -> str:
    if backend == "ollama":
        return "ollama_api_generate_format"
    if backend in {"azure", "openai"}:
        return "openai_chat_completions_response_format_json_schema"
    return "unsupported"
