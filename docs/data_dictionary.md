# Data dictionary

Generated from `src/schema.py` (the same spec the validator uses).
Types: `str`, `text`, `int`, `float`, `bool`, `date` (YYYY-MM-DD), `datetime` (YYYY-MM-DDTHH:MM:SS, UTC).
**Derived** columns are recomputed from source rows, never drawn independently.

## `reviewers`

Staff actors: instructors and administrators sit on cases; support staff triage; platform admins own rules.

Primary key: `reviewer_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| reviewer_id | str | yes | `^REV-\d{4}$` |  | yes |  |  | Immutable, zero-padded |
| full_name | str | yes |  |  |  |  |  | Synthetic name |
| email | str | yes |  |  | yes |  |  | Synthetic @example.edu address |
| role | str | yes | instructor, academic_administrator, support_staff, platform_administrator |  |  |  |  |  |
| department | str | yes | Computer Science, Business, Engineering, Humanities, Life Sciences |  |  |  |  |  |
| active_from | date | yes |  |  |  |  |  | Earliest date the reviewer may be assigned |
| active_to | date | no |  |  |  |  |  | >= active_from; null = still active |

## `learners`

Students who submit assessments (fully synthetic).

Primary key: `learner_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| learner_id | str | yes | `^LRN-\d{6}$` |  | yes |  |  |  |
| full_name | str | yes |  |  |  |  |  | Synthetic name |
| email | str | yes |  |  | yes |  |  | Synthetic @example.edu address |
| programme | str | yes | BSc Computer Science, BBA Business, BEng Engineering, BA Humanities, BSc Life Sciences |  |  |  |  |  |
| cohort_year | int | yes |  | year |  |  |  | 2022..2025 |
| enrolled_date | date | yes |  |  |  |  |  | Before the first assessment opens |

## `reviewer_conflicts`

Registry of declared reviewer/learner conflicts of interest (reviewer N:M learner).

Primary key: `conflict_id`; composite uniqueness: (reviewer_id, learner_id)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| conflict_id | str | yes | `^CNF-\d{5}$` |  | yes |  |  |  |
| reviewer_id | str | yes |  |  |  | reviewers.reviewer_id |  |  |
| learner_id | str | yes |  |  |  | learners.learner_id |  |  |
| conflict_type | str | yes | family_relation, academic_supervisor, prior_dispute, same_project_group |  |  |  |  |  |
| declared_at | date | yes |  |  |  |  |  | Date the conflict was declared; must precede any assignment it blocks |

## `assessments`

Assessed pieces of work. Shared templates here explain benign overlap.

Primary key: `assessment_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| assessment_id | str | yes | `^ASM-2026-\d{4}$` |  | yes |  |  |  |
| course_code | str | yes |  |  |  |  |  |  |
| title | str | yes |  |  |  |  |  |  |
| assessment_type | str | yes | essay, report, coding_assignment, case_study, lab_report |  |  |  |  |  |
| instructor_id | str | yes |  |  |  | reviewers.reviewer_id |  | Must have role=instructor |
| opens_at | date | yes |  |  |  |  |  |  |
| due_date | date | yes |  |  |  |  |  | >= opens_at |
| word_limit | int | yes |  | words |  |  |  |  |
| has_shared_template | bool | yes |  |  |  |  |  | True if learners start from a common template |
| quotation_permitted | bool | yes |  |  |  |  |  |  |

## `integrity_rules`

Transparent, versioned thresholds/exclusions/procedures. No rule permits automatic guilt.

Primary key: `rule_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| rule_id | str | yes | `^INT-2026-\d{6}$` |  | yes |  |  |  |
| rule_name | str | yes |  |  |  |  |  |  |
| rule_type | str | yes | threshold, exclusion, procedural |  |  |  |  |  |
| action | str | yes | no_action, standard_review, priority_review, panel_escalation, exclude_from_score, procedural_control |  |  |  |  |  |
| min_adjusted_score | float | no |  | fraction 0-1 |  |  |  | Inclusive lower bound (threshold rules) |
| max_adjusted_score | float | no |  | fraction 0-1 |  |  |  | Exclusive upper bound, except 1.0 which is inclusive |
| reviewers_required | int | no |  |  |  |  |  | Minimum human reviewers for the resulting case |
| parameter_value | float | no |  |  |  |  |  | Procedural parameter (e.g. appeal window in days) |
| effective_from | date | yes |  |  |  |  |  |  |
| effective_to | date | no |  |  |  |  |  | >= effective_from; null = current |
| created_by | str | yes |  |  |  | reviewers.reviewer_id |  | role=platform_administrator |
| auto_guilt_permitted | bool | yes |  |  |  |  |  | Must always be false |
| description | text | yes |  |  |  |  |  |  |

## `submissions`

A learner's submission to an assessment (one per learner per assessment).

