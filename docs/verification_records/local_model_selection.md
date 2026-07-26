# Local Model Selection Verification Record

## Record Metadata

- Verification date: 2026-07-22
- Working branch: `codex/stage-d-handover`
- Code version used by both gate runs: `5ad64ba0b5e03fe83440f32b97d4303e29a61a10`
- Dataset: existing 20-row non-sexual synthetic hospital-ward CSV
- Result: final local models selected as `llama3.2:3b` and `qwen2.5:3b`

The worktree was clean and the frozen prompt hash test passed immediately
before the candidate-model gate runs. Each candidate was attempted once. No
prompt, sampling parameter, timeout, or retry setting was changed between the
two runs.

## Installed Model Digests

The Ollama `/api/tags` endpoint returned:

```text
llama3.2:3b
  digest: a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72
  size:   2019393189 bytes

qwen2.5:3b
  digest: 357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b
  size:   1929912432 bytes

qwen2.5:7b
  digest: 845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e
  size:   4683087332 bytes
```

Formal generation must recheck that the tag and digest for the selected model
match this record before each model block.

## Pre-Registered Selection Rule

`qwen2.5:7b` was preferred because it would add a local hardware/quality
gradient to the 3B and cloud comparison. Before final selection it had to
complete one strict 20-row run under the frozen 60-second per-call timeout.

The rule fixed before testing was:

1. If `qwen2.5:7b` completed, select `llama3.2:3b + qwen2.5:7b`.
2. If it failed strict protocol validation or timed out, do not tune a
   model-specific setting or select a favourable retry. Preserve the failure
   and test the predefined fallback `qwen2.5:3b` once.
3. If `qwen2.5:3b` completed, select
   `llama3.2:3b + qwen2.5:3b`.

## Qwen 7B Gate Result

The only `qwen2.5:7b` attempt failed during the first relevance call:

```text
run_id:              ObjectId("6a60c48ce95639a03fc06025")
doc_id:              ObjectId("6a60c487e95639a03fc06010")
document:            D_GATE_QWEN7B_batchA
fragment_count:      20
pipeline:            llm_semantic
llm_backend:         ollama
model_name:          qwen2.5:7b
params:
  column_filters:  {}
  timeout_seconds: 60
  max_retries:     0
  temperature:     0
  seed:            42
  seed_semantics:  provider_supported
  max_tokens:      1024
batch_label:         A
started_at:          2026-07-22T13:24:28.417Z
status:              failed
strict_mode:         true
code_version:        5ad64ba0b5e03fe83440f32b97d4303e29a61a10
failed_at:           2026-07-22T13:25:32.297Z
failure_code:        LLM_REQUEST_FAILED
failure_fragment_id: ObjectId("6a60c488e95639a03fc06011")
failure_message:     LLM relevance filtering failed.
failure_stage:       relevance_filter
failure_type:        ReadTimeout
cluster_count:       0
```

The run ended about 63.9 seconds after it started. This is evidence of the
candidate exceeding the shared 60-second call limit on the test machine, not
evidence of an ID/JSON protocol violation. Strict mode correctly persisted no
cluster projection. The run was not retried and the timeout was not relaxed.

## Qwen 3B Fallback Result

The predefined fallback was then attempted once under the identical frozen
instrument:

```text
run_id:          ObjectId("6a60c69b1d503752e2c55f4c")
doc_id:          ObjectId("6a60c6981d503752e2c55f37")
document:        D_GATE_QWEN3B_batchA
fragment_count:  20
pipeline:        llm_semantic
llm_backend:     ollama
model_name:      qwen2.5:3b
params:
  column_filters:  {}
  timeout_seconds: 60
  max_retries:     0
  temperature:     0
  seed:            42
  seed_semantics:  provider_supported
  max_tokens:      1024
batch_label:     A
started_at:      2026-07-22T13:33:15.453Z
status:          completed
strict_mode:     true
code_version:    5ad64ba0b5e03fe83440f32b97d4303e29a61a10
finished_at:     2026-07-22T13:35:34.439Z
elapsed_seconds: 138.986
cluster_count:   6
failure_fields:  none
```

The six-cluster output is retained as observed granularity, not treated as a
selection score. This gate tested reliable completion under the common
instrument; it did not compare clustering quality.

## Verdict

The final three-model experiment set is:

```text
local 1: llama3.2:3b
local 2: qwen2.5:3b
cloud:   Mistral-Large-3 (Azure deployment version 1, GlobalStandard)
```

`qwen2.5:7b` is excluded from participant-facing document generation because
its single pre-registered gate attempt on the test hardware timed out during
the first relevance call under the shared 60-second limit. The run was not
retried and the limit was not relaxed. This is one local observation, not a
claim that the 7B model is generally unavailable. The failed run remains a
development finding relevant to the local hardware/cost discussion and
limitation section; it is not formal participant comparison data.

## G2 Addendum

The G-to-G2 structured-output upgrade does not reopen model selection. Before
implementation, both selected local configurations passed one synthetic,
database-free assignment-schema probe through the production Ollama
`/api/generate` provider path. Each used its recorded digest, made one request
with zero retry, and returned a locally schema-valid legal assignment despite
an adversarial illegal-ID instruction.

This is a transport/capability gate, not a clustering-quality comparison and
not a replacement for the required G2 smoke. In particular,
`qwen2.5:3b` had not yet produced a Stage D G-era formal run; its first
end-to-end G2 strict behaviour will be observed in the G2 smoke and formal
block. Full probe evidence is in
`docs/verification_records/g2_probe.md`.
