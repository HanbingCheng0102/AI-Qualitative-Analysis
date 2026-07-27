# Session card readability instrument v1

Status: candidate; not approved for a formal participant session

Date: 2026-07-27

## Version boundary and rollback

- Frozen generation instrument: `generation-frozen-G2`
- Generation commit: `544540beedb707c2be5c08fa1647107f80587c84`
- Operational S audit/rollback anchor:
  `ddb5355972ca63df44edad184b11e30f420e4c62`
- Candidate branch: `codex/session-card-readability-v1`
- The candidate is an isolated session-interface change. It does not move or
  replace G2, Operational S, or the audit commit.
- To abandon the candidate without rewriting history, switch back to
  `provenance-extension`, or inspect the exact prior instrument with:

  ```powershell
  git switch --detach ddb5355972ca63df44edad184b11e30f420e4c62
  ```

Do not use `reset`, force-push, or move an existing tag to perform the rollback.

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
   and keyboard behavior are exercised;
3. the post-PILOT dry-run confirms the recorded participant actions still match
   the observer's manual counts;
4. the resulting candidate commit is explicitly approved as the new session
   instrument endpoint; and
5. the applicable FEC/ERGO approval permits formal recruitment and recording.

If the fresh PILOT exposes another error, stop using this candidate and return
to the audit/rollback anchor above. Do not repair it during a participant
session.
