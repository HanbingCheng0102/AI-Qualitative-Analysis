# Session card readability instrument v1

Status: release gate passed; approved before the first formal participant session

Date: 2026-07-27

## Version boundary and rollback

- Frozen generation instrument: `generation-frozen-G2`
- Generation commit: `544540beedb707c2be5c08fa1647107f80587c84`
- Operational S audit/rollback anchor:
  `ddb5355972ca63df44edad184b11e30f420e4c62`
- Fixed-card inspection checkpoint:
  `c5b7354fb4df23e60382f4858922adac516f81f9`
- Candidate branch: `codex/session-card-readability-v1`
- The candidate is an isolated session-interface change. It does not move or
  replace G2, Operational S, or the audit commit.
- To abandon the candidate without rewriting history, switch back to
  `provenance-extension`, or inspect the exact prior instrument with:

  ```powershell
  git switch --detach ddb5355972ca63df44edad184b11e30f420e4c62
  ```

Do not use `reset`, force-push, or move an existing tag to perform the rollback.
If only the URL-persistence addition needs to be removed, the fixed-card
checkpoint above remains an exact intermediate rollback point.

## Pilot observation and intended change

During the isolated P2 rehearsal, fixed-size response cards frequently required
expansion or repositioning before their full text could be read. This added
navigation effort and could reduce the number of responses reviewed in a
time-limited session.

The candidate keeps response-card geometry fixed while providing a separate
full-text inspection layer:

- response cards use a fixed `240 x 132` layout;
- the in-card preview is clamped to four lines;
- hovering or keyboard-focusing a card shows its full text;
- `Enter`, `Space`, or the `Full text` control pins/unpins the full-text view;
- the pinned view is independently scrollable and can be closed;
- the note editor is a popover and does not resize the card;
- dragging remains available from the card body.
- the selected document ID is stored in the `docId` URL query parameter;
  refresh, browser back/forward, and copied links retain the selection while
  preserving the explicit participant query parameter.

The presentation-only inspection state is held in React memory. It does not add
or alter an API request, database write, participant action, or analysis field.

## Scope

Changed:

- `react-client/src/views/ClusterGraphView.jsx`

Unchanged:

- `api-server`;
- `ai-service`;
- generation prompts, schemas, parameters, models, manifests, and formal
  documents;
- confirm and move API call sites and their interaction-order provenance;
- MongoDB contents and the formal analysis whitelist.

## Verification

The following checks were run from this candidate branch:

- `git diff --check`: passed.
- React production build: passed with Vite `5.4.21` and 2,480 modules
  transformed; the existing chunk-size warning remained.
- Runtime route smoke:
  `/cluster-graph?participant=UI_TEST` returned HTTP 200 from a temporary Vite
  process on port 5174; the exact process was then stopped and the port was
  confirmed closed. No database or backend service was used.
- Static feedback-call comparison against the audit anchor:
  `pipeline_logFeedback` remained 2 call sites and
  `pipeline_recordFeedback` remained 2 call sites.
- Target-file lint, with the file's existing `react/prop-types` and `no-empty`
  legacy categories excluded: baseline and candidate both produced 0 errors
  and the same 5 warnings.
- Full `ai-service` suite: 83 tests passed; 3 live provider probes skipped as
  designed.
- G2 prompt-freeze test: 1 test passed.

Repository-wide React lint is not a clean gate at the audit anchor. It reports
pre-existing legacy debt. The candidate introduces no new non-`prop-types`
target-file lint finding; the new callback/detail props are the only additional
findings in the existing untyped component pattern.

## Release gate

This candidate must not be used in a formal participant session until:

1. the interface is re-tested using a fresh isolated `nie_pilot` environment;
2. fixed-card dragging, confirm, move, note, hover/focus inspection, pin/close,
   keyboard behavior, and document persistence after refresh are exercised;
3. the post-PILOT dry-run confirms the recorded participant actions still match
   the observer's manual counts;
4. the resulting candidate commit is explicitly approved as the new session
   instrument endpoint; and
5. the applicable FEC/ERGO approval permits formal recruitment and recording.

If the fresh PILOT exposes another error, stop using this candidate and return
to the audit/rollback anchor above. Do not repair it during a participant
session.

## Release-gate closure (2026-08-02)

The researcher explicitly selected this UI before the first formal participant
action. The old `ddb5355972ca63df44edad184b11e30f420e4c62` session endpoint was
started for preflight, then stopped when the version mismatch was noticed. No
demo or formal feedback was written: `DEMO_P1` had zero feedback on its demo
document and `P1` had zero feedback on all three formal P1 documents.

The latest protocol line and the two preserved UI commits were joined without
rewriting either history:

- protocol parent: `8ed3aa17551611388a3b5d5074eb4d9c032ab2b0`;
- UI parent: `2f496942e78b2f43b909fbfe98b4c730e5c86644`;
- integration merge: `68c93006d408b6cf9d01c459d86757563f65b052`.

The participant runtime is the session UI operational commit containing this
release closure. Its full hash is recorded by the unique following audit child:

```text
0e37f187d95db5f10cb6892cc2a97b543a5bd4eb
```

### Static and test gates

- `git diff --check`: passed.
- React production build: Vite `5.4.21`, 2,480 modules transformed; passed with
  the unchanged large-chunk warning.
- Target-file lint: 0 errors and the same 5 hook warnings already recorded for
  the candidate.
