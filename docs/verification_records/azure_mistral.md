# Azure Mistral Backend Verification Record

## Record Metadata

- Verification date: 2026-07-19
- Working branch: `codex/azure-mistral-backend`
- Shared-provider commit: `936fdda45adfdbc33f9f2ce96c8f6412a033636f`
- Azure-backend commit: `434efe13b02174408348b541d940f31db68a657e`
- Deployment/model: `Mistral-Large-3`
- Model version: `1`
- Deployment type: `GlobalStandard`
- Deployment deactivation date shown by the portal: 2099-12-31 00:00
- Result: implementation verification passed; C2 closure remains pending

The worktree was clean after both implementation commits and before the real
Azure runs:

```text
## codex/azure-mistral-backend
```

The API key is stored only in the ignored root `.env`. No key, prompt, model
response, or fragment text is included in this record.

## Automated Verification

Command:

```powershell
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Summary from the post-manual-test recheck:

```text
Ran 50 tests in 0.277s
OK
```

The suite includes active-backend-only configuration validation, Azure URL and
hostname validation, disabled SDK retries, shared clusterer/labeller provider
dispatch, Azure deployment provenance, secret redaction, HTTP 400 content
filter errors, HTTP 200 `finish_reason=content_filter`, strict failure-code
preservation, and zero projection persistence after filtering.

The refactor also preserved all four experiment prompt byte hashes:

```text
relevance:           189d583cbd52e0839250fafe3cf0e73f22cf27b7cc13344178bf10435b4ab1a4
initial assignment:  d8ca347ba17007747c8ca0783edde2e2983dc70f19d6e0749474511972bef06b
existing assignment: 7bb5a5d9f0a70965314a1bc3a642f97c5410dc37c8ccab52b04926e134f7343d
labelling:           f3c5e4b0e97cbfe06e90b7b83d28cd0c2fb50d00ec9fb181515e9467bc395536
```

## C1 Real Ollama Regression

Before adding Azure, the shared provider completed a real one-fragment Ollama
run. The MongoDB record was:

```text
run_id:        ObjectId("6a5cda82f1c3d2e948d2508b")
doc_id:        ObjectId("6a5cda7df1c3d2e948d25089")
pipeline:      llm_semantic
llm_backend:   ollama
model_name:    llama3.2:3b
batch_label:   A
started_at:    2026-07-19T14:09:06.781Z
status:        completed
strict_mode:   true
code_version:  936fdda45adfdbc33f9f2ce96c8f6412a033636f
finished_at:   2026-07-19T14:09:25.654Z
fragment_count: 1
cluster_count:  1
```

This is a real-provider regression check, not formal experiment data.

## Timeout Compatibility Evidence

At the pre-refactor commit `6f4be60`, both Ollama call sites used:

```python
httpx.Client(timeout=60)
```

The shared provider now reads `LLM_TIMEOUT_SECONDS=60` and applies that value
to Ollama. Therefore the C2 timeout is **unchanged** for the local backend: it
is neither a tightening nor a relaxation of the original Ollama behaviour.

A controlled one-fragment diagnostic exercised the same strict relevance and
initial-assignment methods through the real shared Ollama provider. It recorded
per-call wall-clock times without printing prompts or responses:

```text
call_count=2
call_seconds=12.011,4.593
relevance_protocol_valid=True
assignment_protocol_valid=True
```

Both observed calls completed below the 60-second timeout. This diagnostic is
a local timing observation, not a guarantee that every future call will finish
within 60 seconds and not an experiment-eligible pipeline run.

## Azure Startup Validation

The first manual startup deliberately used a full chat-completions URL. The AI
service rejected it before accepting requests:

```text
RuntimeError: AZURE_OPENAI_BASE_URL must end at /openai/v1/, not /chat/completions.
```

After correcting the value to the Foundry `/openai/v1/` base URL, Uvicorn
reported:

```text
Application startup complete.
```

No pipeline run was created by the rejected startup.

## Azure 20-Fragment Smoke Run

This smoke test used the existing 20-row non-sexual synthetic hospital-ward
dataset. It was not the permission-gated COMP2300 sexual-health material. The
key MongoDB fields were captured as follows:

```text
run_id:          ObjectId("6a5ce7de7c6951dc31361a4f")
doc_id:          ObjectId("6a5ce7d87c6951dc31361a3a")
pipeline:        llm_semantic
llm_backend:     azure
model_name:      Mistral-Large-3
params:
  column_filters:    {}
  timeout_seconds:   60
  max_retries:       0
  temperature:       0.2
  max_tokens:        null
  provider_protocol: openai_v1
  model_version:     "1"
  deployment_type:   GlobalStandard
