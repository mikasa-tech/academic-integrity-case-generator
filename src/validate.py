#!/usr/bin/env python3
"""Validate a generated dataset.

    python src/validate.py --data data

Two groups of checks:
  A. Structural (must all pass): PK uniqueness, FK integrity, types, enums, patterns, required fields,
     date ordering, arithmetic reconciliation, duplicate checks, SQL load into SQLite.
  B. Process checks (lifecycle + four anomaly detectors). These are *expected* to fire on the injected
     anomalies. Detection uses only the input tables; ground_truth is read afterwards, only to score
     the detectors (precision/recall) and to prove every finding is a labelled one.
Exit code 0 only if A passes and B has no unexplained findings and no missed labels.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R   # noqa: E402
import schema as S  # noqa: E402

DT = "%Y-%m-%dT%H:%M:%S"


def load(data):
    T = {}
    for name in S.T:
        with open(f"{data}/csv/{name}.csv", newline="", encoding="utf-8") as fh:
            T[name] = list(csv.DictReader(fh))
    return T


def conv(v, typ):
    if v == "":
        return None
    if typ == "int":
        return int(v)
    if typ == "float":
        return float(v)
    if typ == "bool":
        if v not in ("true", "false"):
            raise ValueError(v)
        return v == "true"
    if typ == "date":
        return datetime.strptime(v, "%Y-%m-%d").date()
    if typ == "datetime":
        return datetime.strptime(v, DT)
    return v


class Report:
    def __init__(self):
        self.checks = []

    def add(self, group, name, failures, total=None):
        self.checks.append(dict(group=group, check=name, failures=len(failures), examined=total,
                                passed=not failures, examples=[str(x) for x in failures[:5]]))


def structural(T, rep):
    typed = {}
    # --- types / required / enums / patterns / uniqueness / PK
    for name, t in S.T.items():
        bad_type, bad_req, bad_enum, bad_pat, rows = [], [], [], [], []
        for i, r in enumerate(T[name], 2):
            row = {}
            for f in t["fields"]:
                raw = r[f["name"]]
                if raw == "":
                    if f["required"]:
                        bad_req.append(f"{name}:{i}:{f['name']}")
                    row[f["name"]] = None
                    continue
                try:
                    v = conv(raw, f["type"])
                except Exception:
                    bad_type.append(f"{name}:{i}:{f['name']}={raw}")
                    row[f["name"]] = None
                    continue
                if f["allowed"] and v not in f["allowed"]:
                    bad_enum.append(f"{name}:{i}:{f['name']}={v}")
                if f["pattern"] and not re.match(f["pattern"], str(v)):
                    bad_pat.append(f"{name}:{i}:{f['name']}={v}")
                row[f["name"]] = v
            rows.append(row)
        typed[name] = rows
        n = len(rows)
        rep.add("A", f"{name}: types parse", bad_type, n)
        rep.add("A", f"{name}: required fields present", bad_req, n)
        rep.add("A", f"{name}: enum values allowed", bad_enum, n)
        rep.add("A", f"{name}: ID pattern", bad_pat, n)
        seen, dup = set(), []
        for r in rows:
            k = r[t["pk"]]
            (dup.append(k) if k in seen else seen.add(k))
        rep.add("A", f"{name}: primary key unique", dup, n)
        for f in t["fields"]:
            if f["unique"] and f["name"] != t["pk"]:
                vals = [r[f["name"]] for r in rows if r[f["name"]] is not None]
                rep.add("A", f"{name}.{f['name']}: unique", [v for v in set(vals) if vals.count(v) > 1] if len(vals) < 3000 else
                        _dups(vals), len(vals))
        for u in t["unique"]:
            if len(u) > 1:
                ks = [tuple(r[c] for c in u) for r in rows]
                rep.add("A", f"{name}: unique {u}", _dups(ks), n)
    # --- foreign keys
    for name, t in S.T.items():
        for f in t["fields"]:
            if f["fk"]:
                tt, cc = f["fk"].split(".")
                keys = {r[cc] for r in typed[tt]}
                bad = [f"{r[t['pk']]}->{r[f['name']]}" for r in typed[name]
                       if r[f["name"]] is not None and r[f["name"]] not in keys]
                rep.add("A", f"FK {name}.{f['name']} -> {f['fk']}", bad, len(typed[name]))
    # polymorphic references (entity_id by entity_type, actor_id by actor_type)
    pk_sets = {"SimilarityReport": {r["similarity_id"] for r in typed["similarity_reports"]},
               "Case": {r["case_id"] for r in typed["cases"]},
               "EvidenceItem": {r["evidence_id"] for r in typed["evidence_items"]},
               "Appeal": {r["appeal_id"] for r in typed["appeals"]}}
    revs = {r["reviewer_id"] for r in typed["reviewers"]}
    lrns = {r["learner_id"] for r in typed["learners"]}
    rep.add("A", "FK state_events.entity_id by entity_type",
            [e["event_id"] for e in typed["state_events"] if e["entity_id"] not in pk_sets[e["entity_type"]]],
            len(typed["state_events"]))
    for tbl, tcol, acol in [("state_events", "actor_type", "actor_id"), ("evidence_items", "added_by_actor_type", "added_by_actor_id")]:
        bad = []
        for r in typed[tbl]:
            at, ai = r[tcol], r[acol]
            if (at == "system") != (ai is None) or (at == "reviewer" and ai not in revs) or (at == "learner" and ai not in lrns):
                bad.append(r[S.T[tbl]["pk"]])
        rep.add("A", f"FK {tbl}.{acol} by {tcol}", bad, len(typed[tbl]))
    return typed


def _dups(vals):
    seen, d = set(), set()
    for v in vals:
        (d.add(v) if v in seen else seen.add(v))
    return sorted(map(str, d))


def reconcile(X, rep, snap):
    sub = {r["submission_id"]: r for r in X["submissions"]}
    asm = {r["assessment_id"]: r for r in X["assessments"]}
    sim = {r["similarity_id"]: r for r in X["similarity_reports"]}
    cas = {r["case_id"]: r for r in X["cases"]}
    rules = {r["rule_id"]: r for r in X["integrity_rules"]}
    dec = {r["decision_id"]: r for r in X["decisions"]}
    # --- date ordering
    bad = []
    for r in X["assessments"]:
        if r["opens_at"] > r["due_date"]:
            bad.append(r["assessment_id"])
    for r in X["reviewers"]:
        if r["active_to"] and r["active_to"] < r["active_from"]:
            bad.append(r["reviewer_id"])
    for r in X["integrity_rules"]:
        if r["effective_to"] and r["effective_to"] < r["effective_from"]:
            bad.append(r["rule_id"])
    for r in X["submissions"]:
        a = asm[r["assessment_id"]]
        if r["is_late"] != (r["submitted_at"] > datetime.combine(a["due_date"], datetime.min.time()).replace(hour=23, minute=59, second=59)):
            bad.append(f"{r['submission_id']} is_late")
    for r in X["similarity_reports"]:
        if r["generated_at"] < sub[r["submission_id"]]["submitted_at"]:
            bad.append(r["similarity_id"])
    for r in X["cases"]:
        s = sim[r["similarity_id"]]
        if r["opened_at"] < s["generated_at"] or (r["decided_at"] and r["decided_at"] < r["opened_at"]) or \
                (r["closed_at"] and r["decided_at"] and r["closed_at"] < r["decided_at"]):
            bad.append(r["case_id"])
    for r in X["case_reviewers"]:
        if r["assigned_at"] < cas[r["case_id"]]["opened_at"] or (r["recommended_at"] and r["recommended_at"] < r["assigned_at"]):
            bad.append(r["assignment_id"])
    for r in X["evidence_items"]:
        if r["added_at"] < cas[r["case_id"]]["opened_at"]:
            bad.append(r["evidence_id"])
    for r in X["decisions"]:
        if r["decided_at"] < cas[r["case_id"]]["opened_at"]:
            bad.append(r["decision_id"])
    for r in X["appeals"]:
        d = dec[r["original_decision_id"]]
        if r["filed_at"] <= d["decided_at"] or r["filed_at"] > d["decided_at"] + timedelta(days=R.APPEAL_WINDOW_DAYS):
            bad.append(f"{r['appeal_id']} outside window")
        if r["resolved_at"] and r["resolved_at"] < r["filed_at"]:
            bad.append(r["appeal_id"])
    for r in X["state_events"]:
        if r["event_at"] > snap:
            bad.append(r["event_id"])
    rep.add("A", "date ordering and snapshot cut-off", bad)
    # --- scores and rule application
    bad_a, bad_r, bad_cur = [], [], []
    for r in X["similarity_reports"]:
        if abs(max(0.0, r["raw_score"] - r["quoted_match_score"] - r["template_match_score"]) - r["adjusted_score"]) > 1.5e-4 \
                or not (0 <= r["adjusted_score"] <= r["raw_score"] <= 1.0):
            bad_a.append(r["similarity_id"])
        rule = R.classify(r["adjusted_score"], r["generated_at"].date(), list(rules.values()))
        if rule["rule_id"] != r["rule_id"] or rule["action"] != r["recommended_action"] \
                or r["flagged"] != (rule["action"] != "no_action"):
            bad_r.append(r["similarity_id"])
    cur = {}
    for r in X["similarity_reports"]:
        if r["is_current"]:
            cur[r["submission_id"]] = cur.get(r["submission_id"], 0) + 1
    bad_cur = [s for s in sub if cur.get(s, 0) != 1]
    rep.add("A", "adjusted_score = raw - quoted - template", bad_a, len(X["similarity_reports"]))
    rep.add("A", "rule_id/action/flagged follow thresholds effective at scan date", bad_r, len(X["similarity_reports"]))
    rep.add("A", "exactly one current report per submission", bad_cur, len(sub))
    rep.add("A", "no rule permits automatic guilt", [r["rule_id"] for r in X["integrity_rules"] if r["auto_guilt_permitted"]])
    rep.add("A", "similarity_id = SIM-<submission_id>-<version>",
            [r["similarity_id"] for r in X["similarity_reports"] if r["similarity_id"] != f"SIM-{r['submission_id']}-{r['report_version']:02d}"])
    rep.add("A", "evidence/decision/appeal IDs embed their case ID",
            [r["evidence_id"] for r in X["evidence_items"] if not r["evidence_id"].startswith(f"EVD-{r['case_id']}-")] +
            [r["decision_id"] for r in X["decisions"] if not r["decision_id"].startswith(f"DEC-{r['case_id']}-")] +
            [r["appeal_id"] for r in X["appeals"] if r["appeal_id"] != f"APL-{r['case_id']}-01"])
    # --- case derived fields
    rc, ec, st = {}, {}, {}
    for r in X["case_reviewers"]:
        rc[r["case_id"]] = rc.get(r["case_id"], 0) + 1
    for r in X["evidence_items"]:
        ec[r["case_id"]] = ec.get(r["case_id"], 0) + 1
    evts = {}
    for e in X["state_events"]:
        evts.setdefault((e["entity_type"], e["entity_id"]), []).append(e)
    bad = []
    for c in X["cases"]:
        cid = c["case_id"]
        s = sim[c["similarity_id"]]
        if c["submission_id"] != s["submission_id"] or c["opened_by_rule_id"] != s["rule_id"] \
                or c["reviewers_required"] != rules[s["rule_id"]]["reviewers_required"]:
            bad.append(f"{cid} link")
        if c["reviewer_count"] != rc.get(cid, 0) or c["evidence_count"] != ec.get(cid, 0):
            bad.append(f"{cid} counts")
        if c["status"] != max(evts[("Case", cid)], key=lambda e: (e["event_at"], e["event_id"]))["to_state"]:
            bad.append(f"{cid} status")
        if c["sla_due_at"] != c["opened_at"] + timedelta(days=R.SLA_DAYS) or \
                c["sla_breached"] != ((c["decided_at"] or snap) > c["sla_due_at"]):
            bad.append(f"{cid} sla")
        if s["flagged"] is False:
            bad.append(f"{cid} unflagged")
    rep.add("A", "case derived fields reconcile to source rows", bad, len(X["cases"]))
    bad = []
    byc = {}
    for d in X["decisions"]:
        byc.setdefault(d["case_id"], []).append(d)
    for d in X["decisions"]:
        if not d["rationale"] or not d["rationale"].strip():
            bad.append(f"{d['decision_id']} rationale")
        n_ev = sum(1 for e in X["evidence_items"] if e["case_id"] == d["case_id"] and e["added_at"] <= d["decided_at"])
        if n_ev != d["evidence_count_at_decision"]:
            bad.append(f"{d['decision_id']} evidence_count")
        if d["decision_stage"] == "initial":
            rs = [r for r in X["case_reviewers"] if r["case_id"] == d["case_id"] and r["recommendation"]]
            if d["votes_total"] != len(rs) or d["votes_violation"] != sum(r["recommendation"] == "violation" for r in rs):
                bad.append(f"{d['decision_id']} votes")
        elif d["supersedes_decision_id"] not in dec:
            bad.append(f"{d['decision_id']} supersedes")
    for cid, ds in byc.items():
        if sum(1 for d in ds if d["decision_stage"] == "initial") != 1:
            bad.append(f"{cid} initial decisions")
    rep.add("A", "decisions: rationale present, votes/evidence counts reconcile, one initial per case", bad, len(X["decisions"]))
    bad = []
    for a in X["appeals"]:
        d = dec[a["original_decision_id"]]
        if d["case_id"] != a["case_id"] or d["outcome"] not in S.VIOLATION_OUTCOMES:
            bad.append(f"{a['appeal_id']} appeals non-adverse/foreign decision")
        if a["outcome"] in ("overturned", "reduced") and a["resulting_decision_id"] not in dec:
            bad.append(f"{a['appeal_id']} missing resulting decision")
        if a["status"] != evts[("Appeal", a["appeal_id"])][-1]["to_state"]:
            bad.append(f"{a['appeal_id']} status")
    rep.add("A", "appeals reference adverse decisions of the same case; outcomes have decisions", bad, len(X["appeals"]))
    cst = {c["submission_id"]: c for c in X["cases"]}
    bad = []
    cur_sim = {r["submission_id"]: r for r in X["similarity_reports"] if r["is_current"]}
    for s in X["submissions"]:
        c, f = cst.get(s["submission_id"]), cur_sim[s["submission_id"]]
        if c is None:
            exp = "flag_closed" if f["flag_status"] == "triaged_closed" else "not_flagged"
        elif c["status"] != "closed":
            exp = "case_in_progress"
        else:
            exp = "sanctioned" if c["final_outcome"] in S.VIOLATION_OUTCOMES else "cleared"
        if s["integrity_status"] != exp:
            bad.append(s["submission_id"])
    rep.add("A", "submission.integrity_status derived consistently", bad, len(X["submissions"]))
    # --- audit-history completeness (evidence events are checked in the process group: an anomaly targets them)
    bad = []
    for r in X["similarity_reports"]:
        es = evts.get(("SimilarityReport", r["similarity_id"]), [])
        if not es or es[0]["to_state"] != "generated" or (r["flagged"] and r["is_current"] and not any(e["to_state"] == "flagged" for e in es)):
            bad.append(r["similarity_id"])
    for c in X["cases"]:
        es = evts.get(("Case", c["case_id"]), [])
        if not es or es[0]["to_state"] != "opened" or es[0]["event_at"] != c["opened_at"]:
            bad.append(c["case_id"])
        if not any(e["entity_type"] == "SimilarityReport" and e["to_state"] == "case_opened" for e in evts.get(("SimilarityReport", c["similarity_id"]), [])):
            bad.append(f"{c['case_id']} flag history lacks case_opened")
    for a in X["appeals"]:
        if not any(e["to_state"] == "filed" and e["event_at"] == a["filed_at"] for e in evts.get(("Appeal", a["appeal_id"]), [])):
            bad.append(a["appeal_id"])
    for d in X["decisions"]:
        want = "decided" if d["decision_stage"] == "initial" else "closed"
        if not any(e["to_state"] == want and e["event_at"] == d["decided_at"] for e in evts.get(("Case", d["case_id"]), [])):
            bad.append(d["decision_id"])
    rep.add("A", "audit history complete: creation/filing/decision events exist and match record timestamps", bad)
    return evts


def sql_check(data, X, rep):
    con = sqlite3.connect(":memory:")
    con.executescript(open(f"{data}/sql/schema.sql", encoding="utf-8").read())
    con.executescript(open(f"{data}/sql/seed.sql", encoding="utf-8").read())
    con.execute("PRAGMA foreign_keys=ON")
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    rep.add("A", "SQL seed loads; PRAGMA foreign_key_check clean", fk)
    bad = [n for n in S.T if con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] != len(X[n])]
    rep.add("A", "SQL row counts equal CSV row counts", bad)
    con.close()


# ------------------------------------------------------- process checks (B)
def process(X, evts, rep):
    sim = {r["similarity_id"]: r for r in X["similarity_reports"]}
    cas = {r["case_id"]: r for r in X["cases"]}
    sub = {r["submission_id"]: r for r in X["submissions"]}
    asm = {r["assessment_id"]: r for r in X["assessments"]}
    conflicts = {(r["reviewer_id"], r["learner_id"]) for r in X["reviewer_conflicts"]}
    init = {d["case_id"]: d for d in X["decisions"] if d["decision_stage"] == "initial"}
    crev = {}
    for r in X["case_reviewers"]:
        crev.setdefault(r["case_id"], []).append(r)
    ev_events = {e["entity_id"] for e in X["state_events"] if e["entity_type"] == "EvidenceItem"}

    # lifecycle transitions + monotonic time, for every entity
    life = {}
    for (et, eid), es in evts.items():
        es = sorted(es, key=lambda e: (e["event_at"], e["event_id"]))
        prev = None
        for e in es:
            if e["from_state"] != prev or e["to_state"] not in S.TRANSITIONS[et].get(prev, set()):
                life.setdefault(eid, []).append(f"{et}:{prev}->{e['to_state']}")
            prev = e["to_state"]
    life_cases = {k for k in life if k in cas}
    rep.add("B", "lifecycle: all transitions allowed (illegal ones listed)", [f"{k}:{v}" for k, v in life.items()], len(evts))

    found = {"flag_auto_guilt": set(), "reviewer_conflict": set(), "evidence_added_after_decision_no_history": set(),
             "appeal_closed_without_independent_review": set()}
    for cid, d in init.items():
        if d["decision_basis"] == "auto_threshold" or d["decided_by"] is None or cid not in crev or cid in life_cases:
            found["flag_auto_guilt"].add(cid)
    for cid, rs in crev.items():
        s = sub[cas[cid]["submission_id"]]
        ins = asm[s["assessment_id"]]["instructor_id"]
        for r in rs:
            if (r["reviewer_id"], s["learner_id"]) in conflicts or r["reviewer_id"] == ins:
                found["reviewer_conflict"].add(cid)
    for e in X["evidence_items"]:
        d = init.get(e["case_id"])
        if e["evidence_stage"] != "appeal" and (e["evidence_id"] not in ev_events or (d and e["added_at"] > d["decided_at"])):
            found["evidence_added_after_decision_no_history"].add(e["case_id"])
        if e["evidence_stage"] == "appeal" and e["evidence_id"] not in ev_events:
            found["evidence_added_after_decision_no_history"].add(e["case_id"])
    for a in X["appeals"]:
        if a["outcome"] in ("upheld", "overturned", "reduced"):
            on_case = {r["reviewer_id"] for r in crev.get(a["case_id"], [])}
            s = sub[cas[a["case_id"]]["submission_id"]]
            if (a["appeal_reviewer_id"] is None or a["appeal_reviewer_id"] in on_case or not a["independent_review_completed"]
                    or (a["appeal_reviewer_id"], s["learner_id"]) in conflicts):
                found["appeal_closed_without_independent_review"].add(a["case_id"])
    return found, life_cases


def score(found, life_cases, data, rep):
    gt = list(csv.DictReader(open(f"{data}/ground_truth/ground_truth.csv", newline="", encoding="utf-8")))
    labelled = {}
    for g in gt:
        if g["issue_type"]:
            labelled.setdefault(g["issue_type"], set()).add(g["case_id"])
    out = {}
    for k in found:
        tp, fp, fn = found[k] & labelled.get(k, set()), found[k] - labelled.get(k, set()), labelled.get(k, set()) - found[k]
        out[k] = dict(labelled=len(labelled.get(k, set())), detected=len(found[k]), true_pos=len(tp),
                      false_pos=sorted(fp), false_neg=sorted(fn),
                      precision=round(len(tp) / len(found[k]), 3) if found[k] else None,
                      recall=round(len(tp) / len(labelled[k]), 3) if labelled.get(k) else None)
        rep.add("B", f"detector '{k}': no unexplained findings, no missed labels", sorted(fp) + sorted(fn),
                len(labelled.get(k, set())))
    all_lab = set().union(*labelled.values()) if labelled else set()
    rep.add("B", "every illegal lifecycle transition belongs to a labelled anomaly", sorted(life_cases - all_lab))
    return out, gt


def distributions(X, gt):
    from collections import Counter
    sims = [r for r in X["similarity_reports"] if r["is_current"]]
    flagged = [r for r in sims if r["flagged"]]
    cases = X["cases"]
    d = dict(
        submissions=len(X["submissions"]), current_reports=len(sims), flags=len(flagged), cases=len(cases),
        flag_rate=round(len(flagged) / len(sims), 4),
        flags_by_action=dict(Counter(r["recommended_action"] for r in flagged)),
        boundary_scores=dict(at_0_25=sum(r["adjusted_score"] == 0.25 for r in sims),
                             at_0_50=sum(r["adjusted_score"] == 0.5 for r in sims),
                             at_0_75=sum(r["adjusted_score"] == 0.75 for r in sims),
                             just_below_0_25=sum(r["adjusted_score"] == 0.2499 for r in sims)),
        raw_high_but_not_flagged=sum(1 for r in sims if not r["flagged"] and r["raw_score"] >= 0.25),
        case_status=dict(Counter(c["status"] for c in cases)),
        case_final_outcome=dict(Counter(c["final_outcome"] or "undecided" for c in cases)),
    )
    d["cases_with_multiple_reviewers"] = sum(1 for c in cases if c["reviewer_count"] >= 2)
    d["cases_with_tiebreak"] = sum(1 for r in X["case_reviewers"] if r["assignment_role"] == "tiebreak")
    d["appeals"] = dict(Counter(a["outcome"] or "pending" for a in X["appeals"]))
    d["successful_appeals"] = sum(1 for a in X["appeals"] if a["outcome"] in ("overturned", "reduced"))
    d["sla_breached_cases"] = sum(1 for c in cases if c["sla_breached"])
    d["latent_class_of_flags"] = dict(Counter(g["latent_class"] for g in gt))
    exp = {g["case_id"]: g["expected_outcome"] for g in gt if g["case_id"]}
    inc = [c for c in cases if c["final_outcome"] and c["final_outcome"] != exp[c["case_id"]]]
    d["cases_whose_final_outcome_differs_from_expected"] = len(inc)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="docs")
    a = ap.parse_args()
    rep = Report()
    T = load(a.data)
    X = structural(T, rep)
    if any(not c["passed"] for c in rep.checks):
        # keys/types are broken: later checks would crash on dangling references, so stop with a clear report
        for c in rep.checks:
            if not c["passed"]:
                print("FAIL", c["group"], c["check"], c["failures"], c["examples"])
        print("Stopped after structural failures; fix keys/types first.")
        sys.exit(1)
    evts = reconcile(X, rep, R.SNAPSHOT)
    sql_check(a.data, X, rep)
    found, life_cases = process(X, evts, rep)
    det, gt = score(found, life_cases, a.data, rep)
    dist = distributions(X, gt)
    A = [c for c in rep.checks if c["group"] == "A"]
    B = [c for c in rep.checks if c["group"] == "B" and not c["check"].startswith("lifecycle")]
    summary = dict(structural_checks=len(A), structural_failed=sum(not c["passed"] for c in A),
                   process_checks=len(B), process_failed=sum(not c["passed"] for c in B),
                   detectors=det, distributions=dist, checks=rep.checks)
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/validation_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2, default=str)
        fh.write("\n")
    with open(f"{a.out}/validation_summary.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Validation summary\n\n")
        fh.write(f"- Structural checks (A): **{summary['structural_checks'] - summary['structural_failed']}/{summary['structural_checks']} passed**\n")
        fh.write(f"- Process checks (B): **{summary['process_checks'] - summary['process_failed']}/{summary['process_checks']} passed**\n\n")
        fh.write("## Anomaly detectors vs ground truth\n\n| issue_type | labelled | detected | precision | recall |\n|---|---|---|---|---|\n")
        for k, v in det.items():
            fh.write(f"| {k} | {v['labelled']} | {v['detected']} | {v['precision']} | {v['recall']} |\n")
        fh.write("\n## Distributions\n\n```json\n" + json.dumps(dist, indent=2) + "\n```\n\n## All checks\n\n| Group | Check | Examined | Failures |\n|---|---|---|---|\n")
        for c in rep.checks:
            fh.write(f"| {c['group']} | {c['check']} | {c['examined'] if c['examined'] is not None else ''} | {c['failures']} {'✅' if c['passed'] else '❌'} |\n")
    print(f"A structural: {summary['structural_checks'] - summary['structural_failed']}/{summary['structural_checks']} passed")
    print(f"B process   : {summary['process_checks'] - summary['process_failed']}/{summary['process_checks']} passed")
    for k, v in det.items():
        print(f"  {k}: labelled={v['labelled']} detected={v['detected']} precision={v['precision']} recall={v['recall']}")
    for c in rep.checks:
        if not c["passed"] and not c["check"].startswith("lifecycle"):
            print("FAIL", c["group"], c["check"], c["failures"], c["examples"])
    ok = summary["structural_failed"] == 0 and summary["process_failed"] == 0
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
