# Sampling Parameter Freeze Verification Record

## Record Metadata

- Verification date: 2026-07-19
- Working branch: `codex/sampling-freeze`
- Implementation commit: `2567fc31c821146042d52b2ceac0457354e56764`
- Prompt instrument commit: `f7421cf44cdbc075cde1fd9e7904c81a345f0519`
- Result: passed; prompt and sampling parameters frozen for Stage D

The worktree was clean after the implementation commit and before both real
provider runs:

```text
## codex/sampling-freeze
```

Neither provider credentials nor response or fragment text are included in
this record.

## Frozen Parameters

The approved shared sampling profile is:

```text
LLM_TEMPERATURE=0
LLM_SEED=42
LLM_MAX_TOKENS=1024
LLM_TIMEOUT_SECONDS=60
SDK max_retries=0
```

`temperature=0` reduces requested sampling variation for the single-shot
comparison. `seed=42` is sent to both experimental provider protocols.
Provider metadata describes Ollama as `provider_supported` and the Azure
OpenAI-compatible endpoint as `best_effort_beta`; those labels record request
semantics, not a guarantee that repeated runs produce identical decisions.
`max_tokens=1024` is a shared output cap for the short JSON protocol and maps
to Ollama `num_predict=1024`.

`pipelineRuns.params` records the requested values and the provider-specific
`seed_semantics` on every new LLM Semantic run.

## Automated Verification

Command:

```powershell
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Summary:

```text
Ran 56 tests in 0.241s
OK
```

The suite verifies strict parsing and required configuration, Azure request
mapping, Ollama `options` mapping, provider-specific run metadata, and legacy
non-strict Ollama request compatibility. Python compilation also completed
without errors.

The prompt byte-hash regression test passed unchanged. No experiment prompt
was modified by the sampling implementation.

## Azure 20-Fragment Run

The existing non-sexual synthetic hospital-ward 20-row CSV was run exactly
once with the frozen profile. MongoDB recorded:

```text
run_id:          ObjectId("6a5cfaf399248706ada9ab49")
doc_id:          ObjectId("6a5cfaf099248706ada9ab34")
document:        R5_AZURE_SAMPLING_batchA
fragment_count:  20
pipeline:        llm_semantic
llm_backend:     azure
model_name:      Mistral-Large-3
params:
  column_filters:    {}
  timeout_seconds:   60
  max_retries:       0
  temperature:       0
  seed:              42
  seed_semantics:    best_effort_beta
  max_tokens:        1024
  provider_protocol: openai_v1
  model_version:     "1"
  deployment_type:   GlobalStandard
batch_label:     A
started_at:      2026-07-19T16:27:31.521Z
status:          completed
strict_mode:     true
code_version:    2567fc31c821146042d52b2ceac0457354e56764
finished_at:     2026-07-19T16:28:24.977Z
cluster_count:   13
failure_fields:  none
```

## Ollama 20-Fragment Run

After changing only the active backend/model configuration and restarting the
AI service, the same CSV and research question were run exactly once through
Ollama. MongoDB recorded:

```text
run_id:          ObjectId("6a5cfca921fc0a91ba66e6a7")
doc_id:          ObjectId("6a5cfca621fc0a91ba66e692")
document:        R5_OLLAMA_SAMPLING_batchA
fragment_count:  20
pipeline:        llm_semantic
llm_backend:     ollama
model_name:      llama3.2:3b
params:
  column_filters:  {}
  timeout_seconds: 60
  max_retries:     0
  temperature:     0
  seed:            42
  seed_semantics:  provider_supported
  max_tokens:      1024
batch_label:     A
started_at:      2026-07-19T16:34:49.715Z
status:          completed
strict_mode:     true
code_version:    2567fc31c821146042d52b2ceac0457354e56764
finished_at:     2026-07-19T16:37:44.785Z
cluster_count:   2
failure_fields:  none
```

The Azure result of 13 clusters and Ollama result of 2 clusters are retained
as observed model-granularity differences. These development runs establish
configuration and execution correctness; they are not formal comparison data
and are excluded by the formal document whitelist.

## Stage D Decision-Consistency Qualification

During G-era formal generation, two Llama runs used the same input, model,
prompt, and requested sampling parameters. The first produced an illegal
assignment decision and the approved second attempt completed with legal
assignment behaviour. The supported observation is:

> With the same input, model, and requested parameters, the two runs produced
> different assignment decision behaviour; the fixed seed did not guarantee
> identical decision results.

The raw provider outputs were not retained and compared byte for byte.
Accordingly, this record does not claim that the full outputs were or were not
byte-identical. It qualifies the earlier provider seed labels at the observed
decision level only. Complete attempt provenance is therefore required even
when temperature and seed are fixed.

## G2 Instrument Amendment

G-era prompt-only decoding produced out-of-list cluster IDs on two different
formal datasets. The approved G2 instrument retains the sampling profile in
this record but adds the shared schema version
`stage_d_structured_output_v1` and a decision-envelope change to the
existing-assignment prompt. All three models receive the same schema
semantics through their production transports, while the local strict parser
remains a second gate.

The G-era and G2 prompt hashes and the exact methodological boundary are
preserved in `docs/verification_records/g2_instrument_upgrade.md`. G-era
completed candidates are superseded; all nine accepted formal documents must
be regenerated under one `generation-frozen-G2` tag target.

## Freeze Policy

For G, the assignment prompt from commit `f7421cf` and the sampling profile
from commit `2567fc3` defined the frozen instrument. For G2, the preserved
sampling profile, the G2 prompt era, and
`stage_d_structured_output_v1` together define the frozen instrument. The
three compared models must use the same requested profile and G2 schema
semantics.

No G2 prompt, schema, or sampling value may change after G2 formal Stage D
generation starts. If a change is methodologically necessary, every formal
candidate run produced under the previous instrument is invalid and must be
regenerated. Every failed or repeated generation attempt remains in
`pipelineRuns` and must be reported.

## Verdict

Azure and Ollama both completed a real 20-fragment strict run using the shared
frozen sampling profile. The requested values were present in provider calls
through automated tests and in `pipelineRuns.params` through live MongoDB
records. Sampling is no longer a Stage D implementation blocker.
