# Stage D G-to-G2 Instrument Upgrade Record

## Decision

Stage D formal generation under `generation-frozen-G` stopped before the
Llama block completed. A repaired prompt had already made the legal cluster
IDs explicit. Even so, `llama3.2:3b` returned an out-of-list assignment ID on
two different formal datasets. The second incident activated the standing
trigger recorded when the prompt repair was closed: another out-of-list ID
would reopen the JSON Schema decision.

This was not the `_attempt2` decision-tree trigger. The first Batch A attempt
failed with the protocol violation and its approved `_attempt2` completed.
The later Batch B violation, on a different dataset and its first attempt,
activated the older standing trigger. No Batch B retry was made.

The approved decision was to:

1. retain every G-era document and run;
2. supersede the two G-era completed formal candidates;
3. keep `generation-frozen-G` immutable;
4. implement one common structured-output instrument for all three models;
5. establish a new immutable tag, `generation-frozen-G2`, only after a new
   clean gate and explicit approval; and
6. regenerate all three G2 smokes and all nine formal documents from zero.

No G-era formal candidate may enter the final whitelist. The final nine-run
matrix may not mix G and G2.

## G-Era Attempt Ledger

The following database records remain in place and are excluded from the G2
formal whitelist.

| Class | Survey name | doc_id | run_id | Outcome and disposition |
| --- | --- | --- | --- | --- |
| Smoke | `D_SMOKE_LLAMA_batchA` | `6a64c2e83e0dbddf5447c741` | `6a64c2e93e0dbddf5447c756` | failed at `load_fragments` with `NO_EMBEDDED_FRAGMENTS`; provider not called; retained |
| Smoke | `D_SMOKE_LLAMA_batchA_attempt2` | `6a64c6bb3e0dbddf5447c757` | `6a64c6be3e0dbddf5447c76c` | completed; development/smoke exclusion |
| Formal attempt | `P1_task1_batchA` | `6a64c87f3e0dbddf5447c76f` | `6a64c8813e0dbddf5447c781` | failed assignment protocol; retained |
| Formal candidate | `P1_task1_batchA_attempt2` | `6a64e3a53e0dbddf5447c782` | `6a64e3a63e0dbddf5447c794` | completed under G; superseded; never whitelist |
| Formal candidate | `P2_task2_batchC` | `6a651c263e0dbddf5447c796` | `6a651c283e0dbddf5447c7ab` | completed under G; superseded; never whitelist |
| Formal attempt | `P3_task3_batchB` | `6a651df93e0dbddf5447c7ad` | `6a651dfa3e0dbddf5447c7c3` | failed assignment protocol; retained; no retry |

The two protocol failures occurred before cluster projection. In the Batch B
incident, assignment work had begun but the database still contained zero
persisted clusters for the failed run. This is evidence that strict failure
handling and atomic projection prevented a partial formal result from being
accepted; it is not a model-quality score.

## G2 Instrument Definition

The first implementation commit is:

`697bece97573a3f3ee616cd8dce2f17e8f400eea`

The strict-rejection log hardening commit is:

`9c87980a1c13901e5c933d6781419bed0b184814`

The shared schema version is:

`stage_d_structured_output_v1`

Strict relevance, initial-cluster, and existing-cluster assignment calls use
one provider-neutral schema builder. Existing-cluster assignment has a
dynamic enum of the legal cluster IDs for that exact call and a closed
decision envelope with exactly two alternatives:

- assign to one currently legal integer ID; or
- create a new cluster with the required fields.

The transports are:

- Ollama native `/api/generate`: schema in `format`;
- Azure/OpenAI-compatible `chat.completions.create`: strict
  `response_format=json_schema`.

The local strict parser, exact branch-shape checks, and legal-ID validation
remain in place as a second gate. Empty, refused, filtered, timed-out,
schema-invalid, or locally invalid responses still fail the run. Labelling is
unchanged and is not schema constrained. Strict assignment rejection logs
record only a SHA-256 fingerprint and response length, never the raw model
response.

Every G2 strict run must add these fields to `pipelineRuns.params`:

