# Walkthrough: how to explain and demo this project

## The 30-second version
This is a seeded generator for an academic-integrity case system, plus a validator. It creates learners, submissions and
synthetic similarity reports. A high score only triggers human review, never guilt. Reviewers, evidence, decisions and appeals
are simulated as a timeline, four labelled failures are planted, and the validator finds them from the data alone. The same
seed always produces byte-identical files.

## What it is, and what it is not
- **It is** a synthetic data generator and an audit tool for the *process* around similarity flags (reviewers, evidence, decisions, appeals, history).
- **It is not** a plagiarism detector. No documents are read or compared. Similarity scores are generated numbers, and "cheating" is a hidden label the generator assigns so outcomes can be checked against a known truth.
- **There is nothing to upload.** Different seeds give different datasets for different demos.

## The 5-minute story
1. **Problem.** Similarity tools raise false alarms (quotes, shared templates, boilerplate). A fair process needs thresholds that trigger review, independent reviewers, preserved evidence, appeals and a tamper-evident history.
2. **Data model.** 10 required entities plus 3 supporting tables: `case_reviewers` (the N:M bridge), `reviewer_conflicts`, `state_events` (append-only audit trail). `src/schema.py` is the single source of truth for the SQL, the data dictionary and the validator.
3. **Rules.** Bands apply to the *adjusted* score (raw minus quoted minus template text): <25% none, 25-50% one reviewer, 50-75% two, 75%+ a three-member panel. Lower bounds are inclusive. `auto_guilt_permitted` is false everywhere.
4. **Why outcomes are not random.** Each flag gets a hidden true cause (genuine, legitimate quote, shared template, false positive). Reviewer votes, decisions and appeals follow from that cause plus stated error rates (90% / 85% accuracy). Wrongful outcomes and successful appeals emerge from the rules.
5. **Timeline.** Opened, reviewers assigned after a conflict check, evidence added, votes (tiebreak on a split), decision, 14-day appeal window, independent appeal review, closure. Events after 2026-10-31 are cut, so some cases are genuinely still open.
6. **Anomalies.** Injected *after* the clean baseline into targeted cases only: flag treated as guilt, reviewer with a conflict, evidence added after the decision with no history, appeal closed without independent review. Each is labelled in `ground_truth`.
7. **Validation.** 112 structural checks and 5 process checks. The four detectors use only the input tables, then are scored against ground truth: precision and recall 1.0 (8, 8, 8 and 6 cases).
8. **Reproducibility.** One seeded random generator, no clock reads. Two runs and the committed data have identical checksums, and a different seed differs.

## Live demo script (about 5 minutes)
```powershell
py src/generate.py --seed 20261022 --scale 1.0 --out data   # row counts appear
py src/validate.py --data data                               # 112/112 and 5/5, four detectors exact
py src/repro_check.py                                        # run1==run2==committed
py src/generate.py --seed 777 --scale 0.1 --out demo --no-docs ; py src/validate.py --data demo --out demo_docs
```
Then open `dashboard/index.html` (rebuild with `py src/build_dashboard.py --data data`):
1. **Threshold lab:** drag the slider to 25%. About 1,500 submissions look suspicious on raw score, 1,000 after exclusions, so 508 false alarms are avoided.
2. **Case explorer:** open a case, read the timeline, the reviewers' votes, the evidence and the rationale. Filter to "Audit findings only".
3. **Audit findings:** click **Reveal answer key** and show the detectors match the labels exactly. Click a case ID to jump to it.
4. SQL (optional): the conflict, late-evidence and auto-guilt queries each return 8.

## Numbers worth knowing (full run)
10,000 submissions; 1,000 flags (750 standard / 170 priority / 80 panel); 300 cases; 245 cases with multiple reviewers and 26 tiebreaks;
46 appeals: 31 upheld, 5 overturned, 4 reduced, 3 withdrawn, 3 pending (9 successful); 14 SLA breaches; 10 cases still open;
508 submissions with raw score >= 25% that were *not* flagged because exclusions applied; 117 checks in total.

## Questions to expect, with straight answers
- **Why does a high score only trigger review?** Because false positives are common and a score cannot tell a quote from copying. Review is proportionate; guilt needs human findings and evidence.
- **How do I know outcomes aren't random labels?** They derive from a hidden cause plus documented error rates. The ground truth records the expected outcome, and the data differs from it in 20 cases for stated reasons (11 real misconduct wrongly cleared, 4 penalties reduced on appeal, 3 planted auto-guilt, 2 benign overlaps wrongly sanctioned).
- **Does the generator leak the answer key?** Input tables contain no label columns; `ground_truth` is a separate file that generation never reads. One honest caveat: `top_source_type = internal_template` correlates with the shared-template cause, as a real feature would.
- **Why those probabilities (90%, 85%, 80%, 22%, 92%)?** They are modelling assumptions I chose to produce a plausible mix, including wrongful outcomes and successful appeals. They are not measured institutional statistics, and they are all in `src/rules.py`.
- **Why is the case count exactly 300?** The brief asks for it, so I pin it: all priority/panel flags (250) plus 50 triage referrals. Letting it emerge from triage behaviour would be more realistic. This is a known simplification.
- **How do you prove no history is overwritten?** Decisions are append-only (an appeal adds a second decision that supersedes the first), and every state change has a `state_events` row. The validator checks that creation, filing and decision events exist and match record timestamps.
- **What would break the validator?** A fifth, unplanned anomaly type. The detectors know the four planted patterns. That is a limitation.
- **How is reproducibility enforced?** One `random.Random(seed)`, deterministic iteration, explicit LF line endings, no clock reads, checksums of every file.
- **Why Python standard library only?** The FAQ prefers free, local and light. It also means anyone can run it with no install.
- **Why not MySQL or a web app?** The brief asks for generated data, not an application. SQLite loads with no server. The dashboard is a bonus view of the same data.
- **Which parts did the AI write?** Be direct: most of the code was written by Claude (see `docs/AI_USE.md`). What matters is that you can explain each module and have run and tested it yourself.

## Honest limitations
- Fully synthetic, with assumed rates. No real text matching.
- Case count pinned; detectors specific to four planted patterns.
- Conflict declaration dates are not yet applied to earlier assignments; weekends and holidays are ignored in timestamps.
- No automated unit tests (not required by the FAQ); verification is the validator, reproducibility check and negative tests.

## What I would do next
Apply conflict effective dates, let case volume emerge from triage behaviour, add a fifth anomaly type to test the detectors,
add `acceptable_outcomes` to ground truth for proportionality, add business-calendar timestamps and a small unit-test suite.
