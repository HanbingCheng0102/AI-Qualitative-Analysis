# Formal session integrity v3: exact P1 development-event exclusion

Date: 2026-08-03  
Status: PASS before the first formal participant session

## Discovery

The P1 pre-session read-only gate confirmed zero `P1` feedback on all three
approved P1 documents and zero `DEMO_P1` feedback on the dedicated demo. It also
found three older feedback events using `participant_id=P1` on development
document `manual_test_1 / 6a5616310536f5c49a509277`:

| feedback ID | action | timestamp (UTC) |
| --- | --- | --- |
| `6a57a40ef8d6639908e72349` | move | `2026-07-15T15:15:26.447Z` |
| `6a57a80726831fb4dded3f12` | confirm | `2026-07-15T15:32:23.594Z` |
| `6a57a82e26831fb4dded3f13` | move | `2026-07-15T15:33:02.497Z` |

These records pre-date the formal documents and first formal session. They are
development history, not participant-session data. The v2 checker would still
have treated them as out-of-assignment P1 feedback and made Check 2 fail even
where the formal session itself was correctly isolated.

## Approved resolution

The records remain unchanged in MongoDB. v3 introduces
`pre_session_development_feedback_v1`, an event-level allowlist that locks each
entry by feedback ID, document ID, action and millisecond UTC timestamp.

- Only the three complete fingerprints above are excluded from Check 2.
- A new event on the same `manual_test_1` document is not excluded and fails.
- A missing registered event fails, detecting deletion or history rewriting.
- A changed doc, action or timestamp fails as a fingerprint mismatch.
- Formal participant events on assigned whitelist documents remain in scope.
- No document-wide or participant-wide exemption exists.

This amendment changes only the versioned read-only integrity tool and protocol
documentation. It does not change the participant-facing endpoint
`0e37f187d95db5f10cb6892cc2a97b543a5bd4eb`, database write behaviour, the nine
formal documents, participant instructions, metrics or G2 instrument.

Tool commit:
`5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e`  
Schema: `formal_session_integrity_v3`  
Exclusion version: `pre_session_development_feedback_v1`  
Script SHA-256:
`E33B1523D6BB778AE95E8C5C45212FC410C61C892063AD1CFFB0ED4179B9C052`  
Test-file SHA-256:
`E7425DD477D59638A72553656C19F1CF80EBC7F689DD0686624C104AECD19CFF`

## Automated gates

- Integrity-tool tests: 16/16 PASS. The new tests cover exact exclusion,
  missing registered history, fingerprint mismatch and a fourth event on the
  same development document.
- AI-service tests: 83 PASS; three live probes skipped by design.
- Independent G2 prompt-hash test: PASS.
- Diff from the participant-facing endpoint outside `docs/`: empty.

## Isolated `nie_pilot` gates

Both runs restored the sealed post-PILOT dump into new external dbpaths; neither
used or modified formal `nie`.

Attempt 1:
`D:\6003\pilot_isolation\20260803_integrity_v3_gate`  
Logical checks: PASS; repository cleanliness: rejected because a newly generated
untracked `P1_field_record.docx` existed during invocation. The result was
retained and not overwritten. Result SHA-256:
`29C8A2E4AE5041CF8780FFD4D2376FF3A1D32C6A00F5ADC9EBA34554853B6EE8`.

The untracked field record was preserved outside the repository. Attempt 2 used
a new run root and a clean worktree:

`D:\6003\pilot_isolation\20260803_integrity_v3_gate_attempt2`

Attempt 2 reported overall PASS, `N=0`, Check 6 PASS on all three P2 rehearsal
documents, and the expected no-move Check-5 `NA` on task1. It recorded HEAD
`5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e` and
`repository_worktree_clean=true`.

Attempt-2 result SHA-256:
`35B3D37DD4F553AC6C17B6267C5B2888C5866E24043F0800446DF25D2824A971`  
Attempt-2 MongoDB log SHA-256:
`BA976BC26A3C496021D58FCE2082BEF023190C5FACDA48BDD984597A7731D03A`

## Formal P1 read-only preflight

The v3 tool was then run against `127.0.0.1:27017/nie` with participant P1,
before any participant-facing service was started. The run was read-only and
used literal browser-error input `null` only as a pre-session gate, not as a
substitute for the required post-session raw browser log.

All six applicable checks passed on each approved P1 document. All three
documents had zero P1 feedback; Check 5 was the expected `NA`, and all-eligible
Check 6 passed. Check 2 reported exactly the three registered feedback IDs and
an empty `out_of_assignment_doc_ids` list for each document. Overall status was
PASS and `N=0`.

Evidence:
`D:\6003\formal_session_preflight\20260803_P1_integrity_v3\P1_pre_session_integrity_v3.json`  
Evidence SHA-256:
`FFF6C8BA6DFE413A1B292CCD0EB2CEFCC52626C28F106829DE82A4CB3E91E44B`  
MongoDB log SHA-256:
`1E52764DB7FDD98E5E1DCA73FEF9EA687979B6A71177D096DFF86D075E99E944`

Formal MongoDB shut down cleanly after the read-only gate. Ports 27017, 27018
and 11434 had no listeners afterward. No React, API, AI or participant action
was started during this amendment.