```text
schema_enforced: true
schema_version: stage_d_structured_output_v1
schema_transport: ollama_api_generate_format |
  openai_chat_completions_response_format_json_schema
schema_dynamic_cluster_id_enum: true
```

The existing sampling, timeout, strict-mode, freeze-label, no-SDK-retry,
model, input, research-question, and matrix requirements remain unchanged.

## Prompt Eras

The prompt regression test preserves both eras rather than replacing the
historical G record.

| Prompt | G-era SHA-256 | G2-era SHA-256 |
| --- | --- | --- |
| Relevance | `189d583cbd52e0839250fafe3cf0e73f22cf27b7cc13344178bf10435b4ab1a4` | same |
| Initial assignment | `d8ca347ba17007747c8ca0783edde2e2983dc70f19d6e0749474511972bef06b` | same |
| Existing assignment | `7bb5a5d9f0a70965314a1bc3a642f97c5410dc37c8ccab52b04926e134f7343d` | `992487fd59b21235eea7cc96ea6d539b4ff06706e22fab3208afd6862093664f` |
| Labelling | `f3c5e4b0e97cbfe06e90b7b83d28cd0c2fb50d00ec9fb181515e9467bc395536` | same |

The G-era boundary commit is
`f7421cf44cdbc075cde1fd9e7904c81a345f0519`. The G2-era boundary is the
first implementation commit named above. The existing-assignment wording
changed only to require the decision envelope used by the schema; the
semantic choice remains assignment to a legal current cluster or creation of
a new cluster.

## Capability Evidence

Before implementation, all three formal configurations passed an adversarial,
synthetic, database-free capability probe through the production provider
paths. Details, code hashes, payload hashes, live results, and the
silent-ignore limitation are in
`docs/verification_records/g2_probe.md`.

The Azure result is an empirical capability result for the recorded
`Mistral-Large-3` deployment and request. It does not generalise structured
output support to every Azure or Mistral deployment.

## Methodological Boundary

G observed protocol-following behaviour under prompt-only unconstrained
decoding. G2 changes the instrument: legal response structure is constrained
by transport-level JSON Schema and rechecked locally. Protocol adherence is
therefore no longer interpreted in the same way across the two eras. The two
G-era illegal-ID incidents remain independent evidence about unconstrained
small-model protocol behaviour; they are not mixed with G2 formal results.

The G-era Llama outputs that formed one cluster are described only as a
“G-stage repeated diagnostic observation”. G2 can change the model's choice
between a legal existing cluster and a new cluster, so no claim about
systematic Llama granularity is made until the G2 formal documents exist.

The raw provider outputs from the two Batch A attempts were not saved and
compared byte for byte. The supported statement is narrower: with the same
input, model, and requested parameters, the two runs produced different
assignment decision behaviour; the fixed seed did not guarantee identical
decision results. No claim of byte-level non-reproducibility is made.

## Gate and Version Structure

On 2026-07-26, after the implementation and log-hardening commits and before
the final law commit, the implementation gate produced:

```text
unittest discover: Ran 78 tests; OK (skipped=3)
independent G2 prompt hash: Ran 1 test; OK
```

The three skips are the explicitly gated live provider tests. Their real
three-backend results were already obtained once and are recorded in
`g2_probe.md`; ordinary discovery neither sends provider requests nor reads a
live key. The full suite included the safe probe tests, shared schema tests,
both transport mappings, dynamic-ID and second-gate tests, additive
provenance tests, atomic failure tests, and both G/G2 prompt-era records.

The G2 candidate must have a clean worktree and pass:

```powershell
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m unittest tests.test_llm_provider.PromptFreezeTests.test_current_prompts_match_g2_byte_hashes -v
```

The tag may be created only after explicit approval:

```powershell
git tag -a generation-frozen-G2 -m "Freeze Stage D G2 generation instrument"
git push origin generation-frozen-G2
```

The tag must never move or be rebuilt. After G2 is tagged, the operational
version structure is `G2 → S → audit commit`: all nine accepted formal
`pipelineRuns.code_version` values equal the G2 tag target; `S` is the
whitelist/full-ledger docs commit; one subsequent docs-only
`docs: audit record for S` commit records the S hash and equivalence results.
