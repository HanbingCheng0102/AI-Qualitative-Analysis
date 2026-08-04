# Formal session analysis v1 audit

Date: 2026-08-04
Status: PASS

## Frozen endpoint

The operational analysis implementation was committed and pushed before the
accepted run:

`d80da7acf29ddf7254b10991f96c6f1ca569f000`

The branch was `codex/formal-session-analysis-v1`, its divergence from the
same branch on `origin` was `0/0`, and the worktree was clean. The accepted
run explicitly required this exact HEAD. The analysis-tool SHA-256 was
`ED9F64E7766AB0808285E1BDF8D8988013ADA8083F5EFF8FC9A148D4FE94EB18`;
the dedicated test-file SHA-256 was
`3AAA4C65808F714D464509FBE828DF3111366C8D73E728D7812101655CFEE2FA`.

Pre-execution gates passed:

- formal-analysis synthetic tests: 12/12;
- formal-session integrity tests: 16/16;
- AI-service tests: 83 passed, with three live probes skipped by design; and
- the independent G2 prompt-freeze test: PASS.

## Input evidence

The tool consumed the three post-session integrity-v3 outputs at their
external paths. Their SHA-256 values were:

- P1: `3AC15C6EBA07E47404DD26179F6C82FA4DD7FD0FBB7619926C4B00C234B7DD5B`;
- P2: `9D9F50230CB3869AA0CD203C780F804423DF723FDE686A2A965F9E2E0160635D`;
- P3: `657CCF8311CFF547DDFC6DC3F1849772B5CB8BCC89F3CCDB18681D16E71340AA`.

All three inputs passed the frozen identity, matrix, repository-head,
worktree, Check-6-scope and historical-exclusion gates. Against the isolated
restore, all nine recomputed six-check document results were canonically equal
to their sealed post-session counterparts.

## Accepted execution

The accepted run root was:

`D:\6003\formal_analysis\20260804_215952_formal_session_analysis_v1`

Only the previously verified restore at
`127.0.0.1:27019/nie_analysis` was started. PID 20336 belonged to
`D:\mongodb\bin\mongod.exe` and used the accepted restore dbpath. The formal
database on 27017 and Ollama on 11434 were absent throughout. No React, API or
AI service was started.

The analysis executable returned exit code 0. Its stderr was empty. Structural
post-validation passed: the output schema and exact nine-document matrix were
present, every latest-action partition closed against its eligible
denominator, Check 5 was PASS or its pre-registered no-move `NA`, Check 6 was
PASS, and forbidden text-bearing fields were absent.

Sensitive aggregate results remain outside Git:

- JSON:
  `D:\6003\formal_analysis\20260804_215952_formal_session_analysis_v1\results\formal_session_analysis_v1.json`
  SHA-256:
  `6D48689C936AA46F0E5482242F660533583C0AB9B14E95447E0ED908CCF32E68`
- CSV:
  `D:\6003\formal_analysis\20260804_215952_formal_session_analysis_v1\results\formal_session_analysis_v1.csv`
  SHA-256:
  `668DCC9B462CA7B3FCD5BFDE3BA564CFFBA5CE96E0EB8956A6DC6AFB3A46971E`

This record deliberately contains no participant-level or model-level action
count, ratio, qualitative statement or transcript-derived material.

## Read-only proof and shutdown

The pre-analysis and post-analysis audit files had identical raw SHA-256:

`5A4927E0A7A20FDBF5418F4C2CCBFCA27F6386DCFEF4B8F0CB5BBF1F0D9D2A9A`

They were also structurally equal to the accepted restore baseline. All three
canonical audit objects had SHA-256:

`7EB37323A2106D1EB8AC946F4B5A356CAEAF638C6BF05D510CF4F2E3180D08C3`

This establishes zero semantic database change across the analysis run. The
mongod process was then shut down through the admin shutdown command. The
mongosh client returned exit code 1 because the server closed its connection
during shutdown; the identified mongod PID exited, and ports 27017, 27018,
27019, 3000, 5173, 8000 and 11434 were all confirmed without listeners.

## Fail-closed preflight ledger

Two preflight conditions stopped before the accepted analysis execution:

1. The first startup command called `.Trim()` on the empty output of a clean
   `git status`. It failed before creating a run directory or starting a
   process. The check was corrected to an array-count assertion.
2. The first pre-analysis audit gate compared raw files and stopped because
   the newly redirected JSON lacked one trailing newline. Structured JSON
   comparison found no difference path and identical canonical SHA-256. The
   raw audit file was retained; the gate was narrowed to semantic equality
   before the one accepted analysis execution.

Neither preflight condition produced an analysis result, touched the formal
database, or caused selection according to participant or model outcomes. The
accepted analysis tool was executed exactly once and its outputs were not
overwritten.

The post-run docs-only gate also had one invocation error: the independent
prompt-freeze test was first called from the repository root, where Python
could not import the `tests` package. No test body ran. The same exact test was
then invoked from `ai-service` and passed. The non-`docs/` diff from the
operational endpoint remained empty.

## Interpretation boundary

PASS establishes provenance, integrity, partition closure and a read-only
analysis path. It does not by itself establish model quality, participant
agreement, causal effects or statistical generalisability. Quantitative
reporting must retain the labels and limitations frozen in
`formal_session_analysis_v1.md`; qualitative analysis remains a separate
transcript-based workflow.
