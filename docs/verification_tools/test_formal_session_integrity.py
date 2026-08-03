import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId


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


class ParticipantFeedbackScopeTests(unittest.TestCase):
    def _registered_events(self):
        return [
            {
                "_id": ObjectId(feedback_id),
                "doc_id": ObjectId(specification["doc_id"]),
                "participant_id": "P1",
                "action": specification["action"],
                "timestamp": datetime.fromisoformat(
                    specification["timestamp"].replace("Z", "+00:00")
                ),
            }
            for feedback_id, specification in
            MODULE.HISTORICAL_FEEDBACK_EXCLUSIONS["P1"].items()
        ]

    def test_exact_registered_development_events_are_excluded(self):
        errors, details = MODULE.evaluate_participant_feedback_scope(
            self._registered_events(),
            "P1",
            {"formal-a", "formal-b", "formal-c"},
        )

        self.assertEqual([], errors)
        self.assertEqual(
            sorted(MODULE.HISTORICAL_FEEDBACK_EXCLUSIONS["P1"]),
            details["pre_registered_excluded_feedback_ids"],
        )
        self.assertEqual([], details["out_of_assignment_doc_ids"])

    def test_new_event_on_same_development_document_is_not_excluded(self):
        events = self._registered_events()
        events.append({
            "_id": ObjectId(),
            "doc_id": ObjectId("6a5616310536f5c49a509277"),
            "participant_id": "P1",
            "action": "confirm",
            "timestamp": datetime.now(timezone.utc),
        })

        errors, details = MODULE.evaluate_participant_feedback_scope(
            events,
            "P1",
            {"formal-a", "formal-b", "formal-c"},
        )

        self.assertIn(
            "participant has feedback outside the assigned three documents",
            errors,
        )
        self.assertEqual(
            ["6a5616310536f5c49a509277"],
            details["out_of_assignment_doc_ids"],
        )

    def test_registered_event_fingerprint_change_is_rejected(self):
        events = self._registered_events()
        events[0]["action"] = "confirm"

        errors, _ = MODULE.evaluate_participant_feedback_scope(
            events,
            "P1",
            {"formal-a", "formal-b", "formal-c"},
        )

        self.assertTrue(
            any("fingerprint mismatch" in error for error in errors)
        )

    def test_missing_registered_event_is_rejected(self):
        events = self._registered_events()[1:]

        errors, details = MODULE.evaluate_participant_feedback_scope(
            events,
            "P1",
            {"formal-a", "formal-b", "formal-c"},
        )

        self.assertIn(
            "pre-registered historical feedback is absent or deleted",
            errors,
        )
        self.assertEqual(1, len(details["missing_pre_registered_feedback_ids"]))


class PostMoveProjectionTests(unittest.TestCase):
    def setUp(self):
        self.cluster_a = ObjectId()
        self.cluster_b = ObjectId()
        self.fragment_a = ObjectId()
        self.fragment_b = ObjectId()

    def test_no_move_still_checks_all_eligible_fragments(self):
        fragments = {
            str(self.fragment_a): {
                "_id": self.fragment_a,
                "cluster_id": self.cluster_a,
                "feedback_cluster_id": None,
            },
            str(self.fragment_b): {
                "_id": self.fragment_b,
                "cluster_id": self.cluster_b,
                "feedback_cluster_id": None,
            },
        }
        clusters = {
            str(self.cluster_a): {"_id": self.cluster_a, "fragment_ids": [self.fragment_a]},
            str(self.cluster_b): {"_id": self.cluster_b, "fragment_ids": [self.fragment_b]},
        }

        errors, details = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [],
        )

        self.assertEqual([], errors)
        self.assertEqual("all_eligible", details["scope"])
        self.assertEqual(2, details["eligible_fragments"])
        self.assertEqual(0, details["moved_fragments"])

    def test_unmoved_duplicate_membership_is_rejected(self):
        fragments = {
            str(self.fragment_a): {
                "_id": self.fragment_a,
                "cluster_id": self.cluster_a,
                "feedback_cluster_id": None,
            },
        }
        clusters = {
            str(self.cluster_a): {"_id": self.cluster_a, "fragment_ids": [self.fragment_a]},
            str(self.cluster_b): {"_id": self.cluster_b, "fragment_ids": [self.fragment_a]},
        }

        errors, _ = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [],
        )

        self.assertTrue(any("2 current cluster memberships" in error for error in errors))

    def test_unmoved_missing_membership_is_rejected(self):
        fragments = {
            str(self.fragment_a): {
                "_id": self.fragment_a,
                "cluster_id": self.cluster_a,
                "feedback_cluster_id": None,
            },
        }
        clusters = {
            str(self.cluster_a): {"_id": self.cluster_a, "fragment_ids": []},
        }

        errors, _ = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [],
        )

        self.assertTrue(any("0 current cluster memberships" in error for error in errors))

    def test_unmoved_membership_cluster_must_match_fragment_cluster(self):
        fragments = {
            str(self.fragment_a): {
                "_id": self.fragment_a,
                "cluster_id": self.cluster_a,
                "feedback_cluster_id": None,
            },
        }
        clusters = {
            str(self.cluster_a): {"_id": self.cluster_a, "fragment_ids": []},
            str(self.cluster_b): {"_id": self.cluster_b, "fragment_ids": [self.fragment_a]},
        }

        errors, _ = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [],
        )

        self.assertTrue(
            any("membership disagrees with fragment.cluster_id" in error for error in errors)
        )

    def test_moved_fragment_retains_final_projection_checks(self):
        event = {
            "_id": ObjectId(),
            "fragment_id": self.fragment_a,
            "from_cluster_id": self.cluster_a,
            "to_cluster_id": self.cluster_b,
            "timestamp": datetime.now(timezone.utc),
        }
        fragments = {
            str(self.fragment_a): {
                "_id": self.fragment_a,
                "cluster_id": self.cluster_b,
                "feedback_cluster_id": self.cluster_b,
            },
        }
        clusters = {
            str(self.cluster_a): {"_id": self.cluster_a, "fragment_ids": []},
            str(self.cluster_b): {"_id": self.cluster_b, "fragment_ids": [self.fragment_a]},
        }

        errors, details = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [event],
        )

        self.assertEqual([], errors)
        self.assertEqual(1, details["moved_fragments"])

        fragments[str(self.fragment_a)]["feedback_cluster_id"] = self.cluster_a
        errors, _ = MODULE.evaluate_post_move_projection(
            fragments,
            clusters,
            set(fragments),
            [event],
        )
        self.assertTrue(
            any("feedback_cluster_id disagrees with final move" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()

