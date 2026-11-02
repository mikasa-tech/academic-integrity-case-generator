"""Single source of truth for the data model.

Used by generate.py (SQL DDL + data dictionary) and validate.py (type, enum,
required, uniqueness, pattern and FK checks), so the documentation, the
database and the validator can never drift apart.
"""
from collections import OrderedDict

# ---------------------------------------------------------------- enums
ROLES = ["instructor", "academic_administrator", "support_staff", "platform_administrator"]
DEPARTMENTS = ["Computer Science", "Business", "Engineering", "Humanities", "Life Sciences"]
PROGRAMMES = ["BSc Computer Science", "BBA Business", "BEng Engineering", "BA Humanities", "BSc Life Sciences"]
ASSESS_TYPES = ["essay", "report", "coding_assignment", "case_study", "lab_report"]
CONFLICT_TYPES = ["family_relation", "academic_supervisor", "prior_dispute", "same_project_group"]
RULE_TYPES = ["threshold", "exclusion", "procedural"]
RULE_ACTIONS = ["no_action", "standard_review", "priority_review", "panel_escalation",
                "exclude_from_score", "procedural_control"]
BAND_ACTIONS = ["no_action", "standard_review", "priority_review", "panel_escalation"]
SOURCE_TYPES = ["web_page", "published_work", "student_paper_repository",
                "internal_template", "institutional_repository"]
FLAG_STATES = ["generated", "flagged", "triaged_closed", "case_opened"]
CASE_STATES = ["opened", "assigned", "under_review", "decided", "appealed",
               "appeal_under_review", "closed"]
APPEAL_STATES = ["filed", "under_review", "resolved", "withdrawn"]
EVIDENCE_STATES = ["added"]
OUTCOMES = ["no_violation_insufficient_evidence", "permitted_quotation", "permitted_shared_template",
            "false_positive_dismissed", "minor_violation_warning", "major_violation_penalty"]
VIOLATION_OUTCOMES = ["minor_violation_warning", "major_violation_penalty"]
EVIDENCE_TYPES = ["similarity_report_excerpt", "source_match", "citation_check",
                  "template_comparison", "draft_history", "instructor_note", "learner_statement"]
EVIDENCE_STAGES = ["pre_decision", "appeal"]
APPEAL_GROUNDS = ["false_positive_evidence", "quotation_properly_cited", "template_overlap",
                  "procedural_irregularity", "new_evidence", "disproportionate_penalty"]
APPEAL_OUTCOMES = ["upheld", "overturned", "reduced", "withdrawn"]
INTEGRITY_STATUS = ["not_flagged", "flag_closed", "case_in_progress", "cleared", "sanctioned"]
ENTITY_TYPES = ["SimilarityReport", "Case", "EvidenceItem", "Appeal"]
ACTOR_TYPES = ["reviewer", "learner", "system"]
RECOMMENDATIONS = ["violation", "no_violation"]
ASSIGN_ROLES = ["primary", "second", "panel_member", "tiebreak"]
DECISION_STAGES = ["initial", "appeal"]
DECISION_BASES = ["reviewer_vote", "auto_threshold"]  # auto_threshold is only ever produced by the injected anomaly

# Allowed lifecycle transitions (from_state -> set of to_states); None = creation.
TRANSITIONS = {
    "SimilarityReport": {None: {"generated"}, "generated": {"flagged"},
                         "flagged": {"triaged_closed", "case_opened"}},
    "Case": {None: {"opened"}, "opened": {"assigned"}, "assigned": {"under_review"},
             "under_review": {"decided"}, "decided": {"closed", "appealed"},
             "appealed": {"appeal_under_review", "closed"},      # appealed->closed = withdrawal
             "appeal_under_review": {"closed"}},
    "EvidenceItem": {None: {"added"}},
    "Appeal": {None: {"filed"}, "filed": {"under_review", "withdrawn"}, "under_review": {"resolved"}},
}


def F(name, typ, req=True, allowed=None, unit="", uniq=False, rule="", pat=None, fk=None, derived=False):
    return dict(name=name, type=typ, required=req, allowed=allowed, unit=unit,
                unique=uniq, rule=rule, pattern=pat, fk=fk, derived=derived)


T = OrderedDict()


def table(name, pk, desc, fields, unique=()):
    T[name] = dict(pk=pk, desc=desc, fields=fields, unique=[list(u) for u in unique])


