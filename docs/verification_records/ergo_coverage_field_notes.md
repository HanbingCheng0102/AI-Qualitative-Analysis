# ERGO coverage check: field-note recording scope

## Record status

- ERGO reference: `115447`.
- Ethics-material review window: `2026-07-30`.
- Revision recorded: `2026-08-02` (Europe/London), before the first formal
  participant session.
- Reviewer: Hanbing Cheng (researcher/project owner).
- Parent protocol-freeze commit:
  `0044d24ba8575e9e3216c177f50110d2a422d149`.
- Relationship to parent: follow-up revision in a new commit. The parent commit
  is not amended, rebased or rewritten; its timestamp remains the original
  protocol-freeze evidence.
- Reason for revision: **the recording scope was narrowed after verification of
  ethics coverage**. The analytic categories and decision rules are unchanged.

The approved ethics materials remain under the approved study/DPA storage
controls and are not duplicated into Git. This record identifies the reviewed
locations and the conservative operational decision derived from them.

## Coverage findings

| Item | Finding | Location in the reviewed ERGO materials |
| --- | --- | --- |
| Audio recording | Covered | PIS section **“Will the session be recorded?”**; consent form has a separate recording item requiring separate initials; the DPA Plan lists audio recording as personal data. |
| Think-aloud procedure | Covered | Main form, **Study Details → Procedure**, states that the participant works while thinking aloud; PIS section **“What will happen if I take part?”** states “saying out loud what you are thinking as you go”. |
| Researcher field notes | Not separately itemised | The approved data list itemises audit-trail logs, audio recordings, participant written feedback, email addresses and signed consent forms, but does not separately name researcher field notes. |

The third finding is treated conservatively. It does not assert that field
notes are prohibited; it records that they were not separately itemised in the
reviewed approved-data list and therefore must not become an independent
analytic source.

## Frozen handling after the coverage check

1. Formal-session field notes are **observational locator notes only**.
2. During P1/P2/P3 the researcher records only the audio timestamp and 3–5
   locating keywords for a potentially relevant utterance. Technical incidents
   and reflexivity may be logged separately as operational context, but they are
   not participant quotations or an independent qualitative corpus.
3. Every utterance concerning grouping structure or interface operation is
   timestamped even when ambiguous. The researcher does not decide
   `observed`/`unclear` in the room and does not omit an ambiguous utterance.
4. Exact participant wording is taken only from the approved audio transcript.
   Field notes do not supply or repair a quotation.
5. Field notes are not analysed as a separate dataset and are not cited or
   quoted in the thesis. The §2A qualitative summary is grounded in the
   transcript plus its audio timestamps.
6. These formal-session notes use only `P1`, `P2`, or `P3` and contain no name,
   email address, signature or other directly identifying information.
7. Field-note storage and destruction follow the DPA Plan and receive the same
   safeguards as the other research data.
8. Delayed coding is performed once, only after P1/P2/P3 are complete.

## Analytic invariants

This revision changes only the source of exact wording and the amount written
in the live field record. It does **not** change:

- the participant × document observation unit;
- `observed`, `no spontaneous expression recorded`, `unclear`, or the
  single-cluster merge `n/a` rule;
- the preregistered `observed` boundary;
- the no-prompt/no-clarifying-follow-up rule;
- the delayed-coding, aggregation, reporting or analysis rules;
- the uniform closing question;
- G2, the `ddb5355972ca63df44edad184b11e30f420e4c62` runtime endpoint,
  database behaviour, `formal_session_integrity.py`, the nine formal documents,
  or the three demo documents.

The change therefore causes no loss of planned analytic capability: it replaces
an approximate live quotation with the more accurate approved transcript while
keeping what is observed, how it is coded and how it is reported fixed.

## Thesis follow-up (registered, not implemented in this commit)

- Methods §§3.7.3 and 3.8: describe live capture as audio timestamp plus 3–5
  locating keywords, with exact wording sourced from the transcript.
- Methods §3.10.8: state that qualitative quotations and coding use approved
  audio transcripts; researcher observational notes are locator aids only and
  not independent analytic material.
- Preregistration disclosure: state that the recording medium was revised once
  before the first formal session after an ethics-coverage check, while the
  analytic scheme remained unchanged.
