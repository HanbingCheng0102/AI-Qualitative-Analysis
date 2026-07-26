from __future__ import annotations

import sys
import unittest
from pathlib import Path


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from services import llm_schemas


class StructuredOutputSchemaTests(unittest.TestCase):
    def test_relevance_schema_is_closed_and_requires_boolean(self):
        schema = llm_schemas.build_relevance_spec().schema

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(["relevant"], schema["required"])
        self.assertEqual(
            {"type": "boolean"},
            schema["properties"]["relevant"],
        )

    def test_initial_cluster_schema_is_closed_and_requires_text_fields(self):
        schema = llm_schemas.build_initial_cluster_spec().schema

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(["label", "summary"], schema["required"])
        self.assertEqual(
            {"type": "string"},
            schema["properties"]["label"],
        )
        self.assertEqual(
            {"type": "string"},
            schema["properties"]["summary"],
        )

    def test_assignment_schema_sorts_and_deduplicates_dynamic_ids(self):
        schema = llm_schemas.build_assignment_spec([7, 3, 7]).schema
        branches = schema["properties"]["decision"]["anyOf"]

        self.assertEqual(
            [3, 7],
            branches[0]["properties"]["cluster_id"]["enum"],
        )
        self.assertEqual(
            ["assign"],
            branches[0]["properties"]["action"]["enum"],
        )
        self.assertEqual(
            ["new"],
            branches[1]["properties"]["action"]["enum"],
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(branches[0]["additionalProperties"])
        self.assertFalse(branches[1]["additionalProperties"])

    def test_assignment_schema_matches_the_capability_probe_hash(self):
        schema = llm_schemas.build_assignment_spec([0]).schema

        self.assertEqual(
            "94b4e83a001b59faa1006e5e9ec6711a17c08572147112f8c9824a447ea12848",
            llm_schemas.canonical_schema_sha256(schema),
        )

    def test_assignment_schema_rejects_invalid_id_sets(self):
        invalid_values = (
            [],
            [-1],
            [True],
            ["0"],
        )
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                llm_schemas.build_assignment_spec(value)

    def test_schema_builds_do_not_share_mutable_state(self):
        first = llm_schemas.build_assignment_spec([0]).schema
        second = llm_schemas.build_assignment_spec([0]).schema

        first["properties"]["decision"]["anyOf"][0]["properties"][
            "cluster_id"
        ]["enum"].append(99)

        self.assertEqual(
            [0],
            second["properties"]["decision"]["anyOf"][0]["properties"][
                "cluster_id"
            ]["enum"],
        )

    def test_schema_transport_is_explicit_per_backend(self):
        self.assertEqual(
            "ollama_api_generate_format",
            llm_schemas.schema_transport_for_backend("ollama"),
        )
        self.assertEqual(
            "openai_chat_completions_response_format_json_schema",
            llm_schemas.schema_transport_for_backend("azure"),
        )
        self.assertEqual(
            "unsupported",
            llm_schemas.schema_transport_for_backend("anthropic"),
        )


if __name__ == "__main__":
    unittest.main()
