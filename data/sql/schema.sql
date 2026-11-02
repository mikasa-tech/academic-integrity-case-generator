-- SQLite-compatible DDL generated from src/schema.py
CREATE TABLE reviewers (
  reviewer_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('instructor', 'academic_administrator', 'support_staff', 'platform_administrator')),
  department TEXT NOT NULL CHECK (department IN ('Computer Science', 'Business', 'Engineering', 'Humanities', 'Life Sciences')),
  active_from TEXT NOT NULL,
  active_to TEXT
);

CREATE TABLE learners (
  learner_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  programme TEXT NOT NULL CHECK (programme IN ('BSc Computer Science', 'BBA Business', 'BEng Engineering', 'BA Humanities', 'BSc Life Sciences')),
  cohort_year INTEGER NOT NULL,
  enrolled_date TEXT NOT NULL
);

CREATE TABLE reviewer_conflicts (
  conflict_id TEXT PRIMARY KEY,
  reviewer_id TEXT NOT NULL,
  learner_id TEXT NOT NULL,
  conflict_type TEXT NOT NULL CHECK (conflict_type IN ('family_relation', 'academic_supervisor', 'prior_dispute', 'same_project_group')),
  declared_at TEXT NOT NULL,
  FOREIGN KEY (reviewer_id) REFERENCES reviewers(reviewer_id),
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  UNIQUE (reviewer_id, learner_id)
);

CREATE TABLE assessments (
  assessment_id TEXT PRIMARY KEY,
  course_code TEXT NOT NULL,
  title TEXT NOT NULL,
  assessment_type TEXT NOT NULL CHECK (assessment_type IN ('essay', 'report', 'coding_assignment', 'case_study', 'lab_report')),
  instructor_id TEXT NOT NULL,
  opens_at TEXT NOT NULL,
  due_date TEXT NOT NULL,
  word_limit INTEGER NOT NULL,
  has_shared_template INTEGER NOT NULL CHECK (has_shared_template IN (0,1)),
  quotation_permitted INTEGER NOT NULL CHECK (quotation_permitted IN (0,1)),
  FOREIGN KEY (instructor_id) REFERENCES reviewers(reviewer_id)
);

CREATE TABLE integrity_rules (
  rule_id TEXT PRIMARY KEY,
  rule_name TEXT NOT NULL,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('threshold', 'exclusion', 'procedural')),
  action TEXT NOT NULL CHECK (action IN ('no_action', 'standard_review', 'priority_review', 'panel_escalation', 'exclude_from_score', 'procedural_control')),
  min_adjusted_score REAL,
  max_adjusted_score REAL,
  reviewers_required INTEGER,
  parameter_value REAL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  created_by TEXT NOT NULL,
  auto_guilt_permitted INTEGER NOT NULL CHECK (auto_guilt_permitted IN (0,1)),
  description TEXT NOT NULL,
  FOREIGN KEY (created_by) REFERENCES reviewers(reviewer_id)
);

CREATE TABLE submissions (
  submission_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  assessment_id TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  word_count INTEGER NOT NULL,
  is_late INTEGER NOT NULL CHECK (is_late IN (0,1)),
  integrity_status TEXT NOT NULL CHECK (integrity_status IN ('not_flagged', 'flag_closed', 'case_in_progress', 'cleared', 'sanctioned')),
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
  UNIQUE (learner_id, assessment_id)
);

CREATE TABLE similarity_reports (
  similarity_id TEXT PRIMARY KEY,
  submission_id TEXT NOT NULL,
  report_version INTEGER NOT NULL,
  generated_at TEXT NOT NULL,
  raw_score REAL NOT NULL,
  quoted_match_score REAL NOT NULL,
  template_match_score REAL NOT NULL,
  adjusted_score REAL NOT NULL,
  matched_source_count INTEGER NOT NULL,
  top_source_type TEXT NOT NULL CHECK (top_source_type IN ('web_page', 'published_work', 'student_paper_repository', 'internal_template', 'institutional_repository')),
  rule_id TEXT NOT NULL,
  recommended_action TEXT NOT NULL CHECK (recommended_action IN ('no_action', 'standard_review', 'priority_review', 'panel_escalation')),
  flagged INTEGER NOT NULL CHECK (flagged IN (0,1)),
  is_current INTEGER NOT NULL CHECK (is_current IN (0,1)),
  flag_status TEXT NOT NULL CHECK (flag_status IN ('generated', 'flagged', 'triaged_closed', 'case_opened')),
  FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
  FOREIGN KEY (rule_id) REFERENCES integrity_rules(rule_id),
  UNIQUE (submission_id, report_version)
);