batch_label:     A
started_at:      2026-07-19T15:06:06.330Z
status:          completed
strict_mode:     true
code_version:    434efe13b02174408348b541d940f31db68a657e
finished_at:     2026-07-19T15:07:09.388Z
fragment_count:  20
cluster_count:   13
failure_fields:  none
```

The 13-cluster result is retained as observed model granularity, not treated as
an implementation defect.

## Ollama-Offline Backend Isolation

The operator stopped Ollama and confirmed its API was unusable:

```text
Invoke-WebRequest http://localhost:11434/api/tags -TimeoutSec 3
Invoke-WebRequest : The operation has timed out.
```

With Ollama still unavailable and `LLM_BACKEND=azure`, a one-fragment Azure run
completed. Its MongoDB evidence was:

```text
run_id:          ObjectId("6a5ce9aa7c6951dc31361a5f")
doc_id:          ObjectId("6a5ce9aa7c6951dc31361a5d")
pipeline:        llm_semantic
llm_backend:     azure
model_name:      Mistral-Large-3
params:
  column_filters:    {}
  timeout_seconds:   60
  max_retries:       0
  temperature:       0.2
  max_tokens:        null
  provider_protocol: openai_v1
  model_version:     "1"
  deployment_type:   GlobalStandard
batch_label:     A
started_at:      2026-07-19T15:13:46.341Z
status:          completed
strict_mode:     true
code_version:    434efe13b02174408348b541d940f31db68a657e
finished_at:     2026-07-19T15:13:50.552Z
fragment_count:  1
cluster_count:   1
failure_fields:  none
```

Ollama was then restarted and its `/api/tags` endpoint returned HTTP 200.

## Missing-Key Fail-Loud Validation

With Azure still selected, `AZURE_OPENAI_API_KEY` was temporarily blanked. The
AI service rejected startup with:

```text
RuntimeError: Missing required configuration for LLM_BACKEND='azure': AZURE_OPENAI_API_KEY.
```

The latest `pipelineRuns` record remained the completed offline-isolation run
`6a5ce9aa7c6951dc31361a5f`; no false, failed, or permanently running record was
created by this startup validation. The rotated key was then restored locally,
and the service again reached `Application startup complete`.

## Content-Filter Status

Automated tests prove that Azure HTTP 400 policy errors and HTTP 200 responses
with `finish_reason=content_filter` become strict run failures with:

```text
failure_code: CONTENT_FILTERED
```

They also prove that no cluster projection is persisted on this failure path.
No real content-filter incident occurred during the non-sexual smoke tests, so
this record does not claim a live Azure policy-block response.

## Pre-Registered Sexual-Health Smoke Test

Before running the permission-approved smoke test, the following probe and
decision rules were fixed in this record:

```text
local file:     test-data/private/sexual_health_content_filter_smoke_1row.csv
source:         COMP2300 P1 answer about stigma and help-seeking concerns
selection:      participant answer only; interviewer and demographics excluded
length:         110 words
CSV SHA-256:    b1de182ceabc960dbb7fd399d2815a2c45830096d4b32ad756d432d4da66095c
research focus: factors influencing access to and experience of sexual-health services
attempt limit:  one terminal attempt, except for a non-filter infrastructure/protocol failure
```

The source HTML and derived CSV are ignored local files. Neither the COMP2300
text nor a reversible representation of it may enter Git history.

The outcome rules are:

1. `status: "completed"` with a normal response is a terminal pass. It lowers
   the observed content-filter risk for this one probe only.
2. `failure_code: "CONTENT_FILTERED"` is a terminal policy finding, not a
   software failure. Record whether it was the HTTP 400 or HTTP 200
   `finish_reason=content_filter` form and whether it occurred during relevance
   or initial assignment. Do not alter the prompt or retry.
3. Any other network or protocol failure is not evidence about content
   filtering. After fixing the environment, exactly one rerun is allowed and
   both attempts must remain recorded.

Because a one-row input only exercises relevance filtering followed by the
first-cluster creation branch, this test cannot establish sexual-health
performance for existing-cluster assignment or a full formal batch.

## Sexual-Health Smoke Test Result

The pre-registered probe was run once. It reached the terminal-pass outcome;
no retry was attempted. MongoDB recorded:

```text
run_id:          ObjectId("6a5cf34bcfc29aafa1f37fc9")
doc_id:          ObjectId("6a5cf348cfc29aafa1f37fc7")
document:        C2_AZURE_SEXUAL_HEALTH_SMOKE_batchA
pipeline:        llm_semantic
llm_backend:     azure
model_name:      Mistral-Large-3
params:
  column_filters:    {}
  timeout_seconds:   60
  max_retries:       0
  temperature:       0.2
  max_tokens:        null
  provider_protocol: openai_v1
  model_version:     "1"
  deployment_type:   GlobalStandard
