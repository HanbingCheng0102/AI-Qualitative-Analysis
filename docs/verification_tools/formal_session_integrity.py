#!/usr/bin/env python3
"""Read-only six-check verifier for the formal-session protocol.

The tool deliberately emits identifiers, counts and PASS/FAIL/NA findings only.
It never reads text-bearing fragment fields and contains no MongoDB write call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from bson import ObjectId
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri


G2 = "544540beedb707c2be5c08fa1647107f80587c84"
SCHEMA_VERSION = "stage_d_structured_output_v1"
INTEGRITY_SCHEMA_VERSION = "formal_session_integrity_v2"
CHECK6_SCOPE = "all_eligible"


@dataclass(frozen=True)
class ApprovedDocument:
    participant: str
    name: str
    batch: str
    doc_id: str
    run_id: str
    backend: str
    model: str
    eligible: int


APPROVED = (
    ApprovedDocument("P1", "P1_task1_batchA", "A", "6a6621355e9bd7a009d1b97f", "6a66213a5e9bd7a009d1b991", "ollama", "llama3.2:3b", 15),
    ApprovedDocument("P1", "P1_task2_batchB", "B", "6a6672adaaaa46976afdb5ba", "6a6672b1aaaa46976afdb5d0", "azure", "Mistral-Large-3", 20),
    ApprovedDocument("P1", "P1_task3_batchC", "C", "6a662813ed5bcd0c9d8a4439", "6a662818ed5bcd0c9d8a444e", "ollama", "qwen2.5:3b", 17),
    ApprovedDocument("P2", "P2_task1_batchB", "B", "6a666d4f04fc296116b621af", "6a666d5404fc296116b621c5", "ollama", "qwen2.5:3b", 16),
    ApprovedDocument("P2", "P2_task2_batchC", "C", "6a662346b88c6db2d9915ac9", "6a66234bb88c6db2d9915ade", "ollama", "llama3.2:3b", 20),
    ApprovedDocument("P2", "P2_task3_batchA", "A", "6a667375aaaa46976afdb5dc", "6a667376aaaa46976afdb5ee", "azure", "Mistral-Large-3", 16),
    ApprovedDocument("P3", "P3_task1_batchC", "C", "6a6673f2aaaa46976afdb5f7", "6a6673f3aaaa46976afdb60c", "azure", "Mistral-Large-3", 19),
    ApprovedDocument("P3", "P3_task2_batchA", "A", "6a666f0d5f60ce182f69ff12", "6a666f125f60ce182f69ff24", "ollama", "qwen2.5:3b", 16),
    ApprovedDocument("P3", "P3_task3_batchB", "B", "6a6625e3460dababa39a9be4", "6a6625e7460dababa39a9bfa", "ollama", "llama3.2:3b", 19),
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _finding(number: int, name: str, errors: list[str], *, applicable: bool = True, details: dict[str, Any] | None = None) -> dict[str, Any]:
    status = "NA" if not applicable else ("FAIL" if errors else "PASS")
    return {
        "check": number,
        "name": name,
        "status": status,
        "errors": errors,
        "details": _json_safe(details or {}),
    }


def _same_id(left: Any, right: Any) -> bool:
    return left is not None and right is not None and str(left) == str(right)


def _expected_params(doc: ApprovedDocument) -> dict[str, Any]:
    expected: dict[str, Any] = {
        "column_filters": {},
        "timeout_seconds": 60,
        "max_retries": 0,
        "temperature": 0,
        "seed": 42,
        "max_tokens": 1024,
        "schema_enforced": True,
        "schema_version": SCHEMA_VERSION,
        "schema_dynamic_cluster_id_enum": True,
    }
    if doc.backend == "azure":
        expected.update({
            "seed_semantics": "best_effort_beta",
            "schema_transport": "openai_chat_completions_response_format_json_schema",
            "provider_protocol": "openai_v1",
            "model_version": "1",
            "deployment_type": "GlobalStandard",
        })
    else:
        expected.update({
            "seed_semantics": "provider_supported",
            "schema_transport": "ollama_api_generate_format",
        })
    return expected


def parse_browser_errors(raw: str) -> list[dict[str, Any]]:
    parsed = json.loads(raw)
    if parsed is None:
        return []
    if not isinstance(parsed, list) or any(not isinstance(item, dict) for item in parsed):
        raise ValueError("Browser failure log must be JSON null or an array of objects.")
    return parsed


def count_integrity_errors(entries: Iterable[dict[str, Any]], participant: str, assigned_doc_ids: set[str]) -> int:
    return sum(
        1
        for item in entries
        if str(item.get("participant", "")).strip().upper() == participant
        and str(item.get("doc_id", "")) in assigned_doc_ids
        and str(item.get("action", "")).strip() in {"confirm", "move"}
    )


def evaluate_post_move_projection(
    fragment_by_id: dict[str, dict[str, Any]],
    cluster_by_id: dict[str, dict[str, Any]],
    eligible_ids: set[str],
    move_events: list[dict[str, Any]],
) -> tuple[list[str], dict[str, int | str]]:
    """Validate the current graph projection for every eligible fragment.

    The move-event checks retain the historical final-destination and
    feedback-cluster assertions.  The membership assertions deliberately cover
    the full eligible set so a no-move document is still checked and baseline
    drift cannot hide behind move-only applicability.
    """
    errors: list[str] = []
    memberships: dict[str, list[str]] = {}
    for cluster_id, cluster in cluster_by_id.items():
        for fragment_oid in cluster.get("fragment_ids") or []:
            memberships.setdefault(str(fragment_oid), []).append(cluster_id)

    for fragment_id in sorted(eligible_ids):
        fragment = fragment_by_id.get(fragment_id) or {}
        current_cluster = fragment.get("cluster_id")
        member_clusters = memberships.get(fragment_id, [])
        if len(member_clusters) != 1:
            errors.append(
                f"eligible fragment has {len(member_clusters)} current cluster memberships: {fragment_id}"
            )
        elif not _same_id(member_clusters[0], current_cluster):
            errors.append(
                f"cluster membership disagrees with fragment.cluster_id for {fragment_id}"
            )

    moved_fragment_ids = sorted({str(event["fragment_id"]) for event in move_events})
    for fragment_id in moved_fragment_ids:
        chain = sorted(
            (event for event in move_events if str(event["fragment_id"]) == fragment_id),
            key=lambda event: (event.get("timestamp"), event.get("_id")),
        )
        final_destination = chain[-1].get("to_cluster_id")
        fragment = fragment_by_id.get(fragment_id) or {}
        if not _same_id(fragment.get("cluster_id"), final_destination):
            errors.append(f"fragment.cluster_id disagrees with final move for {fragment_id}")
        if not _same_id(fragment.get("feedback_cluster_id"), final_destination):
            errors.append(f"fragment.feedback_cluster_id disagrees with final move for {fragment_id}")

    return sorted(set(errors)), {
        "scope": CHECK6_SCOPE,
        "eligible_fragments": len(eligible_ids),
        "moved_fragments": len(moved_fragment_ids),
    }


def _validate_endpoint(uri: str, db_name: str, mode: str) -> None:
    parsed = parse_uri(uri)
    nodes = parsed.get("nodelist") or []
    if len(nodes) != 1:
        raise ValueError("Exactly one MongoDB node is allowed.")
    host, port = nodes[0]
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Only a loopback MongoDB host is allowed.")
    expected = (27018, "nie_pilot") if mode == "pilot" else (27017, "nie")
    if (port, db_name) != expected:
        raise ValueError(
            f"Fail-closed endpoint mismatch: mode={mode} requires port/db={expected[0]}/{expected[1]}."
        )


def _document_set(mode: str, participant: str) -> tuple[ApprovedDocument, ...]:
    source_participant = "P2" if mode == "pilot" else participant
    docs = tuple(doc for doc in APPROVED if doc.participant == source_participant)
    if len(docs) != 3:
        raise ValueError("The approved assignment must contain exactly three documents.")
    return docs


def verify_document(db: Any, participant: str, doc: ApprovedDocument, assigned_doc_ids: set[str]) -> dict[str, Any]:
    doc_oid = ObjectId(doc.doc_id)
    run_oid = ObjectId(doc.run_id)
    document = db["documents"].find_one({"_id": doc_oid}, {"name": 1})
    run = db["pipelineRuns"].find_one({"_id": run_oid})
    fragments = list(db["fragments"].find(
        {"docid": doc_oid},
        {"cluster_id": 1, "feedback_cluster_id": 1},
    ))
    clusters = list(db["clusters"].find(
        {"survey_doc_id": doc_oid},
        {"fragment_ids": 1},
    ))
    events = list(db["clusterFeedback"].find(
        {"doc_id": doc_oid, "participant_id": participant},
        {
            "fragment_id": 1,
            "doc_id": 1,
            "participant_id": 1,
            "action": 1,
            "from_cluster_id": 1,
            "to_cluster_id": 1,
            "timestamp": 1,
        },
    ))

    fragment_by_id = {str(item["_id"]): item for item in fragments}
    cluster_by_id = {str(item["_id"]): item for item in clusters}
    eligible_ids = {
        fragment_id
        for fragment_id, item in fragment_by_id.items()
        if item.get("cluster_id") is not None
    }

    # Check 1: exact approved document and generation run.
    errors1: list[str] = []
    if not document:
        errors1.append("approved document is absent")
    elif document.get("name") != doc.name:
        errors1.append("document name mismatch")
    if not run:
        errors1.append("approved pipeline run is absent")
    else:
        expected_run = {
            "doc_id": doc_oid,
            "pipeline": "llm_semantic",
            "llm_backend": doc.backend,
            "model_name": doc.model,
            "batch_label": doc.batch,
            "status": "completed",
            "strict_mode": True,
            "code_version": G2,
        }
        for key, expected in expected_run.items():
            actual = run.get(key)
            if key == "doc_id":
                matches = _same_id(actual, expected)
            else:
                matches = actual == expected
            if not matches:
                errors1.append(f"pipelineRuns.{key} mismatch")
        if run.get("finished_at") is None:
            errors1.append("pipelineRuns.finished_at is absent")
        if any(str(key).startswith("failure_") for key in run):
            errors1.append("pipelineRuns contains failure_* field")
        params = run.get("params") or {}
        for key, expected in _expected_params(doc).items():
            if params.get(key) != expected:
                errors1.append(f"pipelineRuns.params.{key} mismatch")
    check1 = _finding(1, "whitelist_run_identity", errors1, details={
        "document_present": bool(document),
        "run_present": bool(run),
        "approved_run_id": doc.run_id,
    })

    # Check 2: participant and eligible scope.
    errors2: list[str] = []
    participant_events_all_docs = list(db["clusterFeedback"].find(
        {"participant_id": participant}, {"doc_id": 1}
    ))
    out_of_assignment = sorted({
        str(event.get("doc_id"))
        for event in participant_events_all_docs
        if str(event.get("doc_id")) not in assigned_doc_ids
    })
    if out_of_assignment:
        errors2.append("participant has feedback outside the assigned three documents")
    for event in events:
        fragment_id = str(event.get("fragment_id"))
        if event.get("participant_id") != participant:
            errors2.append("feedback participant mismatch")
        if not _same_id(event.get("doc_id"), doc_oid):
            errors2.append("feedback document mismatch")
        if fragment_id not in eligible_ids:
            errors2.append(f"feedback references non-eligible fragment {fragment_id}")
    if len(eligible_ids) != doc.eligible:
        errors2.append(
            f"eligible count mismatch: expected {doc.eligible}, observed {len(eligible_ids)}"
        )
    check2 = _finding(2, "participant_eligible_scope", sorted(set(errors2)), details={
        "eligible": len(eligible_ids),
        "feedback_events": len(events),
        "out_of_assignment_doc_ids": out_of_assignment,
    })

    # Check 3: action and reference integrity.
    errors3: list[str] = []
    valid_events: list[dict[str, Any]] = []
    for event in events:
        action = event.get("action")
        fragment_id = str(event.get("fragment_id"))
        from_id = str(event.get("from_cluster_id")) if event.get("from_cluster_id") else None
        to_id = str(event.get("to_cluster_id")) if event.get("to_cluster_id") else None
        event_valid = True
        if action not in {"confirm", "move"}:
            errors3.append(f"unsupported action on feedback {event['_id']}")
            event_valid = False
        if fragment_id not in fragment_by_id:
            errors3.append(f"fragment reference missing on feedback {event['_id']}")
            event_valid = False
        if from_id not in cluster_by_id:
            errors3.append(f"from-cluster reference missing/wrong-document on feedback {event['_id']}")
            event_valid = False
        if action == "confirm" and to_id is not None:
            errors3.append(f"confirm unexpectedly has to_cluster_id on feedback {event['_id']}")
            event_valid = False
        if action == "move":
            if to_id not in cluster_by_id:
                errors3.append(f"to-cluster reference missing/wrong-document on feedback {event['_id']}")
                event_valid = False
            if from_id == to_id:
                errors3.append(f"move source equals destination on feedback {event['_id']}")
                event_valid = False
        if event.get("timestamp") is None:
            errors3.append(f"timestamp absent on feedback {event['_id']}")
            event_valid = False
        if event_valid:
            valid_events.append(event)
    check3 = _finding(3, "action_reference_integrity", sorted(set(errors3)), details={
        "valid_events": len(valid_events),
        "total_events": len(events),
    })

    # Check 4: latest-state partition.
    errors4: list[str] = []
    latest: dict[str, dict[str, Any]] = {}
    ordered_desc = sorted(
        valid_events,
        key=lambda event: (event.get("timestamp"), event.get("_id")),
        reverse=True,
    )
    for event in ordered_desc:
        latest.setdefault(str(event["fragment_id"]), event)
    confirm_count = sum(1 for event in latest.values() if event.get("action") == "confirm")
    move_count = sum(1 for event in latest.values() if event.get("action") == "move")
    no_record_count = len(eligible_ids) - len(latest)
    if no_record_count < 0:
        errors4.append("latest-state fragments exceed eligible set")
    if confirm_count + move_count + no_record_count != len(eligible_ids):
        errors4.append("latest-state partition does not close")
    if len(valid_events) < len(latest):
        errors4.append("event count is below distinct reviewed fragments")
    if any(fragment_id not in eligible_ids for fragment_id in latest):
        errors4.append("latest-state partition includes non-eligible fragment")
    check4 = _finding(4, "latest_state_partition", errors4, details={
        "confirm": confirm_count,
        "move": move_count,
        "no_recorded_decision": no_record_count,
        "eligible": len(eligible_ids),
        "raw_valid_events": len(valid_events),
        "distinct_reviewed_fragments": len(latest),
    })

    # Check 5: move-chain continuity, move-only scope.
    move_events = [event for event in valid_events if event.get("action") == "move"]
    errors5: list[str] = []
    moved_fragment_ids = sorted({str(event["fragment_id"]) for event in move_events})
    for fragment_id in moved_fragment_ids:
        chain = sorted(
            (event for event in move_events if str(event["fragment_id"]) == fragment_id),
            key=lambda event: (event.get("timestamp"), event.get("_id")),
        )
        if not chain[0].get("from_cluster_id"):
            errors5.append(f"first move lacks from_cluster_id for fragment {fragment_id}")
        for previous, current in zip(chain, chain[1:]):
            if not _same_id(previous.get("to_cluster_id"), current.get("from_cluster_id")):
                errors5.append(f"move chain discontinuity for fragment {fragment_id}")
    check5 = _finding(
        5,
        "move_chain_continuity",
        sorted(set(errors5)),
        applicable=bool(move_events),
        details={"moved_fragments": len(moved_fragment_ids), "move_events": len(move_events)},
    )

    # Check 6: post-move fields plus all-eligible membership projection.
    errors6, check6_details = evaluate_post_move_projection(
        fragment_by_id,
        cluster_by_id,
        eligible_ids,
        move_events,
    )
    check6 = _finding(
        6,
        "post_move_projection",
        errors6,
        details=check6_details,
    )

    return {
        "participant": participant,
        "document": doc.name,
        "doc_id": doc.doc_id,
        "run_id": doc.run_id,
        "checks": [check1, check2, check3, check4, check5, check6],
    }


def _git_metadata(repo_root: Path) -> tuple[str | None, bool | None]:
    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        return head, not bool(dirty)
    except Exception:
        return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pilot", "formal"), required=True)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--participant", required=True)
    browser_group = parser.add_mutually_exclusive_group(required=True)
    browser_group.add_argument("--browser-errors-file")
    browser_group.add_argument("--browser-errors-json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    participant = args.participant.strip().upper()
    if args.mode == "pilot" and participant != "PILOT":
        raise SystemExit("Pilot mode accepts participant=PILOT only.")
    if args.mode == "formal" and participant not in {"P1", "P2", "P3"}:
        raise SystemExit("Formal mode accepts P1/P2/P3 only.")
    _validate_endpoint(args.mongo_uri, args.db_name, args.mode)

    if args.browser_errors_file:
        browser_source = str(Path(args.browser_errors_file).resolve())
        raw_browser_errors = Path(args.browser_errors_file).read_text(encoding="utf-8")
    else:
        browser_source = "inline JSON supplied at invocation"
        raw_browser_errors = args.browser_errors_json
    browser_errors = parse_browser_errors(raw_browser_errors)

    approved_docs = _document_set(args.mode, participant)
    assigned_doc_ids = {doc.doc_id for doc in approved_docs}
    n_integrity = count_integrity_errors(browser_errors, participant, assigned_doc_ids)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    head, clean = _git_metadata(repo_root)
    client = MongoClient(
        args.mongo_uri,
        appname="formal-session-integrity-readonly",
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
        db = client[args.db_name]
        required_collections = {"documents", "fragments", "clusters", "clusterFeedback", "pipelineRuns"}
        missing = sorted(required_collections - set(db.list_collection_names()))
        if missing:
            raise RuntimeError(f"Required collections missing: {missing}")
        results = [
            verify_document(db, participant, document, assigned_doc_ids)
            for document in approved_docs
        ]
    finally:
        client.close()

    statuses = [check["status"] for result in results for check in result["checks"]]
    overall = "PASS" if "FAIL" not in statuses else "FAIL"
    output = {
        "schema": INTEGRITY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "database": args.db_name,
        "participant": participant,
        "endpoint": "127.0.0.1:27018" if args.mode == "pilot" else "127.0.0.1:27017",
        "read_only_design": True,
        "check6_scope": CHECK6_SCOPE,
        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "repository_head": head,
        "repository_worktree_clean": clean,
        "browser_error_source": browser_source,
        "integrity_N": n_integrity,
        "documents": results,
        "overall_status": overall,
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "overall_status": overall,
        "integrity_N": n_integrity,
        "output": str(output_path),
        "script_sha256": output["script_sha256"],
        "documents": [
            {
                "document": item["document"],
                "checks": {check["check"]: check["status"] for check in item["checks"]},
            }
            for item in results
        ],
    }, ensure_ascii=False))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