Primary key: `submission_id`; composite uniqueness: (learner_id, assessment_id)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| submission_id | str | yes | `^SUB-2026-\d{6}$` |  | yes |  |  |  |
| learner_id | str | yes |  |  |  | learners.learner_id |  |  |
| assessment_id | str | yes |  |  |  | assessments.assessment_id |  |  |
| submitted_at | datetime | yes |  | UTC |  |  |  |  |
| word_count | int | yes |  | words |  |  |  | > 0 |
| is_late | bool | yes |  |  |  |  | yes | submitted_at > due_date 23:59:59 |
| integrity_status | str | yes | not_flagged, flag_closed, case_in_progress, cleared, sanctioned |  |  |  | yes | Derived from current similarity report + case state |

## `similarity_reports`

Synthetic similarity scans. One current report per submission.

Primary key: `similarity_id`; composite uniqueness: (submission_id, report_version)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| similarity_id | str | yes | `^SIM-SUB-2026-\d{6}-\d{2}$` |  | yes |  |  | SIM-<submission_id>-<version> |
| submission_id | str | yes |  |  |  | submissions.submission_id |  |  |
| report_version | int | yes |  |  |  |  |  | >= 1; rescans increment |
| generated_at | datetime | yes |  | UTC |  |  |  | >= submission.submitted_at |
| raw_score | float | yes |  | fraction 0-1 |  |  |  | Total matched text share |
| quoted_match_score | float | yes |  | fraction 0-1 |  |  |  | Detected properly quoted share (exclusion INT-2026-000005) |
| template_match_score | float | yes |  | fraction 0-1 |  |  |  | Detected shared-template share (exclusion INT-2026-000006) |
| adjusted_score | float | yes |  | fraction 0-1 |  |  | yes | max(0, raw - quoted - template); tolerance 1e-4 |
| matched_source_count | int | yes |  |  |  |  |  | >= 0 |
| top_source_type | str | yes | web_page, published_work, student_paper_repository, internal_template, institutional_repository |  |  |  |  |  |
| rule_id | str | yes |  |  |  | integrity_rules.rule_id | yes | Threshold rule effective at generated_at whose band contains adjusted_score |
| recommended_action | str | yes | no_action, standard_review, priority_review, panel_escalation |  |  |  | yes | = action of rule_id |
| flagged | bool | yes |  |  |  |  | yes | True iff recommended_action != no_action |
| is_current | bool | yes |  |  |  |  |  | Exactly one current report per submission |
| flag_status | str | yes | generated, flagged, triaged_closed, case_opened |  |  |  | yes | Last state_events state |

## `cases`

Integrity review case opened from a flagged report. Current snapshot; history in state_events.

Primary key: `case_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| case_id | str | yes | `^CSE-2026-\d{6}$` |  | yes |  |  |  |
| similarity_id | str | yes |  |  | yes | similarity_reports.similarity_id |  |  |
| submission_id | str | yes |  |  |  | submissions.submission_id |  | Must equal similarity_report.submission_id |
| opened_by_rule_id | str | yes |  |  |  | integrity_rules.rule_id |  | = similarity_report.rule_id |
| opened_at | datetime | yes |  | UTC |  |  |  | >= similarity.generated_at |
| reviewers_required | int | yes |  |  |  |  |  | From opening rule |
| reviewer_count | int | yes |  |  |  |  | yes | Count of case_reviewers rows |
| evidence_count | int | yes |  |  |  |  | yes | Count of evidence_items rows |
| status | str | yes | opened, assigned, under_review, decided, appealed, appeal_under_review, closed |  |  |  | yes | Last Case state_events state |
| decided_at | datetime | no |  |  |  |  | yes | Earliest initial decision time |
| closed_at | datetime | no |  |  |  |  | yes | Time of 'closed' event |
| final_outcome | str | no | no_violation_insufficient_evidence, permitted_quotation, permitted_shared_template, false_positive_dismissed, minor_violation_warning, major_violation_penalty |  |  |  | yes | Outcome of latest decision |
| sla_due_at | datetime | yes |  | UTC |  |  | yes | opened_at + 21 days |
| sla_breached | bool | yes |  |  |  |  | yes | (decided_at or snapshot) > sla_due_at |

## `case_reviewers`

Bridge: case N:M reviewer, with role, independent recommendation and conflict check.

Primary key: `assignment_id`; composite uniqueness: (case_id, reviewer_id)

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| assignment_id | str | yes | `^CRV-\d{6}$` |  | yes |  |  |  |
| case_id | str | yes |  |  |  | cases.case_id |  |  |
| reviewer_id | str | yes |  |  |  | reviewers.reviewer_id |  |  |
| assignment_role | str | yes | primary, second, panel_member, tiebreak |  |  |  |  |  |
| assigned_at | datetime | yes |  | UTC |  |  |  |  |
| recommendation | str | no | violation, no_violation |  |  |  |  |  |
| recommended_at | datetime | no |  | UTC |  |  |  | >= assigned_at |
| conflict_checked | bool | yes |  |  |  |  |  | Conflict registry consulted before assignment |

## `evidence_items`

Evidence attached to a case. Every addition has a state_events row.

Primary key: `evidence_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| evidence_id | str | yes | `^EVD-CSE-2026-\d{6}-\d{3}$` |  | yes |  |  | EVD-<case_id>-<seq> |
| case_id | str | yes |  |  |  | cases.case_id |  |  |
| evidence_type | str | yes | similarity_report_excerpt, source_match, citation_check, template_comparison, draft_history, instructor_note, learner_statement |  |  |  |  |  |
| description | text | yes |  |  |  |  |  |  |
| source_ref | str | yes |  |  |  |  |  | Synthetic evidence:// URI |
| content_sha256 | str | yes |  |  |  |  |  | 64 hex chars; tamper-evidence stub |
| evidence_stage | str | yes | pre_decision, appeal |  |  |  |  | 'appeal' only for evidence added during an appeal |
| added_at | datetime | yes |  | UTC |  |  |  | >= case.opened_at |
| added_by_actor_type | str | yes | reviewer, learner, system |  |  |  |  |  |
| added_by_actor_id | str | no |  |  |  |  |  | reviewers or learners PK by actor_type; null for system |