- Full AI suite: 83 tests passed; 3 live probes skipped as designed.
- G2 prompt hash: 1 test passed.
- `api-server` and `ai-service` are byte-diff unchanged from the historical S
  audit endpoint.

### Fresh isolated database copy

Evidence root (outside the repository):
`D:\6003\session_ui_validation\20260802_233721`.

- Database Tools `100.17.0` and the previously verified isolation scripts were
  reused by exact path; no restricted text or key was printed.
- The copy held formal `nie` at `lockCount 0 -> 1 -> 0`, produced SOURCE_PRE and
  SOURCE_POST dumps, and restored 1,661 documents with zero restore failures to
  a fresh `127.0.0.1:27018/nie_pilot`.
- The outer caller initially reported failure because it inspected the
  expected non-zero `$LASTEXITCODE` left by the unlocked-state probe after the
  copy script itself completed. The copy was not retried. Independent semantic
  and BSON checks all passed.
- Copy comparison SHA-256:
  `4D1D3970C7FB880483DA47078513373C7B04A4081919A6B42C1F29EAF710314B`.
- SOURCE_PRE manifest SHA-256:
  `10198213859E63FBBAB7C12B01FCF6791E52BE589E222D323050EB1806EBE242`.
- SOURCE_POST manifest SHA-256:
  `CBEB21CFB8239BC7018E2DC2EA265D8A0BFE7492FE8D1D8CD27EFE20980D3150`.
- Pilot baseline manifest SHA-256:
  `DBDE0AD542DB7C6CC49672BA6F1FA319470CCCF7F4EC6425A5E1DE146F05CCF3`.

### Runtime and interaction gate

The runtime was locked to integration commit `68c93006...`, formal port 27017
and Ollama port 11434 were closed, and API/AI connections were observed as
`nie-ui-pilot-api` and `nie-ui-pilot-ai` on `nie_pilot`.

Two watchdog starts failed closed because the first two Vite launches bound
only to IPv6 `[::1]:5173`, while the approved watchdog intentionally inspects
IPv4 TCP listeners. Each failure stopped only its recorded React/API/AI PIDs.
The third launch bound Vite explicitly to `127.0.0.1`; watchdog attempt 3 then
remained active for the complete interaction gate. No participant action was
written during the failed starts.

Using participant `DEMO_P1` and the excluded two-cluster demo document
`6a6f8bd596018eb206d7ead2`, the researcher verified:

- fixed `240 x 132` cards;
- zero-click hover full text;
- pin, scroll and close;
- keyboard focus plus Enter/Space control;
- note popover without card resize;
- one confirm and one cross-cluster move;
- participant and `docId` persistence after refresh and in a copied URL.

The browser provenance error value was raw `null`. MongoDB contained exactly
one `confirm`, one `move`, and one saved verification note. The move had distinct
and non-null `from_cluster_id`/`to_cluster_id`; its current fragment projection
and cluster membership agreed. Only `clusterFeedback`, `clusters`, and
`fragments` changed, exactly as expected. Pilot-post manifest SHA-256:
`AACF64406ECD093B454222B882361736F952632692515B35BA783D9AA63ABA5C`.
The redacted validation summary SHA-256 is
`F3EF50D201A5DABF487AAA81215325E94859CC02098767D4F8E3B8070CC6FA9F`.

The versioned `formal_session_integrity.py` correctly rejected `DEMO_P1`
because its preregistered pilot mode accepts only the historical `PILOT`
participant. The tool was not changed and the participant was not relabelled;
the equivalent scoped checks above were executed read-only and this limitation
is explicit.

### Formal-source postcondition

After the isolated stack was stopped and the pilot database was dumped, formal
MongoDB was restarted from its original dbpath. The full semantic audit before
and after validation was byte-identical, with SHA-256
`5DBA16EB3E813E7B3E5FFFFB93D28EE31147B6EB2E10E77513D937A901BB52A8`.
The nine-document combined snapshot remained
`228204a88ccce72c1e017a0d926f675f10e5f5b9ea36c96d322fb6fed2c8b1b0`.
Formal P1 feedback and DEMO_P1 feedback on all three P1 whitelist documents
both remained zero.

The release gate is therefore closed. Any participant-facing change after this
operational freeze requires a new instrument decision and a new isolated
validation; P1, P2 and P3 must use one unchanged operational commit.

## Operational-commit audit

The operational session instrument is exactly:

```text
0e37f187d95db5f10cb6892cc2a97b543a5bd4eb
```

Its direct parent is integration merge
`68c93006d408b6cf9d01c459d86757563f65b052`; its commit message is
`docs: freeze formal session UI v1 protocol`. The operational commit contains
the complete participant-facing code and protocol. This audit child changes
only `docs/` credentials and does not change the runtime.

The pre-audit commands produced:

```text
git diff --check
<no output; exit 0>

git diff --exit-code 68c93006d408b6cf9d01c459d86757563f65b052 -- . ':(exclude)docs'
<no output; exit 0>

git diff --exit-code ddb5355972ca63df44edad184b11e30f420e4c62..68c93006d408b6cf9d01c459d86757563f65b052 -- api-server ai-service
<no output; exit 0>

python -m unittest tests.test_llm_provider.PromptFreezeTests.test_current_prompts_match_g2_byte_hashes -v
Ran 1 test in 0.002s
OK
```

The audit commit is identified by its fixed message
`docs: audit formal session UI v1`, direct parent equal to the operational hash
above, and the pushed branch state. It is not the participant runtime endpoint;
formal P1/P2/P3 sessions detach to the operational hash above.