batch_label:     A
started_at:      2026-07-19T15:54:51.647Z
status:          completed
strict_mode:     true
code_version:    fbac702e310a6cadec25352d7da38a3abe01b130
finished_at:     2026-07-19T15:54:57.541Z
fragment_count:  1
cluster_count:   1
failure_fields:  none
```

Azure did not content-filter this selected sexual-health probe. This lowers the
observed filtering risk for the selected stigma/help-seeking passage only. It
does not establish filter behaviour or clustering quality for the remaining
COMP2300 material or for a multi-fragment formal batch.

## C2 Closure

C2 closed on 2026-07-19 after all recorded conditions were completed:

```text
sexual-health smoke test: completed once; no content filter
session manual update:     fb67891
merge commit:              73816a6
merged branch:             provenance-extension
push target:               origin/provenance-extension
post-push divergence:      0 local-only / 0 remote-only commits
post-merge automated test: 50 tests; OK
```

The sampling-parameter decision and subsequent prompt/parameter freeze remain
mandatory gates before Stage D formal document generation. They are the next
methodology step and do not reopen the completed C2 backend-integration work.

## G2 Structured-Output Capability Addendum

On 2026-07-26 the configured Azure `Mistral-Large-3`, version `1`,
`GlobalStandard` deployment accepted one strict
`response_format=json_schema` request through the same OpenAI SDK
`chat.completions.create` path used by the production provider. The synthetic
prompt requested an illegal assignment ID while the schema allowed only ID
`0` or a valid new-cluster branch. The response ended with
`finish_reason=stop`, selected legal ID `0`, and passed the local schema
validator. One request was made with zero retry and no MongoDB write.

Microsoft's published structured-output support list did not name this model.
The project therefore treats the live result as capability evidence for this
recorded deployment and request only, not as a general claim about all Azure
or Mistral deployments. One valid answer also cannot prove that the service
did not silently ignore the schema and independently comply; the adversarial
prompt reduces that risk, while the unchanged local strict parser remains the
second gate.

The full three-backend probe, formalised probe hash, schema hash, production
base-payload hashes, safe rerun mode, and interpretation limit are recorded in
`docs/verification_records/g2_probe.md`. The G-to-G2 decision boundary is in
`docs/verification_records/g2_instrument_upgrade.md`.
