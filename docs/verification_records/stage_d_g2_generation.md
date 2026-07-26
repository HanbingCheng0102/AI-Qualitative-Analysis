# Stage D G2 Generation and Session-Analysis Record

## Scope

This record freezes the completed Stage D G2 generation matrix and the
operational analysis/session decisions transcribed into S. It contains no
restricted response text, Azure secret, raw provider output, or formal CSV.
Smoke and formal generation finished before this docs-only record was
created. No PILOT, MongoDB write, service start, model call, or `.env` change
is part of S.

## Immutable generation credentials

| Credential | Value |
| --- | --- |
| Historical instrument tag | `generation-frozen-G` |
| Historical instrument G | `da47d0eda734fc4136b8303a03d09e2d5f78c95f` |
| Final generation tag | `generation-frozen-G2` |
| Final generation instrument G2 | `544540beedb707c2be5c08fa1647107f80587c84` |
| G2 tag date | 2026-07-26 |
| Schema version | `stage_d_structured_output_v1` |
| Formal matrix result | 9/9 completed and accepted |
| Formal retry count | 0; all nine G2 formal documents completed on attempt 1 |
| Matrix-level read-only audit | PASS; no field-level errors |

All nine accepted `pipelineRuns.code_version` values equal the G2 full hash.
`generation-frozen-G2` is immutable. G-era and G2 records are not mixed.

## Private-ledger transcription provenance

During the frozen generation period, each attempt was written first to an
ignored private ledger. Tracked docs were intentionally left unchanged until
9/9 completed; S transcribes the ledgers once.

| Ledger | SHA-256 at S transcription | Role |
| --- | --- | --- |
| `test-data/private/g2_smoke_ledger.txt` | `508c4231ce8c666f974ba74583905f1aecc74850ab542d4bca1669dcfe16b542` | G2 smoke attempts and S method notes |
| `test-data/private/g2_formal_ledger.txt` | `43947384b376968dc51150bd116b2180594ab5906877da491608241af71e9f35` | nine formal records and session-analysis notes |
| `D:\6003\g2_formal_ledger_9_of_9.txt` | `43947384b376968dc51150bd116b2180594ab5906877da491608241af71e9f35` | repository-external final formal-ledger backup |

The matching formal-ledger hashes prove that the repository-external backup
and the ignored source ledger had identical bytes at 9/9. Private ledgers
remain excluded from Git. “Record immediately after each run” means the
ignored ledger plus its external backup; tracked docs are updated only once
after 9/9 in S.

## G2 smoke ledger

All smoke input was the approved 20-row synthetic non-study CSV with
SHA-256
`9270f9dad53d00777e822b5c26356f5eab28a3a1cae9e64ee6c6f50d8fadcd7a`.
Smoke is development/configuration evidence and never enters Results or the
formal whitelist.

| Survey/attempt | doc_id | run_id | Actual backend/model | fragments/embedded | kept/filtered | clusters | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `D_SMOKE_G2_LLAMA_batchA` attempt 1 | `6a660bdef041b5fef471e029` | `6a660be2f041b5fef471e03e` | `azure` / `Mistral-Large-3` | 20/20 | 15/5 | 12 | run completed but acceptance failed: stale Azure listener caused backend mismatch; retained and excluded |
| `D_SMOKE_G2_LLAMA_batchA_attempt2` | `6a66119a59652a872b0639b2` | `6a66123e59652a872b0639c7` | `ollama` / `llama3.2:3b` | 20/20 | 15/5 | 5 | approved environment-recovery retry; completed and accepted as Llama smoke |
| `D_SMOKE_G2_QWEN_batchA` | `6a661d1ec2a3cea7e6de6028` | `6a661dc2c2a3cea7e6de603d` | `ollama` / `qwen2.5:3b` | 20/20 | 6/14 | 1 | completed and accepted |
| `D_SMOKE_G2_AZURE_batchA` | `6a661f814b63e7a3c45dd144` | `6a661f844b63e7a3c45dd159` | `azure` / `Mistral-Large-3` | 20/20 | 16/4 | 13 | completed and accepted |

The backend-mismatch record is an environment incident, not a provider,
schema, data, or model failure. Its completed status did not override the
field-level acceptance failure. The accepted attempt2 was explicitly
authorised; there was no automatic retry.

## G-era retained and superseded attempts

