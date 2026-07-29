# Formal Retention, Input-Order, and Resource Audit

Status: retention and input-order evidence accepted; formal timing accepted;
Qwen resource measurement accepted; Llama cold-boot repeat and Azure cost
remain open.

Date: 2026-07-29

## Scope and gates

This record contains no restricted response text, formal CSV, embedding,
provider output, or secret. The formal audit:

- connected only to `mongodb://127.0.0.1:27017/nie`;
- hard-coded the nine approved formal `doc_id` values as a whitelist;
- performed read-only `find`, `find_one`, `count`, and aggregation in local
  memory;
- did not start the API, AI, React, Ollama, or participant interfaces; and
- stopped the formal MongoDB process immediately after each audit.

Resource instrumentation used fresh restored `nie_pilot` copies on port
27018. It did not connect to or write to formal `nie`.

The code state required for the separate instrumentation runs was:

```text
ddb5355972ca63df44edad184b11e30f420e4c62
```

## Retention coverage

For these nine documents, the stored unassigned-fragment count exactly equals
the generation ledger's relevance-filtered count. All nine satisfy:

```text
input = kept + filtered
```

The independently checked third bucket is zero in every document: no missing
embedding, blank redacted input, invalid cluster reference, missing/extra
cluster membership, or cluster-size inconsistency contributed another
category.

| Document | Model | Batch | Input | Kept | Filtered | Retention |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `P1_task1_batchA` | `llama3.2:3b` | A | 17 | 15 | 2 | 88.2% |
| `P2_task2_batchC` | `llama3.2:3b` | C | 20 | 20 | 0 | 100.0% |
| `P3_task3_batchB` | `llama3.2:3b` | B | 21 | 19 | 2 | 90.5% |
| `P1_task3_batchC` | `qwen2.5:3b` | C | 20 | 17 | 3 | 85.0% |
| `P2_task1_batchB` | `qwen2.5:3b` | B | 21 | 16 | 5 | 76.2% |
| `P3_task2_batchA` | `qwen2.5:3b` | A | 17 | 16 | 1 | 94.1% |
| `P1_task2_batchB` | `Mistral-Large-3` | B | 21 | 20 | 1 | 95.2% |
| `P2_task3_batchA` | `Mistral-Large-3` | A | 17 | 16 | 1 | 94.1% |
| `P3_task1_batchC` | `Mistral-Large-3` | C | 20 | 19 | 1 | 95.0% |

Each model therefore received the same 58 inputs:

| Model | Kept/input | Observed retention |
| --- | ---: | ---: |
| `llama3.2:3b` | 54/58 | 93.1% |
| `qwen2.5:3b` | 49/58 | 84.5% |
| `Mistral-Large-3` | 55/58 | 94.8% |

The Qwen aggregate is materially influenced by one document:
`P2_task1_batchB` accounts for 5 of its 9 filtered fragments. Aggregate and
per-document rows must therefore be presented together.

Retention is not an accuracy or quality measure. Filtering an irrelevant
fragment is expected behaviour; without relevance ground truth, lower
retention may reflect either better discrimination or false-negative
omission. Permitted wording is:

> Observed retention differed across models; without relevance ground truth,
> retention cannot be interpreted as accuracy.

Qwen's lower observed retention and its `1/1/2` cluster profile are
*consistent with* a shared loss-of-discrimination hypothesis, but the present
data do not establish an effect or causal relationship.

## Fragment identity and processing order

ObjectIds differ across independent ingests and were not used as
cross-document fragment identity. The audit canonicalised `row_data`,
`row_num`, and `survey_question_key`, hashed each input, and compared both
multisets and sequences without printing individual text or hashes.

Multiset evidence:

| Batch | Count | Multiset SHA-256 | Three documents identical |
| --- | ---: | --- | --- |
| A | 17 | `c415ea08c3871b1ff5b937c196797c04405cbed0f1fe4691a5142732d489e7b6` | yes |
| B | 21 | `eff5d47ad974aac74acf7dec839aba4dd4a3c78b66114e40761d9f39c4d151b3` | yes |
| C | 20 | `a88a44acf6ea4f3c81c7670610451b50ec8ef5032b2f4910ff158714de807b6f` | yes |

Sequence evidence:

