# Formal session analysis v1

Date: 2026-08-04
Status: implementation prepared; execution evidence pending

## Purpose and boundary

This record freezes the first descriptive analysis tool used after all three
formal sessions and the final database archive. The tool is
`docs/verification_tools/formal_session_analysis.py`; its dedicated synthetic
tests are in `docs/verification_tools/test_formal_session_analysis.py`.

The tool does not run against the formal database. It accepts only
`127.0.0.1:27019/nie_analysis`, a separately restored copy of the sealed final
archive. It rejects ports 27017 and 27018, database names other than
`nie_analysis`, credentials in the MongoDB URI, output paths inside the Git
repository, a dirty worktree, and a repository HEAD different from the
explicitly supplied analysis endpoint.

The analysis is read-only by construction. It uses only MongoDB read methods,
contains no MongoDB insert, update, replace, delete, bulk-write or drop call,
and writes results only to new files outside the repository. The formal UI,
API, AI service and Ollama are not part of this analysis and must remain
stopped. No fragment text, HTML, embeddings, row data, research question,
notes, recording or transcript is selected or emitted.

## Sealed source and isolated restore

The accepted final archive is:

`D:\6003\formal_session_archive\20260804_202648_final_attempt2`

Its independently copied archive is:

`D:\6003\formal_session_archive_backup\20260804_202648_final_attempt2\archive_copy`

The primary and secondary tree manifests both have SHA-256
`22975EF84D3752883603BA40EBBC5A6AC21440D4C233289075677278FF0A1E3C`.
The final source PRE/POST semantic hash is
`B271850091ED5DF9C99B8A39D7D599500B5D58C2D758882F13C378BD5F39C2BB`.

The accepted isolated restore is under:

`D:\6003\formal_analysis\20260804_212639_analysis_restore_attempt2`

It contains `nie_analysis` and no `nie` database. Comparison with the sealed
source passed with normalized semantic hash
`82F52DDADAE3AC54FEFA80DEBC35E5EB52835C5606D0834BB725485638370119`.
Port 27019 was stopped after restore verification and is started only for the
bounded analysis run.

Two failed infrastructure attempts remain preserved and are not represented
as analysis results: archive attempt 1 stopped before a dump because the lock
counter was parsed with the wrong scalar type; analysis-restore attempt 1
stopped before restore because normal `mongorestore` stderr progress was
promoted to a terminating PowerShell error.

## Integrity binding

The analysis consumes exactly one post-session integrity result for each of
P1, P2 and P3. Each input must be `formal_session_integrity_v3`, PASS, tied to
formal `nie` on `127.0.0.1:27017`, produced from integrity-tool endpoint
`5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e` with a clean worktree, and contain
the exact three-document assignment for that participant.

Against `nie_analysis`, the tool reruns all six checks for every approved
document. The canonical recomputed document results must equal the stored
post-session document results exactly. A mismatch stops the run without an
analysis output. Check 5 may be `NA` only where no move exists; Checks 1–4 and
6 must be PASS. `integrity_N` is participant-level context and is labelled
`participant_integrity_N` on document rows; it is not silently treated as a
document-level count.

## Frozen descriptive metrics

For each eligible fragment, the final valid participant action is selected by
descending `(timestamp, _id)`. The three mutually exclusive outcomes are:

- `final_confirm`;
- `final_move`; and
- `no_recorded_decision`.

The partition must close against the eligible-fragment denominator. A
confirm-then-move sequence is therefore finally classified as move while the
underlying event history remains preserved. The outputs also contain raw valid
event count, distinct reviewed-fragment count, current cluster count and a
single-cluster flag.

The only reported ratios are:

- `final_confirm / eligible`, labelled a confirmation-coverage lower bound;
- `final_move / eligible`, labelled an explicit-correction rate; and
- `no_recorded_decision / eligible`.

`no_recorded_decision` is not automatically interpreted as acceptance or
rejection. In particular, a participant may have rejected the current cluster
without finding a suitable existing destination. In a single-cluster
document, move is structurally unavailable. Participant and model totals are
descriptive only; no inferential test is performed and no causal or quality
claim follows from a difference in these totals.

## Evidence separation

Participant-action counts and ratios are sensitive research outputs. The JSON
and CSV produced by the formal run remain outside Git and are not copied into
this verification record. A later docs-only audit record may contain only the
analysis endpoint commit, PASS/FAIL status, external evidence paths and file
hashes. It must not contain participant-level or model-level metric values.

The qualitative observation workflow is separate. Audio, transcripts and
researcher locator notes are not inputs to this tool and are not joined to the
quantitative output.

## Pre-execution gates

Before the one accepted execution:

1. dedicated synthetic tests must pass;
2. the full verification-tool test set must pass;
3. the AI-service test suite and G2 prompt-freeze test must pass;
4. the implementation and this record must be committed and pushed;
5. the restored database must again match the accepted normalized semantic
   hash before analysis;
6. ports 27017 and 11434 must have no listener; and
7. the run must use the exact committed analysis HEAD with a clean worktree.

If any gate fails, the run stops and the failed attempt is preserved. Outputs
are never overwritten or selected according to their values.