| Class | Survey name | doc_id | run_id | Outcome | Permanent disposition |
| --- | --- | --- | --- | --- | --- |
| Smoke attempt | `D_SMOKE_LLAMA_batchA` | `6a64c2e83e0dbddf5447c741` | `6a64c2e93e0dbddf5447c756` | failed at `load_fragments`: `NO_EMBEDDED_FRAGMENTS`; provider not called | orchestration incident; retain and exclude; not a schema failure |
| Smoke attempt2 | `D_SMOKE_LLAMA_batchA_attempt2` | `6a64c6bb3e0dbddf5447c757` | `6a64c6be3e0dbddf5447c76c` | completed | development/smoke exclusion |
| Formal attempt | `P1_task1_batchA` | `6a64c87f3e0dbddf5447c76f` | `6a64c8813e0dbddf5447c781` | failed assignment: out-of-list cluster ID | retain and exclude |
| Formal attempt2 | `P1_task1_batchA_attempt2` | `6a64e3a53e0dbddf5447c782` | `6a64e3a63e0dbddf5447c794` | completed | superseded by G2; never whitelist |
| Formal attempt | `P2_task2_batchC` | `6a651c263e0dbddf5447c796` | `6a651c283e0dbddf5447c7ab` | completed | superseded by G2; never whitelist |
| Formal attempt | `P3_task3_batchB` | `6a651df93e0dbddf5447c7ad` | `6a651dfa3e0dbddf5447c7c3` | failed assignment: out-of-list cluster ID | standing trigger activated; retain and exclude; no retry |

The three G-era first formal attempts were 1/3 completed; two failed because
of illegal assignment IDs. The Batch A retry and Batch C completed
candidates remain provenance evidence but are superseded. The unembedded G
smoke was an API-orchestration accident and does not count as a schema
failure.

## Accepted G2 formal matrix

