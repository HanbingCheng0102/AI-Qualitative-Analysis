import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("formal_session_integrity.py")
SPEC = importlib.util.spec_from_file_location("formal_session_integrity", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BrowserErrorTests(unittest.TestCase):
    def test_null_is_an_empty_log(self):
        self.assertEqual([], MODULE.parse_browser_errors("null"))

    def test_non_array_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.parse_browser_errors('{"action": "move"}')

    def test_integrity_count_uses_participant_doc_and_action_scope(self):
        entries = [
            {"participant": "P1", "doc_id": "doc-a", "action": "confirm"},
            {"participant": "p1", "doc_id": "doc-a", "action": "move"},
            {"participant": "P2", "doc_id": "doc-a", "action": "move"},
            {"participant": "P1", "doc_id": "doc-b", "action": "move"},
            {"participant": "P1", "doc_id": "doc-a", "action": "note"},
        ]
        self.assertEqual(
            2,
            MODULE.count_integrity_errors(entries, "P1", {"doc-a"}),
        )


class EndpointTests(unittest.TestCase):
    def test_pilot_endpoint_is_exact(self):
        MODULE._validate_endpoint("mongodb://127.0.0.1:27018/", "nie_pilot", "pilot")
        with self.assertRaises(ValueError):
            MODULE._validate_endpoint("mongodb://127.0.0.1:27017/", "nie_pilot", "pilot")

    def test_formal_endpoint_is_exact(self):
        MODULE._validate_endpoint("mongodb://localhost:27017/", "nie", "formal")
        with self.assertRaises(ValueError):
            MODULE._validate_endpoint("mongodb://localhost:27018/", "nie", "formal")


class AssignmentTests(unittest.TestCase):
    def test_each_formal_participant_has_three_documents(self):
        for participant in ("P1", "P2", "P3"):
            self.assertEqual(3, len(MODULE._document_set("formal", participant)))

    def test_pilot_uses_p2_rehearsal_documents(self):
        documents = MODULE._document_set("pilot", "PILOT")
        self.assertEqual(
            ["P2_task1_batchB", "P2_task2_batchC", "P2_task3_batchA"],
            [document.name for document in documents],
        )


if __name__ == "__main__":
    unittest.main()

