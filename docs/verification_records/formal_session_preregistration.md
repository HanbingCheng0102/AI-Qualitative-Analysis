# Formal-session integrity and construct preregistration

## Record status

- Decision date: `2026-07-30` (Europe/London)
- Preregistration point: before the first formal participant session
- Session code endpoint:
  `ddb5355972ca63df44edad184b11e30f420e4c62`
- Parent documentation commit:
  `7d4e403c60183f75bafc1b5951aa9886f481c8de`
- Scope: procedural and analytic rules only; no session code, database, prompt,
  schema, formal input, matrix, or participant data change

The commit containing this file is the timestamped preregistration evidence.
It supplements the operational S/audit chain without moving the frozen session
code endpoint. If a formal session has already started when a future rule is
added, that rule must be labelled post hoc rather than preregistered.

## §4 Fixed order and time boundary

The three-document review segment has one 45-minute hard limit, beginning when
the first assigned document is loaded and the researcher releases the
participant to start. Consent, recording setup, and post-session checks are
outside this review timer.

Document order is the participant-specific task1 → task2 → task3 order already
fixed in the Latin-square matrix. It is not randomized again within a session
and is not changed in response to granularity, completion, or participant
behaviour. The researcher records timezone-qualified ISO 8601 start and end
timestamps for the review segment and separately for each document.

At 45 minutes the researcher stops immediately, even if the current fragment or
document is unfinished. There is no extension, speed-up instruction, or
post-session completion. Eligible fragments without a valid action remain
`no recorded decision (reject-or-unreviewed)`.

## §5.2 Failure handling and consistency checks

### Authoritative records and integrity figure

The unedited browser export from `nieFeedbackProvenanceErrors` is authoritative
for whether the browser observed a feedback-submission failure. MongoDB is
authoritative for which actions were successfully persisted. Neither record is
used to erase or substitute for the other.

For each formal session, `N` is the raw number of error-log entries whose
participant matches the formal participant, whose `doc_id` belongs to that
participant's three approved whitelist documents, and whose action is
`confirm` or `move`. `N` is reported as an integrity figure per participant and
in aggregate. It is not deduplicated or reduced based on HTTP status or later
database state.

- `N=0` means only that no feedback-submission failure was observed by the
  browser log; it is not proof that no unobserved fault existed.
- `N>0` triggers evidence preservation and entry-by-entry reconciliation
  against MongoDB, timestamps, and field notes. A failed action is never
  silently retried, deleted, or recoded as successful. Only valid persisted
  actions enter confirm/move numerators. If no other valid action exists for the
  fragment, its final category remains `no recorded decision`.
- The report includes `N`, failure types, affected documents/fragments, and the
  adjudication. Failure of any applicable consistency check below quarantines
  that participant-document from quantitative analysis pending a separate
  decision. The database is not repaired to manufacture a PASS.

### Six preregistered consistency checks

Each participant-document receives a saved PASS/FAIL/NA result for:

1. **Whitelist/run identity:** exact approved doc and completed G2 run, with
   matching run ID, model, batch, code version, and frozen params.
2. **Participant and eligible scope:** exact formal participant and assigned
   document; every feedback fragment is in that document's eligible set; no
   filtered, PILOT, TEST, or development records enter.
3. **Action/reference integrity:** quantitative actions are only
   `confirm`/`move`; referenced document, fragment, and from/to clusters exist
   in the same document; move source and destination differ.
4. **Latest-state partition:** after `{timestamp:-1,_id:-1}` adjudication,
   `confirm + move + no recorded decision = eligible`; the buckets are
   mutually exclusive and event count is not below the number of distinct
   reviewed fragments.
5. **Move-chain continuity:** applies only to fragments with at least one valid
   move. In ascending `{timestamp:1,_id:1}` order, the first move's
   `from_cluster_id` is the pre-participant assignment and every later move's
   from equals the preceding move's to. Confirm-only and unreviewed fragments
   are `NA`, not FAIL.
6. **Post-move projection:** applies only to moved fragments and their affected
   clusters. Current `cluster_id`/`feedback_cluster_id`, the final move
   destination, and cluster membership agree, and the fragment has exactly one
   current cluster membership. Unmoved fragments/clusters are outside this
   check; the check is not evidence that the entire database or model output
   was validated.

Checks 5 and 6 specifically test the event chain and recluster projection. Their
move-only scope is fixed in advance and cannot be broadened or narrowed after
seeing participant results.

## §12 Coding-versus-clustering construct boundary

The evaluated construct is **first-pass clustering assistance**. The model
provides candidate fragment groupings and placements for participant review.
The study does not treat this as complete qualitative coding, theme development,
theme interpretation, or reflexive thematic analysis.

`confirm` means that the participant explicitly accepts the fragment's current
cluster placement at that moment. It does not mean acceptance of the model as a
whole, the cluster label, a theme interpretation, the relevance decision, or
complete coding accuracy. `move` is an explicit correction into another
existing cluster; it does not express split, merge, or creation of a new
code/theme. Absence of a valid action remains
`no recorded decision (reject-or-unreviewed)`.

Consequently, the quantitative outputs are confirmation coverage/a lower bound
on placement endorsement and an explicit-correction rate. They must not be
reported as a complete acceptance rate, coding quality, thematic validity, or
model accuracy. Think-aloud observations about split, merge, and navigation
remain physically and analytically separate qualitative context.