| Document | Model | doc_id | run_id | fragments/embedded | kept/filtered | clusters | finished_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P1_task1_batchA` | `llama3.2:3b` | `6a6621355e9bd7a009d1b97f` | `6a66213a5e9bd7a009d1b991` | 17/17 | 15/2 | 7 | `2026-07-26T15:04:07.601000Z` |
| `P2_task2_batchC` | `llama3.2:3b` | `6a662346b88c6db2d9915ac9` | `6a66234bb88c6db2d9915ade` | 20/20 | 20/0 | 15 | `2026-07-26T15:13:32.846000Z` |
| `P3_task3_batchB` | `llama3.2:3b` | `6a6625e3460dababa39a9be4` | `6a6625e7460dababa39a9bfa` | 21/21 | 19/2 | 6 | `2026-07-26T15:24:25.873000Z` |
| `P1_task3_batchC` | `qwen2.5:3b` | `6a662813ed5bcd0c9d8a4439` | `6a662818ed5bcd0c9d8a444e` | 20/20 | 17/3 | 2 | `2026-07-26T15:33:23.828000Z` |
| `P2_task1_batchB` | `qwen2.5:3b` | `6a666d4f04fc296116b621af` | `6a666d5404fc296116b621c5` | 21/21 | 16/5 | 1 | `2026-07-26T20:28:42.553000Z` |
| `P3_task2_batchA` | `qwen2.5:3b` | `6a666f0d5f60ce182f69ff12` | `6a666f125f60ce182f69ff24` | 17/17 | 16/1 | 1 | `2026-07-26T20:35:58.113000Z` |
| `P1_task2_batchB` | `Mistral-Large-3` | `6a6672adaaaa46976afdb5ba` | `6a6672b1aaaa46976afdb5d0` | 21/21 | 20/1 | 11 | `2026-07-26T20:49:54.237000Z` |
| `P2_task3_batchA` | `Mistral-Large-3` | `6a667375aaaa46976afdb5dc` | `6a667376aaaa46976afdb5ee` | 17/17 | 16/1 | 8 | `2026-07-26T20:52:46.838000Z` |
| `P3_task1_batchC` | `Mistral-Large-3` | `6a6673f2aaaa46976afdb5f7` | `6a6673f3aaaa46976afdb60c` | 20/20 | 19/1 | 10 | `2026-07-26T20:55:01.170000Z` |

All nine were first formal attempts and passed these checks:

- `status="completed"` with `finished_at`;
- `pipeline="llm_semantic"` and `strict_mode=true`;
- exact G2 `code_version`;
- exact matrix backend/model/batch label;
- manifest fragment and full embedding counts;
- timeout 60, temperature 0, seed 42, max tokens 1024, max retries 0;
- `schema_enforced=true`,
  `schema_version="stage_d_structured_output_v1"`,
  `schema_dynamic_cluster_id_enum=true`, and the correct backend transport;
- Azure version `1`, deployment `GlobalStandard`,
  `provider_protocol="openai_v1"`, and
  `seed_semantics="best_effort_beta"`; and
- no `failure_*` field.

The historical same-name development document
`P1_task2_batchB / 6a58d2cd1d6d1e80c35ba564` remains excluded. The accepted
Azure document is `6a6672adaaaa46976afdb5ba`; analysis must never select by
survey name.

## Frozen exclusion gates

Formal participant identities are exactly `P1`, `P2`, and `P3`. The S
participant exclusion snapshot is:

```text
TEST
P_TEST
P_OTHER
PILOT
RACE_TEST
RACE_TEST_1
RACE_TEST_2
REL_TEST
SWAGGER_REL
VERIFY_REL
VERIFY_REL_2
```

The private generation ledgers introduced no additional participant
identity. Formal analysis must still enumerate real
`clusterFeedback.participant_id` values before analysis and fail closed on an
unregistered identity.

Document eligibility uses two gates simultaneously: the ID must be one of the
nine formal whitelist IDs and must not be in the development/smoke exclusion
table in `docs/P1_session_manual.md`. Missing, overlapping, name-selected, or
partially populated gates fail closed.

## Instrument-reliability interpretation

G→G2 is evidence about generation-instrument reliability and the
provenance-driven stop/review/refreeze process. It is not a model-quality
result. On the G-era Batch B trigger case, 19 kept fragments reached
assignment before an illegal ID stopped the run and atomic projection left no
partial accepted result. Under G2, the first run on the same formal Batch B
completed and assigned all 19 kept fragments. This closes the specific
problem for which the G2 upgrade was commissioned; it does not prove that all
future structured runs cannot fail.

Structured decoding was not a neutral post-processing correction. The formal
granularity profiles were:

- Qwen: `1/1/2`, consistently coarse;
- Azure Mistral: `8/11/10`, intermediate and comparatively stable; and
- Llama: `6/7/15`, substantially higher than G-era diagnostic outputs and
  variable by batch.

On identical Batch C bytes, the cluster counts were Llama 15, Qwen 2, and
Azure 10. These counts describe instrument/model behaviour and anticipated
session burden; generation did not use them to select or regenerate a
document. Smoke granularity and relevance filtering remain development
evidence and are excluded from Results.

The study's three accepted formal Azure runs did not observe
`CONTENT_FILTERED`. This statement is limited to those three recorded runs
and cannot be generalised to other prompts, inputs, deployments, Azure
models, or future requests.

## Session-analysis decisions frozen in S

The analysis unit is participant + document + fragment. Valid confirm/move
events are sorted by `{timestamp: -1, _id: -1}`; the first is the latest
effective action. A later move supersedes an earlier confirm for current-state
classification, while both provenance events remain stored.

Eligible fragments are the kept fragments that entered the Cluster Graph.
For each participant and document:

- confirm / eligible is confirmation coverage or a lower bound on
  endorsement;
- move / eligible is the explicit correction rate; and
- an eligible fragment without a valid event is
  `no recorded decision (reject-or-unreviewed)`.

Confirm / eligible must not be shortened to a complete “acceptance rate”.

The two one-cluster documents are:

- `P2_task1_batchB / 6a666d4f04fc296116b621af`; and
- `P3_task2_batchA / 6a666f0d5f60ce182f69ff12`.

Move is structurally unavailable on them. Natural split, merge, and
navigation comments are recorded in physically separate think-aloud/field
notes; the researcher does not prompt for them, and they are never encoded as
`clusterFeedback`. A future UI or schema change requires a separate
instrument version.

## PILOT isolation decision

The nine whitelisted documents are read-only before formal sessions. PILOT
must not operate on their doc IDs in the formal `nie` database. A
`participant=PILOT` label does not isolate recluster side effects:
`fragment.cluster_id`, cluster membership, and centroid are global document
state.

The P2 rehearsal must use a separate `nie_pilot` database or independently
verified dedicated copies. Copy verification must fail closed and PILOT data
never enters formal analysis. S records only this rule: no copy is made and
no PILOT is started here. The isolation/copy plan requires separate approval
after S.

## Operational S audit slot

The operational S commit cannot contain its own hash. The single permitted
audit commit with message `docs: audit record for S` replaces only the
audit-only values below; it does not change an operational rule.

| Audit item | Value recorded by the audit commit |
| --- | --- |
| S full hash | `PENDING_AUDIT_COMMIT` |
| Validation date | `PENDING_AUDIT_COMMIT` |
| `git status --short` at S | `PENDING_AUDIT_COMMIT` |
| `generation-frozen-G2..S` non-doc diff | `PENDING_AUDIT_COMMIT` |
| G2 prompt-hash test at S | `PENDING_AUDIT_COMMIT` |