table("reviewers", "reviewer_id",
      "Staff actors: instructors and administrators sit on cases; support staff triage; platform admins own rules.", [
    F("reviewer_id", "str", pat=r"^REV-\d{4}$", uniq=True, rule="Immutable, zero-padded"),
    F("full_name", "str", rule="Synthetic name"),
    F("email", "str", uniq=True, rule="Synthetic @example.edu address"),
    F("role", "str", allowed=ROLES),
    F("department", "str", allowed=DEPARTMENTS),
    F("active_from", "date", rule="Earliest date the reviewer may be assigned"),
    F("active_to", "date", req=False, rule=">= active_from; null = still active"),
])

table("learners", "learner_id", "Students who submit assessments (fully synthetic).", [
    F("learner_id", "str", pat=r"^LRN-\d{6}$", uniq=True),
    F("full_name", "str", rule="Synthetic name"),
    F("email", "str", uniq=True, rule="Synthetic @example.edu address"),
    F("programme", "str", allowed=PROGRAMMES),
    F("cohort_year", "int", unit="year", rule="2022..2025"),
    F("enrolled_date", "date", rule="Before the first assessment opens"),
])

table("reviewer_conflicts", "conflict_id",
      "Registry of declared reviewer/learner conflicts of interest (reviewer N:M learner).", [
    F("conflict_id", "str", pat=r"^CNF-\d{5}$", uniq=True),
    F("reviewer_id", "str", fk="reviewers.reviewer_id"),
    F("learner_id", "str", fk="learners.learner_id"),
    F("conflict_type", "str", allowed=CONFLICT_TYPES),
    F("declared_at", "date", rule="Date the conflict was declared; must precede any assignment it blocks"),
], unique=[("reviewer_id", "learner_id")])

table("assessments", "assessment_id", "Assessed pieces of work. Shared templates here explain benign overlap.", [
    F("assessment_id", "str", pat=r"^ASM-2026-\d{4}$", uniq=True),
    F("course_code", "str"),
    F("title", "str"),
    F("assessment_type", "str", allowed=ASSESS_TYPES),
    F("instructor_id", "str", fk="reviewers.reviewer_id", rule="Must have role=instructor"),
    F("opens_at", "date"),
    F("due_date", "date", rule=">= opens_at"),
    F("word_limit", "int", unit="words"),
    F("has_shared_template", "bool", rule="True if learners start from a common template"),
    F("quotation_permitted", "bool"),
])

table("integrity_rules", "rule_id",
      "Transparent, versioned thresholds/exclusions/procedures. No rule permits automatic guilt.", [
    F("rule_id", "str", pat=r"^INT-2026-\d{6}$", uniq=True),
    F("rule_name", "str"),
    F("rule_type", "str", allowed=RULE_TYPES),
    F("action", "str", allowed=RULE_ACTIONS),
    F("min_adjusted_score", "float", req=False, unit="fraction 0-1", rule="Inclusive lower bound (threshold rules)"),
    F("max_adjusted_score", "float", req=False, unit="fraction 0-1",
      rule="Exclusive upper bound, except 1.0 which is inclusive"),
    F("reviewers_required", "int", req=False, rule="Minimum human reviewers for the resulting case"),
    F("parameter_value", "float", req=False, rule="Procedural parameter (e.g. appeal window in days)"),
    F("effective_from", "date"),
    F("effective_to", "date", req=False, rule=">= effective_from; null = current"),
    F("created_by", "str", fk="reviewers.reviewer_id", rule="role=platform_administrator"),
    F("auto_guilt_permitted", "bool", rule="Must always be false"),
    F("description", "text"),
])

table("submissions", "submission_id", "A learner's submission to an assessment (one per learner per assessment).", [
    F("submission_id", "str", pat=r"^SUB-2026-\d{6}$", uniq=True),
    F("learner_id", "str", fk="learners.learner_id"),
    F("assessment_id", "str", fk="assessments.assessment_id"),
    F("submitted_at", "datetime", unit="UTC"),
    F("word_count", "int", unit="words", rule="> 0"),
    F("is_late", "bool", derived=True, rule="submitted_at > due_date 23:59:59"),
    F("integrity_status", "str", allowed=INTEGRITY_STATUS, derived=True,
      rule="Derived from current similarity report + case state"),
], unique=[("learner_id", "assessment_id")])

