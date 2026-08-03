# Formal-session offline checklist

Use one copy per participant. Record an absolute time and initials for every
gate. Do not rely on memory or a moving branch name.

## Before participant arrival

- [ ] ERGO/FEC portal status displays `Approved`; observation time/initials: __________
- [ ] PIS/consent/recording procedure matches the approved materials.
- [ ] Repository detached at `0e37f187d95db5f10cb6892cc2a97b543a5bd4eb`.
- [ ] `git status --short` has no output.
- [ ] `ddb53559…`→session endpoint has no `api-server`/`ai-service` diff;
      operational→audit has no non-doc diff; G2 prompt hash test passes.
- [ ] Azure/cloud keys removed from the session environment.
- [ ] Ollama stopped; port 11434 has no listener.
- [ ] `OLLAMA_MODEL=llama3.2:3b` is present only as a no-fallback guard; no model
      call is made during the session.
- [ ] Formal MongoDB is `nie` on 127.0.0.1:27017; 27018 has no listener.
- [ ] Browser failure log from the previous session exported, then cleared.
- [ ] Recording device tested; storage/retention follows approved materials.
- [ ] Silent external `45:00` countdown is ready, visible only to researcher.
- [ ] Correct participant field record is present; three doc IDs checked against
      the whitelist, with checker/time recorded.

## Immediately before the timed task

- [ ] Consent completed before any recording.
- [ ] Approximately 10 seconds of test audio recorded, stopped, played back and
      confirmed intelligible; main recording then started.
- [ ] Familiarization used the exact participant-specific pair below, with two
      initial clusters and no formal whitelist document opened:

      | Session | Demo participant/badge | Demo doc ID |
      | --- | --- | --- |
      | P1 | `DEMO_P1` | `6a6f8bd596018eb206d7ead2` |
      | P2 | `DEMO_P2` | `6a6f8bd696018eb206d7eae7` |
      | P3 | `DEMO_P3` | `6a6f8bd696018eb206d7eafc` |

- [ ] After familiarization, URL uses exact uppercase formal participant
      `P1` / `P2` / `P3` and badge displays that same formal participant.
- [ ] Fixed six-point briefing delivered verbatim, including the AI-suggestions
      sentence.
- [ ] Correct first formal document loaded by exact doc ID.
- [ ] Recording started only after consent.
- [ ] Overall and first-document start times recorded with timezone.

## During and at the end

- [ ] Each document start/end recorded; order unchanged.
- [ ] At each document transition, recording indicator visually confirmed active.
- [ ] Stage-1 participant-speech notes contain only an audio timestamp and
      3–5 locating keywords; no approximate quotation or live qualitative code.
- [ ] Every utterance about grouping structure or interface operation was
      timestamped with locating keywords even if ambiguous; none was filtered
      out in the moment. Exact wording will come only from the transcript.
- [ ] At 45 minutes, stopped immediately, or recorded that all three completed first.
- [ ] Asked exactly once: “整体感受如何？”; no follow-up/comparison question.
- [ ] Recording stopped and stored under the approved plan.
- [ ] Browser failure log exported unedited; raw integrity count `N` recorded.
- [ ] React/API/AI stopped; only then detached to integrity-tool commit
      `5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e` with a clean worktree.
- [ ] `git diff --exit-code 0e37f187d95db5f10cb6892cc2a97b543a5bd4eb..5eec829db35c8c2ecf370ed444c2c8b3e2f82e6e -- . ':(exclude)docs'`
      produced no output; no participant-facing service was started from the tool commit.
- [ ] Six-check script run once; `N` and all metrics generated in the same output.
- [ ] For P1, Check 2 reported exactly the three pre-registered historical
      feedback IDs and an empty `out_of_assignment_doc_ids`; no document-wide
      exemption was used.
- [ ] Output and raw evidence preserved; no database repair or silent retry.

## Post-check continuation decision

- [ ] `N>0` alone was treated as an integrity result: preserve/reconcile/report,
      not as an automatic stop before the next participant.
- [ ] Checker malfunction, missing trustworthy output or non-zero exit caused a
      stop pending investigation.
- [ ] Database/participant/doc/run mismatch caused a stop and quarantine of the
      affected participant-document; nothing was deleted or repaired.
- [ ] Unexpected `NA` caused a scope check. Only Check 5 was allowed to be `NA`
      where the document had no move; all-eligible Check 6 returned PASS or FAIL.
- [ ] `overall_status` was not combined with `N=0` as a joint continuation gate.
- [ ] Before the next participant, detached back to session endpoint
      `0e37f187d95db5f10cb6892cc2a97b543a5bd4eb` and repeated the pre-session gates.
