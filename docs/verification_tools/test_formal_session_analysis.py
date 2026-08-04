import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).parent

INTEGRITY_SPEC = importlib.util.spec_from_file_location(
    "formal_session_integrity",
    TOOLS_DIR / "formal_session_integrity.py",
)
INTEGRITY = importlib.util.module_from_spec(INTEGRITY_SPEC)
sys.modules[INTEGRITY_SPEC.name] = INTEGRITY
INTEGRITY_SPEC.loader.exec_module(INTEGRITY)

ANALYSIS_SPEC = importlib.util.spec_from_file_location(
    "formal_session_analysis",
    TOOLS_DIR / "formal_session_analysis.py",
)
ANALYSIS = importlib.util.module_from_spec(ANALYSIS_SPEC)
sys.modules[ANALYSIS_SPEC.name] = ANALYSIS
ANALYSIS_SPEC.loader.exec_module(ANALYSIS)


class EndpointTests(unittest.TestCase):
    def test_analysis_endpoint_is_exact(self):
        ANALYSIS._validate_analysis_endpoint(
            "mongodb://127.0.0.1:27019/", "nie_analysis"
        )

    def test_formal_and_pilot_endpoints_are_rejected(self):
        for port in (27017, 27018):
            with self.assertRaises(ValueError):
                ANALYSIS._validate_analysis_endpoint(
                    f"mongodb://127.0.0.1:{port}/", "nie_analysis"
                )

    def test_database_and_credentials_are_rejected(self):
        with self.assertRaises(ValueError):
            ANALYSIS._validate_analysis_endpoint(
                "mongodb://127.0.0.1:27019/", "nie"
            )
        with self.assertRaises(ValueError):
            ANALYSIS._validate_analysis_endpoint(
                "mongodb://user:secret@127.0.0.1:27019/", "nie_analysis"
            )


class IntegrityInputTests(unittest.TestCase):
    def _minimal_result(self, participant):
        docs = INTEGRITY._document_set("formal", participant)
        return {
            "schema": INTEGRITY.INTEGRITY_SCHEMA_VERSION,
            "mode": "formal",
            "database": "nie",
            "participant": participant,
            "endpoint": "127.0.0.1:27017",
            "overall_status": "PASS",
            "repository_head": ANALYSIS.INTEGRITY_TOOL_HEAD,
            "repository_worktree_clean": True,
            "check6_scope": INTEGRITY.CHECK6_SCOPE,
            "historical_feedback_exclusion_version": (
                INTEGRITY.HISTORICAL_FEEDBACK_EXCLUSION_VERSION
            ),
            "integrity_N": 0,
            "documents": [
                {"doc_id": doc.doc_id, "run_id": doc.run_id} for doc in docs
            ],
        }

    def test_integrity_identity_is_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "P1.json"
            result = self._minimal_result("P1")
            path.write_text(json.dumps(result), encoding="utf-8")
            loaded = ANALYSIS._load_integrity_result(path, "P1")
            self.assertEqual(0, loaded["integrity_N"])
            result["repository_head"] = "wrong"
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(ValueError):
                ANALYSIS._load_integrity_result(path, "P1")

    def test_integrity_n_may_be_nonzero_but_not_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "P2.json"
            result = self._minimal_result("P2")
            result["integrity_N"] = 2
            path.write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual(2, ANALYSIS._load_integrity_result(path, "P2")["integrity_N"])
            result["integrity_N"] = -1
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(ValueError):
                ANALYSIS._load_integrity_result(path, "P2")


class MetricTests(unittest.TestCase):
    def _check4(self, **details):
        return {
            "checks": [
                {
                    "check": 4,
                    "status": "PASS",
                    "details": details,
                }
            ]
        }

    def test_latest_partition_closes(self):
        values = ANALYSIS._latest_details(
            self._check4(
                confirm=2,
                move=1,
                no_recorded_decision=1,
                eligible=4,
                raw_valid_events=5,
                distinct_reviewed_fragments=3,
            )
        )
        self.assertEqual(4, values["eligible"])

    def test_latest_partition_rejects_bad_arithmetic(self):
        with self.assertRaises(ValueError):
            ANALYSIS._latest_details(
                self._check4(
                    confirm=2,
                    move=1,
                    no_recorded_decision=2,
                    eligible=4,
                    raw_valid_events=3,
                    distinct_reviewed_fragments=3,
                )
            )

    def test_aggregate_is_descriptive_and_closes(self):
        rows = [
            {
                "model": "m",
                "eligible": 4,
                "final_confirm": 2,
                "final_move": 1,
                "no_recorded_decision": 1,
            },
            {
                "model": "m",
                "eligible": 2,
                "final_confirm": 1,
                "final_move": 0,
                "no_recorded_decision": 1,
            },
        ]
        result = ANALYSIS._aggregate(rows, "model")[0]
        self.assertEqual(6, result["eligible"])
        self.assertTrue(result["descriptive_only"])
        self.assertEqual(50.0, result["confirm_coverage_lower_bound"]["percent"])

    def test_document_row_allows_only_check5_na(self):
        class Clusters:
            def count_documents(self, _query):
                return 1

        class Database:
            def __getitem__(self, name):
                self.assert_name = name
                return Clusters()

        doc = INTEGRITY.ApprovedDocument(
            "P1", "doc", "A", "6a6621355e9bd7a009d1b97f",
            "6a66213a5e9bd7a009d1b991", "ollama", "model", 4,
        )
        checks = [
            {"check": number, "status": "PASS", "details": {}}
            for number in range(1, 7)
        ]
        checks[3]["details"] = {
            "confirm": 2,
            "move": 0,
            "no_recorded_decision": 2,
            "eligible": 4,
            "raw_valid_events": 2,
            "distinct_reviewed_fragments": 2,
        }
        checks[4]["status"] = "NA"
        row = ANALYSIS._document_row(Database(), doc, {"checks": checks}, 0)
        self.assertEqual("NA", row["check5_status"])
        self.assertEqual(0, row["participant_integrity_N"])

        checks[5]["status"] = "NA"
        with self.assertRaises(ValueError):
            ANALYSIS._document_row(Database(), doc, {"checks": checks}, 0)


class OutputSafetyTests(unittest.TestCase):
    def test_output_inside_repository_is_rejected(self):
        repo = TOOLS_DIR.parents[1]
        with self.assertRaises(ValueError):
            ANALYSIS._outside_repo_output(
                str(repo / "test-data" / "private" / "result.json"), repo
            )

    def test_source_contains_no_mongodb_write_calls(self):
        source = (TOOLS_DIR / "formal_session_analysis.py").read_text(encoding="utf-8")
        forbidden = (
            ".insert_one(",
            ".insert_many(",
            ".update_one(",
            ".update_many(",
            ".replace_one(",
            ".delete_one(",
            ".delete_many(",
            ".bulk_write(",
            ".drop(",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_participant_integrity_n_is_not_labelled_document_level(self):
        source = (TOOLS_DIR / "formal_session_analysis.py").read_text(encoding="utf-8")
        self.assertIn('"participant_integrity_N"', source)
        self.assertNotIn('"integrity_N": integrity_n', source)


if __name__ == "__main__":
    unittest.main()