table("similarity_reports", "similarity_id", "Synthetic similarity scans. One current report per submission.", [
    F("similarity_id", "str", pat=r"^SIM-SUB-2026-\d{6}-\d{2}$", uniq=True, rule="SIM-<submission_id>-<version>"),
    F("submission_id", "str", fk="submissions.submission_id"),
    F("report_version", "int", rule=">= 1; rescans increment"),
    F("generated_at", "datetime", unit="UTC", rule=">= submission.submitted_at"),
    F("raw_score", "float", unit="fraction 0-1", rule="Total matched text share"),
    F("quoted_match_score", "float", unit="fraction 0-1", rule="Detected properly quoted share (exclusion INT-2026-000005)"),
    F("template_match_score", "float", unit="fraction 0-1", rule="Detected shared-template share (exclusion INT-2026-000006)"),
    F("adjusted_score", "float", unit="fraction 0-1", derived=True,
      rule="max(0, raw - quoted - template); tolerance 1e-4"),
    F("matched_source_count", "int", rule=">= 0"),
    F("top_source_type", "str", allowed=SOURCE_TYPES),
    F("rule_id", "str", fk="integrity_rules.rule_id", derived=True,
      rule="Threshold rule effective at generated_at whose band contains adjusted_score"),
    F("recommended_action", "str", allowed=BAND_ACTIONS, derived=True, rule="= action of rule_id"),
    F("flagged", "bool", derived=True, rule="True iff recommended_action != no_action"),
    F("is_current", "bool", rule="Exactly one current report per submission"),
    F("flag_status", "str", allowed=FLAG_STATES, derived=True, rule="Last state_events state"),
], unique=[("submission_id", "report_version")])

table("cases", "case_id", "Integrity review case opened from a flagged report. Current snapshot; history in state_events.", [
    F("case_id", "str", pat=r"^CSE-2026-\d{6}$", uniq=True),
    F("similarity_id", "str", fk="similarity_reports.similarity_id", uniq=True),
    F("submission_id", "str", fk="submissions.submission_id", rule="Must equal similarity_report.submission_id"),
    F("opened_by_rule_id", "str", fk="integrity_rules.rule_id", rule="= similarity_report.rule_id"),
    F("opened_at", "datetime", unit="UTC", rule=">= similarity.generated_at"),
    F("reviewers_required", "int", rule="From opening rule"),
    F("reviewer_count", "int", derived=True, rule="Count of case_reviewers rows"),
    F("evidence_count", "int", derived=True, rule="Count of evidence_items rows"),
    F("status", "str", allowed=CASE_STATES, derived=True, rule="Last Case state_events state"),
    F("decided_at", "datetime", req=False, derived=True, rule="Earliest initial decision time"),
    F("closed_at", "datetime", req=False, derived=True, rule="Time of 'closed' event"),
    F("final_outcome", "str", req=False, allowed=OUTCOMES, derived=True, rule="Outcome of latest decision"),
    F("sla_due_at", "datetime", unit="UTC", derived=True, rule="opened_at + 21 days"),
    F("sla_breached", "bool", derived=True, rule="(decided_at or snapshot) > sla_due_at"),
])

table("case_reviewers", "assignment_id",
      "Bridge: case N:M reviewer, with role, independent recommendation and conflict check.", [
    F("assignment_id", "str", pat=r"^CRV-\d{6}$", uniq=True),
    F("case_id", "str", fk="cases.case_id"),
    F("reviewer_id", "str", fk="reviewers.reviewer_id"),
    F("assignment_role", "str", allowed=ASSIGN_ROLES),
    F("assigned_at", "datetime", unit="UTC"),
    F("recommendation", "str", req=False, allowed=RECOMMENDATIONS),
    F("recommended_at", "datetime", req=False, unit="UTC", rule=">= assigned_at"),
    F("conflict_checked", "bool", rule="Conflict registry consulted before assignment"),
], unique=[("case_id", "reviewer_id")])

table("evidence_items", "evidence_id", "Evidence attached to a case. Every addition has a state_events row.", [
    F("evidence_id", "str", pat=r"^EVD-CSE-2026-\d{6}-\d{3}$", uniq=True, rule="EVD-<case_id>-<seq>"),
    F("case_id", "str", fk="cases.case_id"),
    F("evidence_type", "str", allowed=EVIDENCE_TYPES),
    F("description", "text"),
    F("source_ref", "str", rule="Synthetic evidence:// URI"),
    F("content_sha256", "str", rule="64 hex chars; tamper-evidence stub"),
    F("evidence_stage", "str", allowed=EVIDENCE_STAGES, rule="'appeal' only for evidence added during an appeal"),
    F("added_at", "datetime", unit="UTC", rule=">= case.opened_at"),
    F("added_by_actor_type", "str", allowed=ACTOR_TYPES),
    F("added_by_actor_id", "str", req=False, rule="reviewers or learners PK by actor_type; null for system"),
])