| Batch | Count | Sequence SHA-256 | Three documents identical |
| --- | ---: | --- | --- |
| A | 17 | `22a0547afaf9517d1be40b77d5d430309a07c09081742c8fcf2069c2faa37dee` | yes |
| B | 21 | `127f865640dd78405638e3bd8dd79f566e4f37c22a20646a9081a3b02a92a3d1` | yes |
| C | 20 | `99183b4b35e28059ff4e0d31a043f8ebe6f4986a9c09bee44d5094cdfdda1d83` | yes |

For all nine documents:

- current Mongo natural traversal equals ascending ObjectId order;
- current natural traversal equals ascending `row_num` order; and
- `row_num` is exactly `1..N`.

The G2 pipeline uses an unsorted Mongo `find` and iterates the returned cursor.
The evidence therefore supports content-and-order balance across models, so
the Batch C granularity comparison does not contain an observed input-order
difference. The formal runs did not persist a per-fragment call-order event
log; this is a strong reconstruction from current natural, ObjectId, and
`row_num` order rather than an independent historical event-log proof.

## Frozen formal wall-clock observations

Durations come directly from the nine accepted formal
`pipelineRuns.started_at` and `finished_at` timestamps. Values are rounded to
whole seconds in prose/tables; full precision remains in the external JSON.

| Model | Three formal observations (s) | Mean (s) | Range (s) |
| --- | --- | ---: | --- |
| `llama3.2:3b` | 174, 210, 194 | 193 | 174–210 |
| `qwen2.5:3b` | 172, 166, 156 | 165 | 156–172 |
| `Mistral-Large-3` | 65, 40, 49 | 52 | 40–65 |

These are observations, not benchmarks. A separate Llama instrumentation run
on the same 20-input Batch C document took 132 seconds, showing that
environmental/run-to-run variation is large enough to make millisecond
reporting misleading.

Required comparability statement:

> Local wall-clock includes local client and model-loading behaviour; Azure
> wall-clock includes network round trips and GlobalStandard service-side
> queuing. These timings are not like-for-like and should be compared only
> within backend.

The prototype statement that 150 fragments took approximately 19 minutes is
not a formal three-model result. It may be used only as a baseline-stage
observation with its original model and configuration identified.

## Static resource profile

| Item | Recorded value |
| --- | --- |
| Machine | Lenovo 81T0 |
| CPU | Intel Core i5-9300H; 4 physical / 8 logical cores |
| System RAM | 7.92 GiB |
| GPU | NVIDIA GeForce GTX 1650; 4096 MiB |
| `llama3.2:3b` referenced blobs | 2,019,393,189 bytes; 1.881 GiB |
| `qwen2.5:3b` referenced blobs | 1,929,912,432 bytes; 1.797 GiB |

Model manifest SHA-256 values equal the frozen Ollama digests.

## Separate memory instrumentation

Required Methods statement:

> Peak memory figures were captured in separate instrumentation runs under the
> same configuration and code state, not during the frozen generation runs.

Both accepted local measurements used a fresh restored `nie_pilot`, the same
20-input Batch C document, no preloaded Ollama model, and the frozen
temperature, seed, token, timeout, retry, prompt, and schema settings.

RAM is the observed working-set sum of the AI process, Ollama, and
`llama-server`. GPU is whole-system used memory under Windows WDDM rather than
per-process VRAM. Actual sampling cadence was approximately 0.9–1.0 seconds;
body text rounds RAM to 0.1 GiB.

| Model | Separate run (s) | Local-stack WS pre/peak | Whole-system GPU pre/peak |
| --- | ---: | ---: | ---: |
| `llama3.2:3b` | 132 | 0.6 / 3.1 GiB | 494 / 2781 MiB |
| `qwen2.5:3b` | 93 | 0.6 / 1.6 GiB | 489 / 2614 MiB |

The Llama GPU peak is approximately 68% of the installed 4096 MiB. Together
with a 3.1 GiB observed local-stack working set on a 7.92 GiB machine, this
supports the bounded statement that the model ran on consumer hardware but
with limited headroom.

The host-memory difference is not inferred from model file size alone. Ollama
runtime logs show:

- Llama offloaded 26/29 layers, retained a 484.22 MiB CUDA-host model buffer,
  and allocated a 48 MiB CPU KV buffer; and
- Qwen offloaded 37/37 layers, retained a 243.43 MiB CUDA-host model buffer,
  and reported no CPU KV buffer.

