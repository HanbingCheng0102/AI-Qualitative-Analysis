# Formal-session six-check PILOT gate

## Scope and provenance

- Gate date: `2026-08-01` (Europe/London), before the first formal participant
  session.
- Frozen participant-facing session code endpoint:
  `ddb5355972ca63df44edad184b11e30f420e4c62` (unchanged).
- Protocol/tool commit tested:
  `8ea23cce2d40936423a775fcba425b923bed9799`.
- Database endpoint: `127.0.0.1:27018/nie_pilot` only.
- Participant scope: `PILOT`; the approved P2 rehearsal document triplet.
- Formal `127.0.0.1:27017/nie` was not started or queried.
- React, API, AI service and Ollama were not started for the database check.
- Tool design is read-only with respect to MongoDB. It selects only IDs,
  timestamps, action/reference fields and counts; it does not select or emit
  fragment text, HTML, embeddings, row data, research questions or credentials.

The PILOT ledger records
`browser_feedback_provenance_errors=null` and error count zero at lines 92–93.
That preserved value was supplied as literal JSON `null`; the gate therefore
computed integrity `N=0`. This confirms the script's result for the preserved
PILOT value but does not create an independent second copy of the original
browser localStorage object.

## Attempt ledger

The first environment-gate attempt stopped before creating a run directory or
starting MongoDB because post-reboot Ollama was listening on 11434 (server PID
15240; app PID 15108). Both exact Ollama processes were identified and stopped;
the gate was then repeated. This was an environment-gate failure, not a
consistency-check or database failure.

On the accepted attempt:

- pre-run listeners on 27017, 27018 and 11434: none;
- PILOT mongod PID: `12536`, bound only to `127.0.0.1:27018`;
- repository worktree at invocation: clean;
- all queries completed before shutdown;
- post-run listeners on 27017, 27018 and 11434: none (only transient 27018
  `TIME_WAIT` connections remained).

The accepted wrapper initially stopped the exact mongod PID forcibly, so its
first log lacked a normal shutdown tail. This did not affect the already-written
check output or the sealed post-PILOT dump, but it could have left the working
PILOT dbpath non-clean. The same dbpath was therefore recovery-started as PID
`1920` and closed with MongoDB admin shutdown. The recovery log records a
successful WiredTiger shutdown checkpoint, removal of the fs lock,
`mongod shutdown complete`, and server exit code 0. `mongosh` returned exit 1
only because the expected server shutdown closed its connection
(`MongoNetworkError: read ECONNRESET`).

## Hashes and retained evidence

- Script SHA-256:
  `D31B83C7830540176F8F233D2E4842C840C800941E55301397FCB9D848A65648`
- Result SHA-256:
  `80A460EDAD44E7335707206C965A2E8FA2522862EE4657885648342CBE676DAB`
- Result:
  `D:\6003\pilot_isolation\20260801_formal_integrity_gate\pilot_six_checks.json`
- Accepted-start log:
  `D:\6003\pilot_isolation\20260801_formal_integrity_gate\mongod.log`
- Recovery/clean-shutdown log:
  `D:\6003\pilot_isolation\20260801_formal_integrity_gate\mongod_recovery_clean_shutdown.log`
- Original PILOT ledger:
  `D:\6003\pilot_isolation\20260726_225547\ledger\pilot_session_ledger.txt`

## Six-check result

| Document | Check 1 | Check 2 | Check 3 | Check 4 | Check 5 | Check 6 |
| --- | --- | --- | --- | --- | --- | --- |
| `P2_task1_batchB` | PASS | PASS | PASS | PASS | NA | NA |
| `P2_task2_batchC` | PASS | PASS | PASS | PASS | PASS | PASS |
| `P2_task3_batchA` | PASS | PASS | PASS | PASS | PASS | PASS |

Checks 5/6 are correctly `NA` for `P2_task1_batchB` because that document had
no PILOT move event. They were not relabelled PASS and were not applied to
confirm-only or unreviewed fragments. The two documents containing move events
passed both move-only checks.

The Check-4 final-state counts reproduce the prior dry run:

| Document | Final confirm | Final move | No recorded decision | Eligible | Raw valid events | Distinct reviewed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `P2_task1_batchB` | 7 | 0 | 9 | 16 | 7 | 7 |
| `P2_task2_batchC` | 12 | 1 | 7 | 20 | 13 | 13 |
| `P2_task3_batchA` | 8 | 2 | 6 | 16 | 16 | 10 |

Overall result: `PASS`; integrity `N=0`. `final` denotes the adjudicated latest
state per fragment, not raw event totals. Confirm→move ends as final move while
both events remain preserved.

