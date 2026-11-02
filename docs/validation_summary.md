# Validation summary

- Structural checks (A): **112/112 passed**
- Process checks (B): **5/5 passed**

## Anomaly detectors vs ground truth

| issue_type | labelled | detected | precision | recall |
|---|---|---|---|---|
| flag_auto_guilt | 8 | 8 | 1.0 | 1.0 |
| reviewer_conflict | 8 | 8 | 1.0 | 1.0 |
| evidence_added_after_decision_no_history | 8 | 8 | 1.0 | 1.0 |
| appeal_closed_without_independent_review | 6 | 6 | 1.0 | 1.0 |

## Distributions

```json
{
  "submissions": 10000,
  "current_reports": 10000,
  "flags": 1000,
  "cases": 300,
  "flag_rate": 0.1,
  "flags_by_action": {
    "standard_review": 750,
    "priority_review": 170,
    "panel_escalation": 80
  },
  "boundary_scores": {
    "at_0_25": 27,
    "at_0_50": 6,
    "at_0_75": 1,
    "just_below_0_25": 220
  },
  "raw_high_but_not_flagged": 508,
  "case_status": {
    "closed": 290,
    "decided": 6,
    "appealed": 2,
    "appeal_under_review": 1,
    "under_review": 1
  },
  "case_final_outcome": {
    "minor_violation_warning": 129,
    "false_positive_dismissed": 50,
    "permitted_shared_template": 8,
    "permitted_quotation": 43,
    "major_violation_penalty": 58,
    "no_violation_insufficient_evidence": 11,
    "undecided": 1
  },
  "cases_with_multiple_reviewers": 245,
  "cases_with_tiebreak": 26,
  "appeals": {
    "upheld": 31,
    "reduced": 4,
    "overturned": 5,
    "withdrawn": 3,
    "pending": 3
  },
  "successful_appeals": 9,
  "sla_breached_cases": 14,
  "latent_class_of_flags": {
    "legit_quote": 206,
    "false_positive": 429,
    "shared_template": 109,
    "genuine": 256
  },
  "cases_whose_final_outcome_differs_from_expected": 20
}
```

## All checks