The accepted Llama attempt began with zero matching model processes and a
whole-system GPU baseline near 0.45 GiB. It was process-clean but not
reboot-cold; the OS file/page cache was not independently flushed. Its 3.1 GiB
value remains provisional until a post-reboot repeat confirms or revises it.

## Instrumentation attempt ledger

No resource attempt failed because of OOM, GPU exhaustion, provider timeout,
or a model/protocol error.

| Path/attempt | Outcome | Disposition |
| --- | --- | --- |
| `20260729_225054_llama` | setup preflight stopped before services/run because an Ollama CLI check transiently occupied 11434 | retained setup-only directory; no request or pipeline run |
| `20260729_225402_llama`, launcher attempt | Windows argument quoting failed before HTTP request | retained; no model load or `pipelineRuns` record |
| `20260729_225402_llama`, first HTTP measurement | SSE consumer treated bytes as string and crashed; isolated-copy run remained `running` | retained; invalid; never used |
| `20260729_230600_llama_attempt2` | pipeline completed, but RAM sampler omitted `llama-server`; two runner processes were subsequently found and stopped | retained; wall-clock diagnostic only; RAM rejected |
| `20260729_231409_llama_attempt3` | fresh DB/processes, zero residual model processes, completed | accepted as process-clean; Llama RAM provisional pending reboot-cold repeat |
| `20260729_231932_qwen` | fresh DB/processes, completed | accepted |

The attempt suffixes therefore express a fail-loud measurement history rather
than result selection. Invalid attempts remain preserved and are explicitly
excluded.

## Azure cost and resource observability

The "`< $10`" value is a budget ceiling, not an observed cost. The formal
`pipelineRuns` records do not contain token or billing fields. Actual Azure
cost remains open until the portal usage/cost export for the formal window is
available.

If the observed formal cost is small, RQ1 must not claim that this study
demonstrated a monetary advantage for local models. The local-case argument
must instead distinguish privacy, no external dependency, no per-call
billing, and possible scale/repeated-use economics from the observed
small-study cost.

Azure server RAM/VRAM is not exposed to the client. That is a substantive
observability asymmetry: local resource costs are measurable, whereas hosted
model compute/memory is opaque and only monetary usage is externally visible.

## Evidence hashes

All hashes are full SHA-256 values.

| Evidence | SHA-256 |
| --- | --- |
| Formal retention/timing result | `FA5DA090AEE8AB9A66AE5FFD8DE98AD298300B9C37B32BC64BEB034FBB60C5D0` |
| Formal order result | `55CE7D0ABD43C03EA302E0C12838B447ADFF831D112303BEEFAB849A4FDAA1A1` |
| Combined external evidence summary | `4EE9A5C8B2551E6C2338B4769F663B0DC4FA811630F7F6C742F04B4FD55A84EE` |
| Failed Llama state ledger | `933D68602F270456D929C2C359AFD7CE719C301F0839324F196516D8E8E86506` |
| Invalid Llama attempt2 summary | `AB9580AAB48C7CD855FB99597A1F92CF4B84E3BE4AC7BC5B2CC3607BFB0A5DFB` |
| Llama attempt2 validity correction | `17AE3E802F18C003D42A7CE8B9D4F20C0C7DC5AD63C531BF3BD6F3BD55B12FD7` |
| Accepted Llama summary | `B092966C0FFE04181FEF1E369C019105C8C5D9D56FB9D3825F38BB8DE694773C` |
| Accepted Llama samples | `D810B54BDAE5F6A5C6E0F27983F9F432CDAD750C6D1DFBD3E010E9F8A32A4547` |
| Accepted Qwen summary | `8783DEF5F2DF216311AF6662C27A4A7C6F6ACD13253AF6278E039B0F0F83BB83` |
| Accepted Qwen samples | `89737381A2707E60EBE3AD0D7117F3ACD5F35E006D07EEB7710FFC7BC60C588F` |

The ignored audit scripts were anchored at:

| Script | SHA-256 |
| --- | --- |
| `formal_retention_resource_audit.py` | `344F43334929FF6EF341915FC682A63461504AC64856D6E6DF32B65CDF0C1BBC` |
| `formal_fragment_order_audit.py` | `041B85827214991A1440C41434C37E17DD310FBCEA70FFAB23F8479A7A1A1C2D` |
| `resource_instrumentation_run.py` | `227FCD73A3BB82C6B5209D20E7414D8345F2ACFB5EEC78B7F111EE2EE949C918` |

