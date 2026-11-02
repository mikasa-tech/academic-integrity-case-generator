#!/usr/bin/env python3
"""Build dashboard/index.html: one self-contained file embedding the dataset (no server, no internet).

    python src/build_dashboard.py --data data
Anomaly flags shown in the UI come from the validator's detectors (input tables only); the ground-truth
answer key is embedded separately and stays hidden until the viewer clicks "Reveal answer key".
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as V, rules as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data"); ap.add_argument("--out", default="dashboard/index.html")
    a = ap.parse_args()
    rd = lambda n: list(csv.DictReader(open(f"{a.data}/csv/{n}.csv", encoding="utf-8")))
    rep = V.Report(); X = V.structural(V.load(a.data), rep); evts = V.reconcile(X, rep, R.SNAPSHOT); V.sql_check(a.data, X, rep)
    found, life = V.process(X, evts, rep); det, _gt = V.score(found, life, a.data, rep)
    flagged_by = {}
    for k, ids in found.items():
        for c in ids: flagged_by.setdefault(c, []).append(k)
    gt = {g["case_id"]: g["issue_type"] for g in csv.DictReader(open(f"{a.data}/ground_truth/ground_truth.csv", encoding="utf-8")) if g["issue_type"]}
    A = [c for c in rep.checks if c["group"] == "A"]; B = [c for c in rep.checks if c["group"] == "B" and not c["check"].startswith("lifecycle")]
    cur = [r for r in rd("similarity_reports") if r["is_current"] == "true"]
    reports = [[float(r["raw_score"]), float(r["adjusted_score"])] for r in cur]
    by = lambda rows, k: {} if not rows else {x: [r for r in rows if r[k] == x] for x in dict.fromkeys(r[k] for r in rows)}
    sim = {r["similarity_id"]: r for r in cur}
    crev, evd, dec, apl = by(rd("case_reviewers"), "case_id"), by(rd("evidence_items"), "case_id"), by(rd("decisions"), "case_id"), {r["case_id"]: r for r in rd("appeals")}
    ev = {}
    for e in rd("state_events"): ev.setdefault(e["entity_id"], []).append(e)
    cases = []
    for c in rd("cases"):
        cid = c["case_id"]; s = sim[c["similarity_id"]]
        ids = [cid, c["similarity_id"]] + [e["evidence_id"] for e in evd.get(cid, [])] + ([apl[cid]["appeal_id"]] if cid in apl else [])
        tl = sorted((e for i in ids for e in ev.get(i, [])), key=lambda e: (e["event_at"], e["event_id"]))
        cases.append(dict(id=cid, sub=c["submission_id"], score=float(s["adjusted_score"]), raw=float(s["raw_score"]), action=s["recommended_action"],
            status=c["status"], opened=c["opened_at"], outcome=c["final_outcome"], sla=c["sla_breached"] == "true", flags=flagged_by.get(cid, []), key=gt.get(cid, ""),
            rev=[[r["reviewer_id"], r["assignment_role"], r["recommendation"], r["conflict_checked"]] for r in crev.get(cid, [])],
            evd=[[e["evidence_id"][-3:], e["evidence_type"], e["added_at"], e["evidence_stage"]] for e in evd.get(cid, [])],
            dec=[[d["decision_stage"], d["outcome"], d["rationale"], d["decided_at"], d["decision_basis"]] for d in dec.get(cid, [])],
            apl=[apl[cid]["grounds"], apl[cid]["outcome"] or "pending", apl[cid]["appeal_reviewer_id"] or "none", apl[cid]["independent_review_completed"]] if cid in apl else None,
            tl=[[e["event_at"], e["entity_type"], e["to_state"], e["note"]] for e in tl]))
    counts = {k: len(rd(k)) for k in V.S.T}
    data = dict(reports=reports, cases=cases, counts=counts, det=det,
                checks=[len(A), sum(not c["passed"] for c in A), len(B), sum(not c["passed"] for c in B)],
                manifest=json.load(open(f"{a.data}/manifest.json")))
    html = open("dashboard/template.html", encoding="utf-8").read().replace("__DATA__", json.dumps(data, separators=(",", ":")))
    open(a.out, "w", encoding="utf-8", newline="\n").write(html); print(f"wrote {a.out} ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
