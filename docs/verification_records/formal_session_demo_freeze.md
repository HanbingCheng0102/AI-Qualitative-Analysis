# Formal-session demo copies and final procedural freeze

## Status and scope

- Decision and execution date: `2026-08-02` (Europe/London), before the first
  formal participant session.
- Participant-facing session code endpoint remains exactly
  `ddb5355972ca63df44edad184b11e30f420e4c62`.
- This record changes no application code, prompt, schema, model, formal input,
  formal matrix or formal feedback. The repository commit is docs-only.
- The only database writes were three new, excluded demonstration documents and
  their own fragments/clusters. The nine formal whitelist documents were read
  only and hash-checked before and after.

## Fixed demo input and construction

All three copies were independently created through `POST /ingest/survey` from
the same tracked development input:

| Input | Rows | SHA-256 |
| --- | ---: | --- |
| `test-data/p1_pipeline_run_20.csv` | 20 | `9270F9DAD53D00777E822B5C26356F5EAB28A3A1CAE9E64EE6C6F50D8FADCD7A` |

The temporary ingest-only service exposed only the production ingest router,
used explicit `nie`/27017 configuration, did not load the root `.env`, removed
cloud-key variables from its child environment, did not expose an LLM route,
and reported `cloud_keys_present=false`. Port 11434 had no listener.

To avoid stochastic model differences between the three demonstrations, the
fixed two-cluster projection came from the existing non-smoke diagnostic
document `R5_OLLAMA_SAMPLING_batchA / 6a5cfca621fc0a91ba66e692` (20/20 fragments
clustered, two clusters, zero feedback). Before any projection write, each new
ingest was required to match that source fragment-by-fragment using the unique
internal tuple `(row_num, survey_question_key, redacted_text)`. No tuple values,
response text, HTML, row data or embedding were printed to logs or this record.

Cluster ObjectIds and fragment ObjectIds are necessarily different in each
copy. The verification therefore compared an ID-independent semantic form:
hashed fragment keys, cluster membership signatures, cluster-label hashes,
embedding hashes and null feedback projections. The resulting common initial
semantic SHA-256 was:

```text
b79bb50523e9dcfc64b2ef61d72d6af55a0a08a54d8d6b743b4a3c8a94b5c635
```

## Frozen mapping and initial gates

| Formal session | Demo participant | Demo survey | Demo doc ID | Fragments | Clusters | Initial feedback | pipelineRuns |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| P1 | `DEMO_P1` | `D_SESSION_DEMO_P1` | `6a6f8bd596018eb206d7ead2` | 20 | 2 | 0 | 0 |
| P2 | `DEMO_P2` | `D_SESSION_DEMO_P2` | `6a6f8bd696018eb206d7eae7` | 20 | 2 | 0 | 0 |
| P3 | `DEMO_P3` | `D_SESSION_DEMO_P3` | `6a6f8bd696018eb206d7eafc` | 20 | 2 | 0 | 0 |

All 60 demo fragments were clustered, and every initial
`feedback_cluster_id` was null. Each session must use only its paired demo
identity/document. The three identities, three demo documents and the
projection-source document are analysis exclusions. After familiarization, the
URL parameter and badge must be changed back to the formal participant before a
formal whitelist document is opened.

## Formal-document zero-change guard

The pre-write and post-write audit used canonical extended JSON, sorted by `_id`,
for the nine formal documents across `documents`, `fragments`, `clusters`,
`clusterFeedback` and `pipelineRuns`. The combined hash was identical before
and after:

```text
228204a88ccce72c1e017a0d926f675f10e5f5b9ea36c96d322fb6fed2c8b1b0
```

This is evidence that the demo setup did not change the nine formal document
records in those collections. It is not a claim about collections or documents
outside the stated scope.

## Attempt ledger

1. The first ingest-only process launch was rejected before startup because the
   Windows child environment contained duplicate case variants of `Path`; port
   8000 never listened and no ingest occurred. The environment was normalized,
   and the second launch succeeded.
2. All three ingest calls then succeeded once, each returning 20 fragments.
3. Projection attempt 1 proposed `STRICT_OK_batchA / 6a5b85c0947147db1b998d7e`
   as source. The setup guard rejected it before any projection write because
   it contained unclustered fragments.
4. Projection attempt 2 used the fixed two-cluster source above and completed.
   No failed document, cluster or feedback write was deleted or hidden.

## Private evidence anchors

The setup code and raw JSON evidence remain in ignored private storage and do
not contain participant data. Their hashes at execution were:

| Evidence | SHA-256 |
| --- | --- |
| `session_demo_setup.py` | `F4734DC482E6DD5226C659C5293957941A950C131A85FD307752CD2DD6BCF86C` |
| `demo_ingest_app.py` | `9448B73EF63D8FF76073CB2CD2324B71F95CA1E20D34D1C792FC8FBE10824A15` |
| `session_demo_formal_pre.json` | `105B1DC3C205C5040ED3F2CC255AFB562AD8D8189B21FEFF19817F2991CC8492` |
| `session_demo_materialization_attempt2.json` | `14008239EA0B53342DE94A20D3CC9FA4891584C7929AC8D12F7B926B296B2BB8` |
| `session_demo_verification.json` | `36A36B7C19FC1D9BA3608658F42CEB48407C4A7AE670E867A624F51C45164F34` |

After verification, the ingest-only service and formal MongoDB were stopped.
Ports 27017, 8000 and 11434 had no listeners. Demo feedback produced during
familiarization is expected to mutate only that participant's excluded demo
copy and is never reset, selected or analysed as formal study data.
