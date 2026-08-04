#!/usr/bin/env python3
"""Read-only consolidation of the three completed formal sessions.

The tool re-runs the frozen v3 document checks against an isolated
``nie_analysis`` restore, compares them with the three post-session integrity
records, and emits aggregate counts only.  It never projects fragment text,
HTML, embeddings, row data, research questions, notes, or participant speech.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from bson import ObjectId
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

from formal_session_integrity import (
    APPROVED,
    CHECK6_SCOPE,
    HISTORICAL_FEEDBACK_EXCLUSION_VERSION,
    INTEGRITY_SCHEMA_VERSION,
    ApprovedDocument,
    _document_set,
    _git_metadata,
    verify_document,
)


ANALYSIS_SCHEMA_VERSION = "formal_session_analysis_v1"
ANALYSIS_DATABASE = "nie_analysis"
ANALYSIS_HOST = "127.0.0.1"
ANALYSIS_PORT = 27019
INTEGRITY_TOOL_HEAD = "5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e"
PARTICIPANTS = ("P1", "P2", "P3")
LATEST_ACTION_RULE = "timestamp_desc_then_id_desc"
NO_DECISION_SEMANTICS = "reject-or-unreviewed; no automatic interpretation"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_analysis_endpoint(uri: str, db_name: str) -> None:
    if db_name != ANALYSIS_DATABASE:
        raise ValueError(f"Analysis database must be {ANALYSIS_DATABASE}.")
    parsed = parse_uri(uri)
    if parsed.get("username") is not None or parsed.get("password") is not None:
        raise ValueError("Analysis URI must not contain credentials.")
    nodes = parsed.get("nodelist") or []
    if len(nodes) != 1:
        raise ValueError("Analysis URI must identify exactly one MongoDB node.")
    host, port = nodes[0]
    if str(host).lower() != ANALYSIS_HOST or int(port) != ANALYSIS_PORT:
        raise ValueError(
            f"Analysis endpoint must be {ANALYSIS_HOST}:{ANALYSIS_PORT}."
        )


def _parse_integrity_arguments(values: Iterable[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("Integrity result must use PARTICIPANT=PATH.")
        participant, raw_path = value.split("=", 1)
        participant = participant.strip().upper()
        if participant not in PARTICIPANTS:
            raise ValueError(f"Unsupported integrity participant: {participant}")
        if participant in parsed:
            raise ValueError(f"Duplicate integrity result for {participant}.")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Integrity result is absent: {path}")
        parsed[participant] = path
    if set(parsed) != set(PARTICIPANTS):
        raise ValueError("Exactly one integrity result is required for P1, P2 and P3.")
    return parsed


def _load_integrity_result(path: Path, participant: str) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    expected_docs = _document_set("formal", participant)
    if result.get("schema") != INTEGRITY_SCHEMA_VERSION:
        raise ValueError(f"{participant} integrity schema mismatch.")
    if result.get("mode") != "formal" or result.get("participant") != participant:
        raise ValueError(f"{participant} integrity identity mismatch.")
    if result.get("database") != "nie" or result.get("endpoint") != "127.0.0.1:27017":
        raise ValueError(f"{participant} integrity source was not formal nie.")
    if result.get("overall_status") != "PASS":
        raise ValueError(f"{participant} integrity result is not PASS.")
    if result.get("repository_head") != INTEGRITY_TOOL_HEAD:
        raise ValueError(f"{participant} integrity tool head mismatch.")
    if result.get("repository_worktree_clean") is not True:
        raise ValueError(f"{participant} integrity worktree was not clean.")
    if result.get("check6_scope") != CHECK6_SCOPE:
        raise ValueError(f"{participant} Check 6 scope mismatch.")
    if (
        result.get("historical_feedback_exclusion_version")
        != HISTORICAL_FEEDBACK_EXCLUSION_VERSION
    ):
        raise ValueError(f"{participant} historical exclusion version mismatch.")
    integrity_n = result.get("integrity_N")
    if not isinstance(integrity_n, int) or integrity_n < 0:
        raise ValueError(f"{participant} integrity_N is invalid.")
    documents = result.get("documents")
    if not isinstance(documents, list) or len(documents) != 3:
        raise ValueError(f"{participant} must have exactly three integrity documents.")
    actual_identity = [(item.get("doc_id"), item.get("run_id")) for item in documents]
    expected_identity = [(doc.doc_id, doc.run_id) for doc in expected_docs]
    if actual_identity != expected_identity:
        raise ValueError(f"{participant} integrity document matrix mismatch.")
    return result


def _check_by_number(result: dict[str, Any], number: int) -> dict[str, Any]:
    matches = [item for item in result.get("checks", []) if item.get("check") == number]
    if len(matches) != 1:
        raise ValueError(f"Expected one Check {number} result.")
    return matches[0]


def _latest_details(result: dict[str, Any]) -> dict[str, int]:
    check = _check_by_number(result, 4)
    if check.get("status") != "PASS":
        raise ValueError("Latest-state Check 4 is not PASS.")
    details = check.get("details") or {}
    required = (
        "confirm",
        "move",
        "no_recorded_decision",
        "eligible",
        "raw_valid_events",
        "distinct_reviewed_fragments",
    )
    values: dict[str, int] = {}
    for key in required:
        value = details.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"Check 4 detail {key} is invalid.")
        values[key] = value
    if values["confirm"] + values["move"] + values["no_recorded_decision"] != values["eligible"]:
        raise ValueError("Latest-state partition does not close.")
    if values["confirm"] + values["move"] != values["distinct_reviewed_fragments"]:
        raise ValueError("Reviewed-fragment count does not match final actions.")
    if values["raw_valid_events"] < values["distinct_reviewed_fragments"]:
        raise ValueError("Raw valid events are below distinct reviewed fragments.")
    return values


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator <= 0:
        raise ValueError("Rate denominator must be positive.")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "proportion": round(numerator / denominator, 6),
        "percent": round(100 * numerator / denominator, 2),
    }


def _document_row(
    db: Any,
    doc: ApprovedDocument,
    recomputed: dict[str, Any],
    integrity_n: int,
) -> dict[str, Any]:
    details = _latest_details(recomputed)
    if details["eligible"] != doc.eligible:
        raise ValueError(f"Eligible denominator mismatch for {doc.name}.")
    statuses = {item["check"]: item["status"] for item in recomputed["checks"]}
    if any(statuses.get(number) not in ({"PASS", "NA"} if number == 5 else {"PASS"}) for number in range(1, 7)):
        raise ValueError(f"Six-check status is not analyzable for {doc.name}.")
    cluster_count = db["clusters"].count_documents({"survey_doc_id": ObjectId(doc.doc_id)})
    if cluster_count <= 0:
        raise ValueError(f"No clusters found for {doc.name}.")
    return {
        "participant": doc.participant,
        "document": doc.name,
        "doc_id": doc.doc_id,
        "run_id": doc.run_id,
        "batch": doc.batch,
        "backend": doc.backend,
        "model": doc.model,
        "cluster_count": cluster_count,
        "single_cluster": cluster_count == 1,
        "eligible": details["eligible"],
        "raw_valid_events": details["raw_valid_events"],
        "distinct_reviewed_fragments": details["distinct_reviewed_fragments"],
        "final_confirm": details["confirm"],
        "final_move": details["move"],
        "no_recorded_decision": details["no_recorded_decision"],
        "confirm_coverage_lower_bound": _ratio(details["confirm"], details["eligible"]),
        "explicit_correction_rate": _ratio(details["move"], details["eligible"]),
        "no_recorded_decision_rate": _ratio(details["no_recorded_decision"], details["eligible"]),
        "participant_integrity_N": integrity_n,
        "check5_status": statuses[5],
        "check6_status": statuses[6],
    }


def _aggregate(rows: Iterable[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key])].append(row)
    output = []
    for name in sorted(grouped):
        items = grouped[name]
        eligible = sum(item["eligible"] for item in items)
        confirm = sum(item["final_confirm"] for item in items)
        move = sum(item["final_move"] for item in items)
        no_record = sum(item["no_recorded_decision"] for item in items)
        if confirm + move + no_record != eligible:
            raise ValueError(f"Aggregate partition does not close for {name}.")
        output.append({
            group_key: name,
            "documents": len(items),
            "eligible": eligible,
            "final_confirm": confirm,
            "final_move": move,
            "no_recorded_decision": no_record,
            "confirm_coverage_lower_bound": _ratio(confirm, eligible),
            "explicit_correction_rate": _ratio(move, eligible),
            "no_recorded_decision_rate": _ratio(no_record, eligible),
            "descriptive_only": True,
        })
    return output


def _outside_repo_output(path: str, repo_root: Path) -> Path:
    output = Path(path).expanduser().resolve()
    try:
        output.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("Participant-action analysis output must remain outside Git.")
    if output.exists():
        raise ValueError(f"Refusing to overwrite existing output: {output}")
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "participant",
        "document",
        "doc_id",
        "run_id",
        "batch",
        "backend",
        "model",
        "cluster_count",
        "single_cluster",
        "eligible",
        "raw_valid_events",
        "distinct_reviewed_fragments",
        "final_confirm",
        "final_move",
        "no_recorded_decision",
        "confirm_coverage_lower_bound_percent",
        "explicit_correction_rate_percent",
        "no_recorded_decision_rate_percent",
        "participant_integrity_N",
        "check5_status",
        "check6_status",
    )
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fields}
            flat["confirm_coverage_lower_bound_percent"] = row["confirm_coverage_lower_bound"]["percent"]
            flat["explicit_correction_rate_percent"] = row["explicit_correction_rate"]["percent"]
            flat["no_recorded_decision_rate_percent"] = row["no_recorded_decision_rate"]["percent"]
            writer.writerow(flat)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--expected-repository-head", required=True)
    parser.add_argument(
        "--integrity-result",
        action="append",
        required=True,
        help="Repeat exactly three times as PARTICIPANT=PATH.",
    )
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    _validate_analysis_endpoint(args.mongo_uri, args.db_name)
    integrity_paths = _parse_integrity_arguments(args.integrity_result)
    integrity = {
        participant: _load_integrity_result(path, participant)
        for participant, path in integrity_paths.items()
    }

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    output_json = _outside_repo_output(args.output_json, repo_root)
    output_csv = _outside_repo_output(args.output_csv, repo_root)
    if output_json == output_csv:
        raise ValueError("JSON and CSV output paths must differ.")

    head, clean = _git_metadata(repo_root)
    if head != args.expected_repository_head:
        raise RuntimeError("Repository HEAD does not match the approved analysis endpoint.")
    if clean is not True:
        raise RuntimeError("Repository worktree must be clean for formal analysis.")

    client = MongoClient(
        args.mongo_uri,
        appname="formal-session-analysis-readonly",
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
        database_names = set(client.list_database_names())
        if ANALYSIS_DATABASE not in database_names or "nie" in database_names:
            raise RuntimeError("Analysis MongoDB namespace isolation failed.")
        db = client[args.db_name]
        required = {"documents", "fragments", "clusters", "clusterFeedback", "pipelineRuns"}
        missing = sorted(required - set(db.list_collection_names()))
        if missing:
            raise RuntimeError(f"Required collections missing: {missing}")

        rows: list[dict[str, Any]] = []
        for participant in PARTICIPANTS:
            docs = _document_set("formal", participant)
            assigned = {doc.doc_id for doc in docs}
            recomputed = [verify_document(db, participant, doc, assigned) for doc in docs]
            stored_documents = integrity[participant]["documents"]
            if _canonical(recomputed) != _canonical(stored_documents):
                raise RuntimeError(
                    f"{participant} live analysis checks differ from the sealed post-session result."
                )
            rows.extend(
                _document_row(
                    db,
                    doc,
                    result,
                    integrity[participant]["integrity_N"],
                )
                for doc, result in zip(docs, recomputed)
            )
    finally:
        client.close()

    if len(rows) != len(APPROVED):
        raise RuntimeError("Formal analysis did not produce exactly nine document rows.")

    output = {
        "schema": ANALYSIS_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": ANALYSIS_DATABASE,
        "endpoint": f"{ANALYSIS_HOST}:{ANALYSIS_PORT}",
        "read_only_design": True,
        "descriptive_only": True,
        "latest_action_rule": LATEST_ACTION_RULE,
        "no_recorded_decision_semantics": NO_DECISION_SEMANTICS,
        "script_sha256": _sha256_file(script_path),
        "repository_head": head,
        "repository_worktree_clean": clean,
        "integrity_inputs": {
            participant: {
                "sha256": _sha256_file(integrity_paths[participant]),
                "integrity_N": integrity[participant]["integrity_N"],
                "overall_status": integrity[participant]["overall_status"],
            }
            for participant in PARTICIPANTS
        },
        "documents": rows,
        "participant_totals": _aggregate(rows, "participant"),
        "model_totals": _aggregate(rows, "model"),
        "interpretation_limits": [
            "confirm/eligible is a coverage lower bound, not a complete acceptance rate",
            "move/eligible is an explicit correction rate",
            "no recorded decision cannot be interpreted as acceptance or rejection",
            "single-cluster documents make move structurally unavailable",
            "all model summaries are descriptive; no inferential test is performed",
        ],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_json.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _write_csv(output_csv, rows)
    except Exception:
        output_json.unlink(missing_ok=True)
        output_csv.unlink(missing_ok=True)
        raise

    print(json.dumps({
        "schema": ANALYSIS_SCHEMA_VERSION,
        "documents": len(rows),
        "participants": len(PARTICIPANTS),
        "integrity_N_total": sum(integrity[item]["integrity_N"] for item in PARTICIPANTS),
        "output_json": str(output_json),
        "output_csv": str(output_csv),
        "script_sha256": output["script_sha256"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