| Group | Check | Examined | Failures |
|---|---|---|---|
| A | reviewers: types parse | 38 | 0 ✅ |
| A | reviewers: required fields present | 38 | 0 ✅ |
| A | reviewers: enum values allowed | 38 | 0 ✅ |
| A | reviewers: ID pattern | 38 | 0 ✅ |
| A | reviewers: primary key unique | 38 | 0 ✅ |
| A | reviewers.email: unique | 38 | 0 ✅ |
| A | learners: types parse | 2500 | 0 ✅ |
| A | learners: required fields present | 2500 | 0 ✅ |
| A | learners: enum values allowed | 2500 | 0 ✅ |
| A | learners: ID pattern | 2500 | 0 ✅ |
| A | learners: primary key unique | 2500 | 0 ✅ |
| A | learners.email: unique | 2500 | 0 ✅ |
| A | reviewer_conflicts: types parse | 207 | 0 ✅ |
| A | reviewer_conflicts: required fields present | 207 | 0 ✅ |
| A | reviewer_conflicts: enum values allowed | 207 | 0 ✅ |
| A | reviewer_conflicts: ID pattern | 207 | 0 ✅ |
| A | reviewer_conflicts: primary key unique | 207 | 0 ✅ |
| A | reviewer_conflicts: unique ['reviewer_id', 'learner_id'] | 207 | 0 ✅ |
| A | assessments: types parse | 160 | 0 ✅ |
| A | assessments: required fields present | 160 | 0 ✅ |
| A | assessments: enum values allowed | 160 | 0 ✅ |
| A | assessments: ID pattern | 160 | 0 ✅ |
| A | assessments: primary key unique | 160 | 0 ✅ |
| A | integrity_rules: types parse | 9 | 0 ✅ |
| A | integrity_rules: required fields present | 9 | 0 ✅ |
| A | integrity_rules: enum values allowed | 9 | 0 ✅ |
| A | integrity_rules: ID pattern | 9 | 0 ✅ |
| A | integrity_rules: primary key unique | 9 | 0 ✅ |
| A | submissions: types parse | 10000 | 0 ✅ |
| A | submissions: required fields present | 10000 | 0 ✅ |
| A | submissions: enum values allowed | 10000 | 0 ✅ |
| A | submissions: ID pattern | 10000 | 0 ✅ |
| A | submissions: primary key unique | 10000 | 0 ✅ |
| A | submissions: unique ['learner_id', 'assessment_id'] | 10000 | 0 ✅ |
| A | similarity_reports: types parse | 10173 | 0 ✅ |
| A | similarity_reports: required fields present | 10173 | 0 ✅ |
| A | similarity_reports: enum values allowed | 10173 | 0 ✅ |
| A | similarity_reports: ID pattern | 10173 | 0 ✅ |
| A | similarity_reports: primary key unique | 10173 | 0 ✅ |
| A | similarity_reports: unique ['submission_id', 'report_version'] | 10173 | 0 ✅ |
| A | cases: types parse | 300 | 0 ✅ |
| A | cases: required fields present | 300 | 0 ✅ |
| A | cases: enum values allowed | 300 | 0 ✅ |
| A | cases: ID pattern | 300 | 0 ✅ |
| A | cases: primary key unique | 300 | 0 ✅ |
| A | cases.similarity_id: unique | 300 | 0 ✅ |
| A | case_reviewers: types parse | 641 | 0 ✅ |
| A | case_reviewers: required fields present | 641 | 0 ✅ |
| A | case_reviewers: enum values allowed | 641 | 0 ✅ |
| A | case_reviewers: ID pattern | 641 | 0 ✅ |
| A | case_reviewers: primary key unique | 641 | 0 ✅ |
| A | case_reviewers: unique ['case_id', 'reviewer_id'] | 641 | 0 ✅ |
| A | evidence_items: types parse | 1032 | 0 ✅ |
| A | evidence_items: required fields present | 1032 | 0 ✅ |
| A | evidence_items: enum values allowed | 1032 | 0 ✅ |
| A | evidence_items: ID pattern | 1032 | 0 ✅ |
| A | evidence_items: primary key unique | 1032 | 0 ✅ |
| A | decisions: types parse | 308 | 0 ✅ |
| A | decisions: required fields present | 308 | 0 ✅ |
| A | decisions: enum values allowed | 308 | 0 ✅ |
| A | decisions: ID pattern | 308 | 0 ✅ |
| A | decisions: primary key unique | 308 | 0 ✅ |
| A | appeals: types parse | 46 | 0 ✅ |
| A | appeals: required fields present | 46 | 0 ✅ |
| A | appeals: enum values allowed | 46 | 0 ✅ |
| A | appeals: ID pattern | 46 | 0 ✅ |
| A | appeals: primary key unique | 46 | 0 ✅ |
| A | appeals.case_id: unique | 46 | 0 ✅ |
| A | state_events: types parse | 14883 | 0 ✅ |
| A | state_events: required fields present | 14883 | 0 ✅ |
| A | state_events: enum values allowed | 14883 | 0 ✅ |
| A | state_events: ID pattern | 14883 | 0 ✅ |
| A | state_events: primary key unique | 14883 | 0 ✅ |
| A | FK reviewer_conflicts.reviewer_id -> reviewers.reviewer_id | 207 | 0 ✅ |
| A | FK reviewer_conflicts.learner_id -> learners.learner_id | 207 | 0 ✅ |
| A | FK assessments.instructor_id -> reviewers.reviewer_id | 160 | 0 ✅ |
| A | FK integrity_rules.created_by -> reviewers.reviewer_id | 9 | 0 ✅ |
| A | FK submissions.learner_id -> learners.learner_id | 10000 | 0 ✅ |
| A | FK submissions.assessment_id -> assessments.assessment_id | 10000 | 0 ✅ |
| A | FK similarity_reports.submission_id -> submissions.submission_id | 10173 | 0 ✅ |
| A | FK similarity_reports.rule_id -> integrity_rules.rule_id | 10173 | 0 ✅ |
| A | FK cases.similarity_id -> similarity_reports.similarity_id | 300 | 0 ✅ |
| A | FK cases.submission_id -> submissions.submission_id | 300 | 0 ✅ |
| A | FK cases.opened_by_rule_id -> integrity_rules.rule_id | 300 | 0 ✅ |
| A | FK case_reviewers.case_id -> cases.case_id | 641 | 0 ✅ |
| A | FK case_reviewers.reviewer_id -> reviewers.reviewer_id | 641 | 0 ✅ |
| A | FK evidence_items.case_id -> cases.case_id | 1032 | 0 ✅ |
| A | FK decisions.case_id -> cases.case_id | 308 | 0 ✅ |
| A | FK decisions.decided_by -> reviewers.reviewer_id | 308 | 0 ✅ |
| A | FK decisions.supersedes_decision_id -> decisions.decision_id | 308 | 0 ✅ |
| A | FK appeals.case_id -> cases.case_id | 46 | 0 ✅ |
| A | FK appeals.original_decision_id -> decisions.decision_id | 46 | 0 ✅ |
| A | FK appeals.filed_by_learner_id -> learners.learner_id | 46 | 0 ✅ |
| A | FK appeals.appeal_reviewer_id -> reviewers.reviewer_id | 46 | 0 ✅ |
| A | FK appeals.resulting_decision_id -> decisions.decision_id | 46 | 0 ✅ |
| A | FK state_events.entity_id by entity_type | 14883 | 0 ✅ |
| A | FK state_events.actor_id by actor_type | 14883 | 0 ✅ |
| A | FK evidence_items.added_by_actor_id by added_by_actor_type | 1032 | 0 ✅ |
| A | date ordering and snapshot cut-off |  | 0 ✅ |
| A | adjusted_score = raw - quoted - template | 10173 | 0 ✅ |
| A | rule_id/action/flagged follow thresholds effective at scan date | 10173 | 0 ✅ |
| A | exactly one current report per submission | 10000 | 0 ✅ |
| A | no rule permits automatic guilt |  | 0 ✅ |
| A | similarity_id = SIM-<submission_id>-<version> |  | 0 ✅ |
| A | evidence/decision/appeal IDs embed their case ID |  | 0 ✅ |
| A | case derived fields reconcile to source rows | 300 | 0 ✅ |
| A | decisions: rationale present, votes/evidence counts reconcile, one initial per case | 308 | 0 ✅ |
| A | appeals reference adverse decisions of the same case; outcomes have decisions | 46 | 0 ✅ |
| A | submission.integrity_status derived consistently | 10000 | 0 ✅ |
| A | audit history complete: creation/filing/decision events exist and match record timestamps |  | 0 ✅ |
| A | SQL seed loads; PRAGMA foreign_key_check clean |  | 0 ✅ |
| A | SQL row counts equal CSV row counts |  | 0 ✅ |
| B | lifecycle: all transitions allowed (illegal ones listed) | 11543 | 10 ❌ |
| B | detector 'flag_auto_guilt': no unexplained findings, no missed labels | 8 | 0 ✅ |
| B | detector 'reviewer_conflict': no unexplained findings, no missed labels | 8 | 0 ✅ |
| B | detector 'evidence_added_after_decision_no_history': no unexplained findings, no missed labels | 8 | 0 ✅ |
| B | detector 'appeal_closed_without_independent_review': no unexplained findings, no missed labels | 6 | 0 ✅ |
| B | every illegal lifecycle transition belongs to a labelled anomaly |  | 0 ✅ |
