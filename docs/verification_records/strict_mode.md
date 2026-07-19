# Strict Mode Verification Record

## Record Metadata

- Verification date: 2026-07-18; rechecked 2026-07-19
- Feature and prompt-fix commit: `f7421cf44cdbc075cde1fd9e7904c81a345f0519`
- Backend/model: `ollama` / `llama3.2:3b`
- Result: passed

Clean worktree output recorded before the post-fix manual run:

```text
## provenance-extension...origin/provenance-extension [ahead 1]
```

Current configuration recheck confirms that unused cloud keys are absent while
the active Ollama backend remains valid:

```text
llm_backend=ollama
llm_strict_mode=true
model_name=llama3.2:3b
openai_key_present=false
anthropic_key_present=false
```

## Automated Verification

Command:

```powershell
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -p test_llm_strict_mode.py -v
```

Summary from the 2026-07-19 recheck:

```text
Ran 20 tests in 0.011s
OK
```

The suite covers strict boolean/backend validation, active-backend-only key
validation, request failures, invalid JSON and response types, lossless ID
normalisation, unknown-ID rejection, prompt ID enumeration, explicit run
states, and zero persistence after a mid-run LLM failure.

## Fail-Loud Diagnostic Evidence

Before the prompt ambiguity was corrected, the diagnostic logger captured the
model's original assignment response:

```text
Strict LLM assignment response rejected
stage=cluster_assignment
code=INVALID_LLM_RESPONSE
valid_cluster_ids=[0, 1]
raw_response={"action": "assign", "cluster_id": 2}
```

The matching `pipelineRuns` record contains:

```text
doc_id:              ObjectId("6a5b94a519eea56016ac24c7")
pipeline:            llm_semantic
llm_backend:         ollama
model_name:          llama3.2:3b
started_at:          2026-07-18T14:58:48.913Z
status:              failed
strict_mode:         true
failed_at:           2026-07-18T15:00:29.058Z
failure_code:        INVALID_LLM_RESPONSE
failure_fragment_id: ObjectId("6a5b94a619eea56016ac24cb")
failure_message:     LLM assign response references unknown cluster_id=2; valid_cluster_ids=[0, 1].
failure_stage:       cluster_assignment
failure_type:        LLMStrictModeError
cluster_count:       0
theme_one_count:     0
```

This diagnostic run occurred while the strict implementation was still an
uncommitted worktree change, so its recorded `code_version` is the preceding
commit `f514f0a`. It is retained as diagnostic evidence only and is not eligible
for experiment analysis.

The response established that the validator was correct and the original
assignment prompt was under-specified. Commit `f7421cf` then made the valid
integer ID list and the `new` action exit explicit for every model.

## Clean Post-Fix Completed Run

One controlled 20-row rerun after the prompt correction produced:

```text
document:     STRICT_PROMPT_batchA
doc_id:       ObjectId("6a5b97b07769c059d29cbaac")
pipeline:     llm_semantic
llm_backend:  ollama
model_name:   llama3.2:3b
batch_label:  A
started_at:   2026-07-18T15:11:47.949Z
status:       completed
strict_mode:  true
code_version: f7421cf44cdbc075cde1fd9e7904c81a345f0519
finished_at:  2026-07-18T15:14:39.002Z
cluster_count: 4
theme_one_count: 0
```

The first rerun with the corrected and committed instrument completed, so JSON
Schema constraints were not introduced. A future out-of-range ID or repeated
formal-generation failure reopens that recorded design decision; every attempt
must remain in `pipelineRuns`.

## Verdict

Strict mode fails loudly, records an explicit failed run without persisting
heuristic clusters, and records completed runs only after valid LLM output and
successful persistence. The prompt correction was a construct-validity repair
applied uniformly to all compared models, not a model-specific allowance.