## `decisions`

Append-only decisions. An appeal outcome adds a new row; the original is never edited.

Primary key: `decision_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| decision_id | str | yes | `^DEC-CSE-2026-\d{6}-\d{2}$` |  | yes |  |  |  |
| case_id | str | yes |  |  |  | cases.case_id |  |  |
| decision_stage | str | yes | initial, appeal |  |  |  |  |  |
| outcome | str | yes | no_violation_insufficient_evidence, permitted_quotation, permitted_shared_template, false_positive_dismissed, minor_violation_warning, major_violation_penalty |  |  |  |  |  |
| rationale | text | yes |  |  |  |  |  | Mandatory, non-empty |
| decision_basis | str | yes | reviewer_vote, auto_threshold |  |  |  |  | Baseline is always reviewer_vote |
| decided_by | str | no |  |  |  | reviewers.reviewer_id |  | Lead reviewer |
| decided_at | datetime | yes |  | UTC |  |  |  |  |
| votes_violation | int | no |  |  |  |  | yes | Count of 'violation' recommendations (initial stage) |
| votes_total | int | no |  |  |  |  | yes | Count of recommendations (initial stage) |
| evidence_count_at_decision | int | yes |  |  |  |  | yes | Evidence rows with added_at <= decided_at |
| supersedes_decision_id | str | no |  |  |  | decisions.decision_id |  | Set on appeal-stage decisions |

## `appeals`

Learner appeals of adverse decisions (max one per case).

Primary key: `appeal_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| appeal_id | str | yes | `^APL-CSE-2026-\d{6}-\d{2}$` |  | yes |  |  |  |
| case_id | str | yes |  |  | yes | cases.case_id |  | At most one appeal per case |
| original_decision_id | str | yes |  |  |  | decisions.decision_id |  | Must be an adverse (violation) decision |
| filed_by_learner_id | str | yes |  |  |  | learners.learner_id |  |  |
| filed_at | datetime | yes |  | UTC |  |  |  | Within 14 days after decision (INT-2026-000007) |
| grounds | str | yes | false_positive_evidence, quotation_properly_cited, template_overlap, procedural_irregularity, new_evidence, disproportionate_penalty |  |  |  |  |  |
| status | str | yes | filed, under_review, resolved, withdrawn |  |  |  | yes | Last Appeal state_events state |
| appeal_reviewer_id | str | no |  |  |  | reviewers.reviewer_id |  | Administrator not on the original case and without conflict (INT-2026-000008) |
| review_assigned_at | datetime | no |  | UTC |  |  |  |  |
| resolved_at | datetime | no |  | UTC |  |  |  |  |
| outcome | str | no | upheld, overturned, reduced, withdrawn |  |  |  |  |  |
| independent_review_completed | bool | yes |  |  |  |  |  | True only if resolved by an independent reviewer |
| resulting_decision_id | str | no |  |  |  | decisions.decision_id |  | Set when overturned/reduced |
| resolution_rationale | text | no |  |  |  |  |  |  |

## `state_events`

Append-only audit trail of every state change (flags, cases, evidence, appeals).

Primary key: `event_id`

| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |
|---|---|---|---|---|---|---|---|---|
| event_id | str | yes | `^EVT-\d{7}$` |  | yes |  |  |  |
| entity_type | str | yes | SimilarityReport, Case, EvidenceItem, Appeal |  |  |  |  |  |
| entity_id | str | yes |  |  |  |  |  | PK of the entity named by entity_type |
| from_state | str | no |  |  |  |  |  | Null on creation |
| to_state | str | yes |  |  |  |  |  |  |
| event_at | datetime | yes |  | UTC |  |  |  |  |
| actor_type | str | yes | reviewer, learner, system |  |  |  |  |  |
| actor_id | str | no |  |  |  |  |  | reviewers or learners PK by actor_type; null for system |
| note | text | no |  |  |  |  |  |  |