table("decisions", "decision_id", "Append-only decisions. An appeal outcome adds a new row; the original is never edited.", [
    F("decision_id", "str", pat=r"^DEC-CSE-2026-\d{6}-\d{2}$", uniq=True),
    F("case_id", "str", fk="cases.case_id"),
    F("decision_stage", "str", allowed=DECISION_STAGES),
    F("outcome", "str", allowed=OUTCOMES),
    F("rationale", "text", rule="Mandatory, non-empty"),
    F("decision_basis", "str", allowed=DECISION_BASES, rule="Baseline is always reviewer_vote"),
    F("decided_by", "str", req=False, fk="reviewers.reviewer_id", rule="Lead reviewer"),
    F("decided_at", "datetime", unit="UTC"),
    F("votes_violation", "int", req=False, derived=True, rule="Count of 'violation' recommendations (initial stage)"),
    F("votes_total", "int", req=False, derived=True, rule="Count of recommendations (initial stage)"),
    F("evidence_count_at_decision", "int", derived=True, rule="Evidence rows with added_at <= decided_at"),
    F("supersedes_decision_id", "str", req=False, fk="decisions.decision_id", rule="Set on appeal-stage decisions"),
])

table("appeals", "appeal_id", "Learner appeals of adverse decisions (max one per case).", [
    F("appeal_id", "str", pat=r"^APL-CSE-2026-\d{6}-\d{2}$", uniq=True),
    F("case_id", "str", fk="cases.case_id", uniq=True, rule="At most one appeal per case"),
    F("original_decision_id", "str", fk="decisions.decision_id", rule="Must be an adverse (violation) decision"),
    F("filed_by_learner_id", "str", fk="learners.learner_id"),
    F("filed_at", "datetime", unit="UTC", rule="Within 14 days after decision (INT-2026-000007)"),
    F("grounds", "str", allowed=APPEAL_GROUNDS),
    F("status", "str", allowed=APPEAL_STATES, derived=True, rule="Last Appeal state_events state"),
    F("appeal_reviewer_id", "str", req=False, fk="reviewers.reviewer_id",
      rule="Administrator not on the original case and without conflict (INT-2026-000008)"),
    F("review_assigned_at", "datetime", req=False, unit="UTC"),
    F("resolved_at", "datetime", req=False, unit="UTC"),
    F("outcome", "str", req=False, allowed=APPEAL_OUTCOMES),
    F("independent_review_completed", "bool", rule="True only if resolved by an independent reviewer"),
    F("resulting_decision_id", "str", req=False, fk="decisions.decision_id", rule="Set when overturned/reduced"),
    F("resolution_rationale", "text", req=False),
])

table("state_events", "event_id", "Append-only audit trail of every state change (flags, cases, evidence, appeals).", [
    F("event_id", "str", pat=r"^EVT-\d{7}$", uniq=True),
    F("entity_type", "str", allowed=ENTITY_TYPES),
    F("entity_id", "str", rule="PK of the entity named by entity_type"),
    F("from_state", "str", req=False, rule="Null on creation"),
    F("to_state", "str"),
    F("event_at", "datetime", unit="UTC"),
    F("actor_type", "str", allowed=ACTOR_TYPES),
    F("actor_id", "str", req=False, rule="reviewers or learners PK by actor_type; null for system"),
    F("note", "text", req=False),
])

# creation order respects FK dependencies (parents first)
ORDER = ["reviewers", "learners", "reviewer_conflicts", "assessments", "integrity_rules", "submissions",
         "similarity_reports", "cases", "case_reviewers", "evidence_items", "decisions", "appeals",
         "state_events"]
assert list(T.keys()) == ORDER or set(T.keys()) == set(ORDER)
T = OrderedDict((k, T[k]) for k in ORDER)

SQL_TYPES = {"str": "TEXT", "text": "TEXT", "int": "INTEGER", "float": "REAL",
             "bool": "INTEGER", "date": "TEXT", "datetime": "TEXT"}


def ddl():
    out = []
    for name, t in T.items():
        cols, cons = [], []
        for f in t["fields"]:
            c = f"  {f['name']} {SQL_TYPES[f['type']]}"
            if f["name"] == t["pk"]:
                c += " PRIMARY KEY"
            elif f["required"]:
                c += " NOT NULL"
            if f["allowed"]:
                vals = ", ".join("'%s'" % v for v in f["allowed"])
                c += f" CHECK ({f['name']} IN ({vals}))"
            if f["type"] == "bool":
                c += f" CHECK ({f['name']} IN (0,1))"
            if f["unique"] and f["name"] != t["pk"]:
                c += " UNIQUE"
            cols.append(c)
            if f["fk"]:
                tt, cc = f["fk"].split(".")
                cons.append(f"  FOREIGN KEY ({f['name']}) REFERENCES {tt}({cc})")
        for u in t["unique"]:
            if len(u) > 1:
                cons.append(f"  UNIQUE ({', '.join(u)})")
        out.append(f"CREATE TABLE {name} (\n" + ",\n".join(cols + cons) + "\n);")
    return "\n\n".join(out)
