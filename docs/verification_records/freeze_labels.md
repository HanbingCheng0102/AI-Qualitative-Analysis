# FREEZE_LABELS Verification Record

## Record Metadata

- Verification date: 2026-07-19
- Feature commit: `fd495424dbce22b0681c94dd2ab2f20366c68221`
- Backend/model: `ollama` / `llama3.2:3b`
- Test participant: `VERIFY_REL_2` (registered exclusion identity)
- Test document: `6a58d2cd1d6d1e80c35ba564` (`P1_task2_batchB`, not in the formal doc whitelist)
- Result: passed

Clean worktree output recorded before the original manual verification:

```text
## provenance-extension...origin/provenance-extension [ahead 3]
```

Runtime configuration rechecked after verification without exposing secrets:

```text
llm_backend=ollama
llm_strict_mode=true
freeze_labels=true
model_name=llama3.2:3b
openai_key_present=false
anthropic_key_present=false
```

## Automated Verification

Command:

```powershell
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Relevant results and summary:

```text
test_cluster_run_is_locked_before_database_access ... ok
test_label_clusters_is_locked_before_database_access ... ok
test_llm_cluster_run_remains_available_when_labels_are_frozen ... ok
test_save_manual_clusters_is_locked_before_database_access ... ok
test_freeze_only_changes_labels_and_response_metadata ... ok
test_frozen_recluster_moves_and_records_without_labelling ... ok
test_unfrozen_recluster_retains_runtime_labelling ... ok
test_freeze_boolean_typo_is_rejected ... ok

Ran 28 tests in 0.026s
OK
```

The mode-consistency test uses identical IDs and inputs in both modes. It
compares the complete `clusterFeedback` record after normalising only the UTC
timestamp value, the complete fragment update, and all membership and centroid
updates. The only permitted differences are the response's `labels_frozen`
value and two `label`/`summary` writes when freeze is false.

## Offline Recluster Verification

For the original browser test, the operator loaded Cluster Graph, stopped
Ollama, confirmed `TcpTestSucceeded : False`, and then moved a card. The card
moved successfully and did not bounce back. The response was:

```text
POST /feedback/recluster
HTTP 200
{"ok":true,"labels_frozen":true}
```

The response was recaptured from the same endpoint after the original offline
test. A second controlled development move was recorded to preserve complete
before/after MongoDB evidence.

Before the controlled move:

```text
source cluster 6a58d3831d6d1e80c35ba57a
  label: NHS Staff Communication
  summary: Patients praised staff for clear explanations
  fragment_ids: [6a58d2cd1d6d1e80c35ba565,
                 6a58d2cd1d6d1e80c35ba566,
                 6a58d2cd1d6d1e80c35ba569]

target cluster 6a58d3831d6d1e80c35ba57b
  label: Staff Respect
  summary: Patient felt respected and cared for.
  fragment_ids: [6a58d2cd1d6d1e80c35ba567,
                 6a58d2cd1d6d1e80c35ba56b]

fragment 6a58d2cd1d6d1e80c35ba565
  cluster_id: 6a58d3831d6d1e80c35ba57a

VERIFY_REL_2 feedback_count: 3
```

After the controlled move:

```text
source cluster 6a58d3831d6d1e80c35ba57a
  label: NHS Staff Communication
  summary: Patients praised staff for clear explanations
  fragment_ids: [6a58d2cd1d6d1e80c35ba566,
                 6a58d2cd1d6d1e80c35ba569]

target cluster 6a58d3831d6d1e80c35ba57b
  label: Staff Respect
  summary: Patient felt respected and cared for.
  fragment_ids: [6a58d2cd1d6d1e80c35ba567,
                 6a58d2cd1d6d1e80c35ba56b,
                 6a58d2cd1d6d1e80c35ba565]

fragment 6a58d2cd1d6d1e80c35ba565
  cluster_id:          6a58d3831d6d1e80c35ba57b
  feedback_cluster_id: 6a58d3831d6d1e80c35ba57b

VERIFY_REL_2 feedback_count: 4
latest feedback:
  action: move
  from_cluster_id: 6a58d3831d6d1e80c35ba57a
  to_cluster_id:   6a58d3831d6d1e80c35ba57b
  timestamp: 2026-07-19T12:56:29.003Z
```

The source and target `label` and `summary` values are byte-for-byte identical
before and after. Placement, provenance, and both membership lists changed as
expected.

## Frozen Mutation Endpoints

Raw responses captured with `FREEZE_LABELS=true`:

```text
POST /cluster/run
HTTP 423
{"detail":{"error":"labels_frozen","operation":"cluster_run","message":"Cluster labels are frozen for experiment sessions."}}

POST /label/clusters
HTTP 423
{"detail":{"error":"labels_frozen","operation":"label_clusters","message":"Cluster labels are frozen for experiment sessions."}}

POST /suggest/save
HTTP 423
{"detail":{"error":"labels_frozen","operation":"save_manual_clusters","message":"Cluster labels are frozen for experiment sessions."}}
```

The guard tests assert that each route rejects before `get_db()` is called. The
operator also compared the MongoDB label snapshot after all three requests:

```text
labelSnapshot() === labelsAfter
true
```

## Strict/Freeze Orthogonality

With both switches still true and without restarting AI service,
`FREEZE_ORTHOGONAL_batchA` completed through `/llm-cluster/run`:

```text
doc_id:       ObjectId("6a5cc5999b3bd3f7ab893d09")
pipeline:     llm_semantic
llm_backend:  ollama
model_name:   llama3.2:3b
batch_label:  A
started_at:   2026-07-19T12:39:56.885Z
status:       completed
strict_mode:  true
code_version: fd495424dbce22b0681c94dd2ab2f20366c68221
finished_at:  2026-07-19T12:40:12.194Z
cluster_count: 1
```

## Verdict

`FREEZE_LABELS=true` preserves review-time placement and provenance behaviour,
prevents runtime label changes, fails loudly on the three projection-rewriting
routes, and does not block strict LLM Semantic generation of a new document.