CREATE TABLE cases (
  case_id TEXT PRIMARY KEY,
  similarity_id TEXT NOT NULL UNIQUE,
  submission_id TEXT NOT NULL,
  opened_by_rule_id TEXT NOT NULL,
  opened_at TEXT NOT NULL,
  reviewers_required INTEGER NOT NULL,
  reviewer_count INTEGER NOT NULL,
  evidence_count INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('opened', 'assigned', 'under_review', 'decided', 'appealed', 'appeal_under_review', 'closed')),
  decided_at TEXT,
  closed_at TEXT,
  final_outcome TEXT CHECK (final_outcome IN ('no_violation_insufficient_evidence', 'permitted_quotation', 'permitted_shared_template', 'false_positive_dismissed', 'minor_violation_warning', 'major_violation_penalty')),
  sla_due_at TEXT NOT NULL,
  sla_breached INTEGER NOT NULL CHECK (sla_breached IN (0,1)),
  FOREIGN KEY (similarity_id) REFERENCES similarity_reports(similarity_id),
  FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
  FOREIGN KEY (opened_by_rule_id) REFERENCES integrity_rules(rule_id)
);

CREATE TABLE case_reviewers (
  assignment_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  reviewer_id TEXT NOT NULL,
  assignment_role TEXT NOT NULL CHECK (assignment_role IN ('primary', 'second', 'panel_member', 'tiebreak')),
  assigned_at TEXT NOT NULL,
  recommendation TEXT CHECK (recommendation IN ('violation', 'no_violation')),
  recommended_at TEXT,
  conflict_checked INTEGER NOT NULL CHECK (conflict_checked IN (0,1)),
  FOREIGN KEY (case_id) REFERENCES cases(case_id),
  FOREIGN KEY (reviewer_id) REFERENCES reviewers(reviewer_id),
  UNIQUE (case_id, reviewer_id)
);

CREATE TABLE evidence_items (
  evidence_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  evidence_type TEXT NOT NULL CHECK (evidence_type IN ('similarity_report_excerpt', 'source_match', 'citation_check', 'template_comparison', 'draft_history', 'instructor_note', 'learner_statement')),
  description TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  evidence_stage TEXT NOT NULL CHECK (evidence_stage IN ('pre_decision', 'appeal')),
  added_at TEXT NOT NULL,
  added_by_actor_type TEXT NOT NULL CHECK (added_by_actor_type IN ('reviewer', 'learner', 'system')),
  added_by_actor_id TEXT,
  FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE decisions (
  decision_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  decision_stage TEXT NOT NULL CHECK (decision_stage IN ('initial', 'appeal')),
  outcome TEXT NOT NULL CHECK (outcome IN ('no_violation_insufficient_evidence', 'permitted_quotation', 'permitted_shared_template', 'false_positive_dismissed', 'minor_violation_warning', 'major_violation_penalty')),
  rationale TEXT NOT NULL,
  decision_basis TEXT NOT NULL CHECK (decision_basis IN ('reviewer_vote', 'auto_threshold')),
  decided_by TEXT,
  decided_at TEXT NOT NULL,
  votes_violation INTEGER,
  votes_total INTEGER,
  evidence_count_at_decision INTEGER NOT NULL,
  supersedes_decision_id TEXT,
  FOREIGN KEY (case_id) REFERENCES cases(case_id),
  FOREIGN KEY (decided_by) REFERENCES reviewers(reviewer_id),
  FOREIGN KEY (supersedes_decision_id) REFERENCES decisions(decision_id)
);

CREATE TABLE appeals (
  appeal_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL UNIQUE,
  original_decision_id TEXT NOT NULL,
  filed_by_learner_id TEXT NOT NULL,
  filed_at TEXT NOT NULL,
  grounds TEXT NOT NULL CHECK (grounds IN ('false_positive_evidence', 'quotation_properly_cited', 'template_overlap', 'procedural_irregularity', 'new_evidence', 'disproportionate_penalty')),
  status TEXT NOT NULL CHECK (status IN ('filed', 'under_review', 'resolved', 'withdrawn')),
  appeal_reviewer_id TEXT,
  review_assigned_at TEXT,
  resolved_at TEXT,
  outcome TEXT CHECK (outcome IN ('upheld', 'overturned', 'reduced', 'withdrawn')),
  independent_review_completed INTEGER NOT NULL CHECK (independent_review_completed IN (0,1)),
  resulting_decision_id TEXT,
  resolution_rationale TEXT,
  FOREIGN KEY (case_id) REFERENCES cases(case_id),
  FOREIGN KEY (original_decision_id) REFERENCES decisions(decision_id),
  FOREIGN KEY (filed_by_learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (appeal_reviewer_id) REFERENCES reviewers(reviewer_id),
  FOREIGN KEY (resulting_decision_id) REFERENCES decisions(decision_id)
);

CREATE TABLE state_events (
  event_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('SimilarityReport', 'Case', 'EvidenceItem', 'Appeal')),
  entity_id TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  event_at TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('reviewer', 'learner', 'system')),
  actor_id TEXT,
  note TEXT
);
