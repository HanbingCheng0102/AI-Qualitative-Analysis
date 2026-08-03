# Formal session integrity v2: all-eligible Check 6

Date: 2026-08-03  
Status: PASS before the first formal participant session

## Purpose and boundary

The pre-registered decision was to expand Check 6 from its historical
move-only scope to every eligible fragment before the first formal session.
This change closes a baseline-verification gap: a document with no move events
must still prove that each eligible fragment appears in exactly one current
cluster and that this membership agrees with `fragment.cluster_id`.

This is a versioned, read-only integrity-analysis amendment. It does not change:

- the participant-facing session endpoint
  `0e37f187d95db5f10cb6892cc2a97b543a5bd4eb`;
- the G2 generation instrument, prompt, schema or frozen parameters;
- React, API or AI-service behaviour;
- MongoDB write behaviour, the nine formal documents or their whitelist; or
- the pre-registered participant order, 45-minute stopping rule or metrics.

The historical v1 gate remains recorded unchanged in
`docs/verification_records/formal_session_integrity_pilot_gate.md`. Its
no-move Check-6 `NA` result was valid for the then-frozen move-only scope; it is
not represented as an all-eligible test.

## Implemented semantics

- Check 5, `move_chain_continuity`, remains move-only. It returns `NA` where a
  participant-document contains no valid move.
- Check 6, `post_move_projection`, now has `scope=all_eligible` and always
  returns PASS or FAIL.
- For every eligible fragment, Check 6 requires exactly one current cluster
  membership and equality between that membership and
  `fragment.cluster_id`.
- For moved fragments, the existing second layer remains: current
  `fragment.cluster_id`, `feedback_cluster_id` and the final move
  `to_cluster_id` must agree.
- Check 6 tests current graph-projection consistency. It does not score cluster
  quality and does not redefine the current projection as an immutable copy of
  the initial AI assignment.

Implementation commit:
`f34856a072d6761b44decdfd77963cf3fcee550b`  
Implementation script SHA-256:
`3F3C9DDB46D47B35577A4F9F0ACA3D1044943F0260EFAAA3EDB863590F9F4111`  
Unit-test file SHA-256:
`812C7FB2BB6289B8C0B5CA4881E648175A5BB910ACAF5B775EC67D8425652186`

## Automated gates

The dedicated integrity-tool suite passed 12/12 tests. Its v2 cases cover:

- no-move documents still receiving an all-eligible Check 6;
- missing current membership;
- duplicate current membership;
- membership disagreement with `fragment.cluster_id`; and
- preservation of the moved-fragment final-destination and
  `feedback_cluster_id` assertions.

The AI-service suite passed 83 tests; three live provider probes were skipped by
design. The independent G2 prompt-freeze test passed. The diff from the formal
session endpoint outside `docs/` was empty.

## Isolated live gate

The accepted run restored the sealed post-PILOT dump
`D:\6003\pilot_isolation\20260726_225547\pilot_post` into a new external
database path:

`D:\6003\pilot_isolation\20260803_integrity_v2_gate\pilot_dbpath`

The temporary server was bound to `127.0.0.1:27018`; the checker connected only
to `nie_pilot` with participant `PILOT`. The formal database on port 27017,
React, API, AI service and Ollama were not started for the accepted run. The
restore reported 1,628 documents restored and zero failures. The checker
reported:

| Document | Eligible | Moved | Check 5 | Check 6 | Check-6 scope |
| --- | ---: | ---: | --- | --- | --- |
| `P2_task1_batchB` | 16 | 0 | NA | PASS | `all_eligible` |
| `P2_task2_batchC` | 20 | 1 | PASS | PASS | `all_eligible` |
| `P2_task3_batchA` | 16 | 2 | PASS | PASS | `all_eligible` |

Overall status was PASS and browser integrity `N=0`. The output recorded
repository HEAD `f34856a072d6761b44decdfd77963cf3fcee550b` and a clean worktree.

Evidence output:
`D:\6003\pilot_isolation\20260803_integrity_v2_gate\ledger\pilot_six_checks_v2.json`  
Evidence SHA-256:
`C72134FA53458106BFD317CF86027B8EE240F247660158EA98AD775DC3E201D8`  
MongoDB log SHA-256:
`299B7664ACC1C0D6E80D4546F6E0AA8BDFBC26EA39E8A4DB9222FD4B6740D9EB`

The temporary mongod shut down cleanly with exit code 0. Post-run listeners on
27017, 27018 and 11434 were all absent.

## Fail-closed attempt ledger

Two preflight attempts stopped before creating the run directory, restoring a
database or invoking the checker because an automatically restarted Ollama
process was listening on port 11434. The blocking process was identified as
Ollama server PID 7256, launched by Ollama desktop-app PID 16664. Only those two
identified PIDs were stopped. Ports 27017, 27018 and 11434 were then rechecked as
clear before the accepted run. These were environment-gate failures with zero
database side effects, not Check-6 results.

## Interpretation

The live gate establishes that the expanded implementation executes against
all eligible fragments, including the no-move document, and that the preserved
PILOT projection passes the new scope. It does not establish the quality of any
model clustering or predict the outcome of future formal-session integrity
checks.
