"""Documented business rules and parameters.

Every outcome in the dataset is derived from these rules plus a latent
"true cause" of the similarity (see generate.py). Nothing here assigns guilt
from a score alone: a threshold only decides *how much human review* is needed.
"""
from datetime import datetime

SNAPSHOT = datetime(2026, 10, 31, 23, 59, 59)   # "now" for the dataset; no real clock is ever read

APPEAL_WINDOW_DAYS = 14        # INT-2026-000007
SLA_DAYS = 21                  # case decision SLA

REVIEWER_ACCURACY_GENUINE = 0.90      # P(reviewer recommends 'violation' | real misconduct)
REVIEWER_ACCURACY_OTHER = 0.85        # P(reviewer clears | benign overlap) - lower: high scores bias reviewers
APPEAL_ACCURACY = 0.92         # P(independent appeal reviewer reaches the true conclusion)
P_APPEAL_IF_WRONGLY_ACCUSED = 0.80
P_APPEAL_IF_GUILTY = 0.22
P_APPEAL_WITHDRAWN = 0.08
P_BOUNDARY = 0.04              # share of flags placed exactly on a band's lower bound
P_RESCAN = 0.02                # share of unflagged submissions that get a v02 report
ANOMALY_RATE = 0.025           # injected anomalies per type, as a share of cases (min 2)

# Flag volume shaping (fractions of the flag count). The case count is pinned to
# the brief (300 at scale 1.0): all priority/escalation flags open a case, plus a
# small set of standard-review flags that the triage reviewer refers.
REFERRED_SHARE_OF_FLAGS = 0.05
ESCALATION_SHARE_OF_PRIORITY_AND_ESCALATION = 0.32

# Latent cause of the similarity, by where the flag landed. 'genuine' = real misconduct.
LATENT_MIX = {
    "closed":   [("genuine", 8), ("legit_quote", 25), ("shared_template", 30), ("false_positive", 37)],
    "ref":      [("genuine", 70), ("legit_quote", 15), ("shared_template", 0), ("false_positive", 15)],
    "priority": [("genuine", 55), ("legit_quote", 15), ("shared_template", 12), ("false_positive", 18)],
    "escalate": [("genuine", 75), ("legit_quote", 10), ("shared_template", 5), ("false_positive", 10)],
}
BAND_RANGE = {"closed": (0.25, 0.4999), "ref": (0.25, 0.4999),
              "priority": (0.50, 0.7499), "escalate": (0.75, 0.92)}
BAND_LOWER = {"closed": 0.25, "ref": 0.25, "priority": 0.50, "escalate": 0.75}

NONVIOLATION_OUTCOME = {
    "genuine": "no_violation_insufficient_evidence",   # reviewers wrongly cleared real misconduct
    "legit_quote": "permitted_quotation",
    "shared_template": "permitted_shared_template",
    "false_positive": "false_positive_dismissed",
}


def violation_outcome(adjusted_score):
    """Severity is a documented function of the adjusted score (proportionality)."""
    return "major_violation_penalty" if adjusted_score >= 0.75 else "minor_violation_warning"


def expected_outcome(latent, adjusted_score):
    """Ground-truth 'right answer' for a case, from its true cause."""
    return violation_outcome(adjusted_score) if latent == "genuine" else NONVIOLATION_OUTCOME[latent]


# ------------------------------------------------------------ rule lookup
def rule_active(rule, d):
    return rule["effective_from"] <= d and (rule["effective_to"] is None or d <= rule["effective_to"])


def classify(score, d, rules):
    """Return the threshold rule row whose band contains `score` on date `d`.
    Bands are [min, max) except a top band with max == 1.0, which is [min, 1.0]."""
    for r in rules:
        if r["rule_type"] != "threshold" or not rule_active(r, d):
            continue
        mn, mx = r["min_adjusted_score"], r["max_adjusted_score"]
        if score >= mn and (score < mx or (mx >= 1.0 and score <= 1.0)):
            return r
    raise ValueError(f"no threshold rule for score={score} on {d}")


def rationale(outcome, adjusted, rule_id, votes_v, votes_t, n_evidence):
    head = (f"Adjusted similarity {adjusted:.2f} met review threshold {rule_id}, which requires human review "
            f"and does not imply guilt. {n_evidence} evidence item(s) examined; {votes_v} of {votes_t} "
            f"reviewer(s) recommended a violation.")
    tail = {
        "no_violation_insufficient_evidence": " Evidence did not establish misconduct; case closed without penalty.",
        "permitted_quotation": " Matched passages are attributed quotations permitted by the assessment brief.",
        "permitted_shared_template": " Overlap is attributable to the shared assessment template provided to all learners.",
        "false_positive_dismissed": " Matches are common phrasing or reference-list boilerplate; flag dismissed as a false positive.",
        "minor_violation_warning": " Unattributed overlap confirmed; formal warning and resubmission advised.",
        "major_violation_penalty": " Substantial unattributed overlap confirmed across multiple sources; grade penalty applied.",
    }[outcome]
    return head + tail
