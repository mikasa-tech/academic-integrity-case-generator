#!/usr/bin/env python3
"""Synthetic academic-integrity case dataset generator.

    python src/generate.py --seed 20261022 --scale 1.0 --out data

Pipeline (see README for the reasoning):
  1. master data  : reviewers, learners, conflict registry, assessments, rules
  2. submissions  : learner x assessment pairs
  3. similarity   : synthetic reports; a *latent cause* is drawn for flagged ones
  4. cases        : opened by rule; reviewers, evidence, votes, decisions, appeals simulated
                    as time-ordered events; later stages are cut at the snapshot date
  5. anomalies    : four labelled edge cases injected AFTER the clean baseline
  6. derivation   : all derived columns recomputed from source rows
  7. export       : CSV / JSON / SQL / ground truth / dictionary / manifest / checksums

All randomness comes from one random.Random(seed); no wall-clock time is read, so
the same seed + scale gives byte-identical output.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R          # noqa: E402
import schema as S         # noqa: E402

FIRST = ["Aarav", "Meera", "Rohan", "Ananya", "Kabir", "Isha", "Vikram", "Diya", "Arjun", "Nisha",
         "Liam", "Olivia", "Noah", "Emma", "Lucas", "Sofia", "Mateo", "Amara", "Kofi", "Zara",
         "Yuki", "Hana", "Wei", "Mei", "Omar", "Layla", "Tariq", "Fatima", "Ivan", "Elena",
         "Pierre", "Chloe", "Hugo", "Greta", "Jonas", "Priya", "Sanjay", "Tara", "Dev", "Rhea"]
LAST = ["Sharma", "Patel", "Nair", "Reddy", "Khan", "Gupta", "Iyer", "Singh", "Das", "Mehta",
        "Smith", "Johnson", "Brown", "Garcia", "Martinez", "Okafor", "Mensah", "Adeyemi", "Tanaka", "Sato",
        "Chen", "Wang", "Kim", "Park", "Haddad", "Nasser", "Petrov", "Novak", "Dubois", "Laurent",
        "Muller", "Schmidt", "Rossi", "Bianchi", "Silva", "Costa", "Lopez", "Fernandez", "Bose", "Kulkarni"]
SRC = {
    "genuine": [("student_paper_repository", 3), ("web_page", 3), ("published_work", 2)],
    "legit_quote": [("published_work", 5), ("web_page", 3)],
    "shared_template": [("internal_template", 8), ("student_paper_repository", 1)],
    "false_positive": [("web_page", 5), ("institutional_repository", 3), ("published_work", 1)],
    None: [("web_page", 5), ("published_work", 2), ("student_paper_repository", 2), ("institutional_repository", 1)],
}
EVD_DESC = {
    "similarity_report_excerpt": "Machine-generated excerpt of the flagged similarity report.",
    "source_match": "Side-by-side comparison of submission text against a matched source.",
    "citation_check": "Check of whether matched passages carry quotation marks and citations.",
    "template_comparison": "Comparison of overlap against the shared assessment template.",
    "draft_history": "Version history of the learner's drafts showing how the text evolved.",
    "instructor_note": "Instructor's note on the assessment brief and expected sources.",
    "learner_statement": "Written statement from the learner supporting the appeal.",
}
EVD_BY_LATENT = {
    "genuine": ["source_match", "source_match", "draft_history", "instructor_note"],
    "legit_quote": ["citation_check", "source_match", "instructor_note"],
    "shared_template": ["template_comparison", "source_match", "instructor_note"],
    "false_positive": ["source_match", "citation_check", "draft_history"],
}


# ------------------------------------------------------------------ helpers
def tadd(dt, **kw):
    """datetime + timedelta, truncated to whole seconds (keeps output deterministic and tidy)."""
    return (dt + timedelta(**kw)).replace(microsecond=0)


def wchoice(rng, pairs):
    tot = sum(w for _, w in pairs)
    x = rng.random() * tot
    acc = 0
    for v, w in pairs:
        acc += w
        if x < acc:
            return v
    return pairs[-1][0]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def jsonable(v):
    if isinstance(v, (datetime, date)):
        return fmt(v)
    if isinstance(v, float):
        return round(v, 4)
    return v


def sqlval(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        return f"{v:.4f}"
    return "'" + fmt(v).replace("'", "''") + "'"


# ----------------------------------------------------------------- generator
def generate(seed=20261022, scale=1.0):
    rng = random.Random(seed)
    SNAP = R.SNAPSHOT
    n_sub = max(100, round(10000 * scale))
    n_flag = round(1000 * scale)
    n_case = round(300 * scale)
    n_ref = round(R.REFERRED_SHARE_OF_FLAGS * n_flag)
    n_pe = n_case - n_ref
    n_esc = round(R.ESCALATION_SHARE_OF_PRIORITY_AND_ESCALATION * n_pe)
    n_pri = n_pe - n_esc
    assert 0 < n_case <= n_flag <= n_sub, "scale too small for the requested ratios"

    events = []                       # appended in generation order; ids assigned at the very end
    seq = [0]

    def ev(etype, eid, frm, to, at, atype, aid, note=None):
        seq[0] += 1
        events.append(dict(_seq=seq[0], event_id=None, entity_type=etype, entity_id=eid, from_state=frm,
                           to_state=to, event_at=at, actor_type=atype, actor_id=aid, note=note))

    def person():
        return f"{rng.choice(FIRST)} {rng.choice(LAST)}"

    # ---- 1. master data ---------------------------------------------------
    n_instr, n_admin = max(6, round(20 * scale)), max(6, round(10 * scale))
    n_sup, n_plat = max(3, round(6 * scale)), 2
    reviewers = []
    for role, n in zip(S.ROLES, [n_instr, n_admin, n_sup, n_plat]):
        for _ in range(n):
            rid = f"REV-{len(reviewers) + 1:04d}"
            nm = person()
            at = None
            if role in ("instructor", "academic_administrator") and rng.random() < 0.07:
                at = date(2026, 3, 1) + timedelta(days=rng.randint(0, 150))
            reviewers.append(dict(
                reviewer_id=rid, full_name=nm, email=f"{nm.lower().replace(' ', '.')}.{rid.lower()}@example.edu",
                role=role, department=rng.choice(S.DEPARTMENTS),
                active_from=date(2023, 1, 1) + timedelta(days=rng.randint(0, 900)), active_to=at))
    rev_by_id = {r["reviewer_id"]: r for r in reviewers}

    n_l = max(40, round(2500 * scale))
    learners = []
    for i in range(n_l):
        lid, nm, cy = f"LRN-{i + 1:06d}", person(), rng.randint(2022, 2025)
        learners.append(dict(
            learner_id=lid, full_name=nm, email=f"{nm.lower().replace(' ', '.')}.{lid.lower()}@example.edu",
            programme=rng.choice(S.PROGRAMMES), cohort_year=cy,
            enrolled_date=date(cy, 9, 1) + timedelta(days=rng.randint(0, 14))))
    lrn_by_id = {l["learner_id"]: l for l in learners}

    staff = [r for r in reviewers if r["role"] in ("instructor", "academic_administrator")]
    conflicts, conflict_set = [], set()
    for l in learners:
        if rng.random() < 0.08:
            r = rng.choice(staff)
            conflicts.append(dict(conflict_id=f"CNF-{len(conflicts) + 1:05d}", reviewer_id=r["reviewer_id"],
                                  learner_id=l["learner_id"], conflict_type=rng.choice(S.CONFLICT_TYPES),
                                  declared_at=date(2025, 1, 1) + timedelta(days=rng.randint(0, 500))))
            conflict_set.add((r["reviewer_id"], l["learner_id"]))

    n_a = max(8, round(160 * scale))
    instructors = [r for r in reviewers if r["role"] == "instructor"]
    dues = sorted(date(2026, 1, 20) + timedelta(days=rng.randint(0, 263)) for _ in range(n_a))  # to 10 Oct
    assessments = []
    for i, due in enumerate(dues):
        typ = rng.choice(S.ASSESS_TYPES)
        cand = [r for r in instructors if r["active_from"] <= due and (r["active_to"] is None or r["active_to"] >= due)]
        ins = rng.choice(cand)
        assessments.append(dict(
            assessment_id=f"ASM-2026-{i + 1:04d}", course_code=f"{ins['department'][:3].upper()}{rng.randint(100, 499)}",
            title=f"{typ.replace('_', ' ').title()} {i + 1}", assessment_type=typ, instructor_id=ins["reviewer_id"],
            opens_at=due - timedelta(days=rng.randint(14, 42)), due_date=due,
            word_limit=rng.choice([1000, 1500, 2000, 3000, 4000]),
            has_shared_template=rng.random() < 0.30, quotation_permitted=rng.random() < 0.85))
    asm_by_id = {a["assessment_id"]: a for a in assessments}

    plat = next(r["reviewer_id"] for r in reviewers if r["role"] == "platform_administrator")
    rule_rows = []

    def addrule(name, typ, action, mn, mx, req, param, frm, to, desc):
        rule_rows.append(dict(
            rule_id=f"INT-2026-{len(rule_rows) + 1:06d}", rule_name=name, rule_type=typ, action=action,
            min_adjusted_score=mn, max_adjusted_score=mx, reviewers_required=req, parameter_value=param,
            effective_from=frm, effective_to=to, created_by=plat, auto_guilt_permitted=False, description=desc))
    d0 = date(2026, 1, 1)
    addrule("Below review threshold", "threshold", "no_action", 0.0, 0.25, None, None, d0, None,
            "Adjusted score under 25%: no action; the report is retained for audit.")
    addrule("Standard review", "threshold", "standard_review", 0.25, 0.50, 1, None, d0, None,
            "25-49%: flagged for triage. A reviewer decides whether to refer to a case. Never automatic guilt.")
    addrule("Priority review", "threshold", "priority_review", 0.50, 0.75, 2, None, d0, None,
            "50-74%: a case is opened and two reviewers must assess independently; a third breaks ties.")
    addrule("Panel escalation", "threshold", "panel_escalation", 0.75, 1.0, 3, None, d0, None,
            "75%+: a case is opened and a three-member panel decides by majority.")
    addrule("Exclude quoted material", "exclusion", "exclude_from_score", None, None, None, None, d0, None,
            "Properly quoted and cited passages are subtracted from the raw score.")
    addrule("Exclude shared template", "exclusion", "exclude_from_score", None, None, None, None, d0, None,
            "Text copied from the shared assessment template is subtracted from the raw score.")
    addrule("Appeal window", "procedural", "procedural_control", None, None, None, float(R.APPEAL_WINDOW_DAYS), d0, None,
            "A learner may appeal an adverse decision within 14 days; cases close when the window lapses.")
    addrule("Independent appeal review", "procedural", "procedural_control", None, None, 1, None, d0, None,
            "Appeals are reviewed by an administrator who sat on neither the case nor has a declared conflict.")
    addrule("Legacy standard review (superseded)", "threshold", "standard_review", 0.30, 0.50, 1, None,
            date(2025, 1, 1), date(2025, 12, 31), "Pre-2026 threshold of 30%; superseded by INT-2026-000002.")
    rules_by_id = {r["rule_id"]: r for r in rule_rows}

    # ---- 2. submissions ---------------------------------------------------
    raw_subs = []
    for p in rng.sample(range(n_l * n_a), n_sub):
        li, ai = divmod(p, n_a)
        a = assessments[ai]
        due_dt = datetime.combine(a["due_date"], datetime.min.time()).replace(hour=23, minute=59, second=59)
        if rng.random() < 0.07:
            sa = tadd(due_dt, hours=rng.uniform(0.1, 48))
        else:
            sa = tadd(due_dt, hours=-min(rng.expovariate(1 / 36), 24 * 14))
        mu = {"essay": 1800, "report": 3000, "coding_assignment": 900, "case_study": 2200, "lab_report": 1500}[a["assessment_type"]]
        raw_subs.append((sa, li, ai, max(300, int(rng.gauss(mu, mu * 0.2)))))
    raw_subs.sort(key=lambda x: (x[0], x[1], x[2]))
    submissions = []
    for i, (sa, li, ai, wc) in enumerate(raw_subs):
        a = assessments[ai]
        due_dt = datetime.combine(a["due_date"], datetime.min.time()).replace(hour=23, minute=59, second=59)
        submissions.append(dict(
            submission_id=f"SUB-2026-{i + 1:06d}", learner_id=learners[li]["learner_id"],
            assessment_id=a["assessment_id"], submitted_at=sa, word_count=wc, is_late=sa > due_dt,
            integrity_status=None))
    sub_by_id = {s["submission_id"]: s for s in submissions}

    # ---- 3. similarity reports -------------------------------------------
    weights = [1.5 if asm_by_id[s["assessment_id"]]["has_shared_template"] else 1.0 for s in submissions]
    keyed = sorted(((rng.random() ** (1.0 / w), i) for i, w in enumerate(weights)), key=lambda x: (-x[0], x[1]))
    flagged_idx = sorted(i for _, i in keyed[:n_flag])
    order = flagged_idx[:]
    rng.shuffle(order)
    band_of = {}
    for j, i in enumerate(order):
        band_of[i] = ("escalate" if j < n_esc else "priority" if j < n_esc + n_pri
                      else "ref" if j < n_esc + n_pri + n_ref else "closed")
    support = [r["reviewer_id"] for r in reviewers if r["role"] == "support_staff"]

    sims, latent_of, band_of_sim = [], {}, {}
    seen_boundary = set()
    plans, closed_triage = [], []
    for i, s in enumerate(submissions):
        a = asm_by_id[s["assessment_id"]]
        has_t = a["has_shared_template"]
        gen_at = tadd(s["submitted_at"], hours=rng.uniform(0.5, 6))
        latent = band = None
        if i in band_of:
            band = band_of[i]
            latent = wchoice(rng, R.LATENT_MIX[band])
            if latent == "shared_template" and not has_t:
                latent = "false_positive"
            lo, hi = R.BAND_RANGE[band]
            force = band not in seen_boundary          # first flag of each band sits exactly on its lower bound
            seen_boundary.add(band)
            adj = lo if (force or rng.random() < R.P_BOUNDARY) else round(rng.uniform(lo, hi), 4)
            if latent == "legit_quote":
                q, t = rng.uniform(0.06, 0.22), (rng.uniform(0.02, 0.10) if has_t else 0.0)
            elif latent == "shared_template":
                q, t = rng.uniform(0.0, 0.05), rng.uniform(0.10, 0.30)
            elif latent == "genuine":
                q, t = (rng.uniform(0.0, 0.06) if rng.random() < 0.5 else 0.0), (rng.uniform(0.02, 0.12) if has_t else 0.0)
            else:
                q, t = rng.uniform(0.0, 0.04), (rng.uniform(0.0, 0.08) if has_t else 0.0)
            q, t = round(q, 4), round(t, 4)
            if adj + q + t > 1.0:                       # keep raw <= 1 while preserving adjusted exactly
                t = round(max(0.0, 1 - adj - q), 4)
                q = round(max(0.0, 1 - adj - t), 4)
        else:
            adj = min(0.2499, round(rng.betavariate(1.6, 8) * 0.45, 4))
            if rng.random() < 0.02:
                adj = 0.2499                            # boundary: just under the review threshold
            q = round(rng.uniform(0.005, 0.06), 4) if rng.random() < 0.15 else 0.0
            t = round(rng.uniform(0.02, 0.20), 4) if (has_t and rng.random() < 0.8) else 0.0
        raw = round(adj + q + t, 4)
        adj_stored = round(max(0.0, raw - q - t), 4)
        rule = R.classify(adj_stored, gen_at.date(), rule_rows)
        if band:
            assert rule["action"] == {"escalate": "panel_escalation", "priority": "priority_review",
                                      "ref": "standard_review", "closed": "standard_review"}[band]
        else:
            assert rule["action"] == "no_action"
        sid = f"SIM-{s['submission_id']}-01"
        sims.append(dict(
            similarity_id=sid, submission_id=s["submission_id"], report_version=1, generated_at=gen_at,
            raw_score=raw, quoted_match_score=q, template_match_score=t, adjusted_score=adj_stored,
            matched_source_count=1 + int(raw * 20) + rng.randint(0, 3), top_source_type=wchoice(rng, SRC[latent]),
            rule_id=rule["rule_id"], recommended_action=rule["action"], flagged=rule["action"] != "no_action",
            is_current=True, flag_status=None))
        ev("SimilarityReport", sid, None, "generated", gen_at, "system", None, "Similarity scan completed")
        if latent:
            latent_of[sid], band_of_sim[sid] = latent, band
            ev("SimilarityReport", sid, "generated", "flagged", tadd(gen_at, seconds=1), "system", None,
               f"Adjusted score {adj_stored:.4f} met {rule['rule_id']}")
            if band == "closed":
                t_tr = tadd(gen_at, hours=rng.uniform(24, 72))
                ev("SimilarityReport", sid, "flagged", "triaged_closed", t_tr, "reviewer", rng.choice(support),
                   "Triage review: no case referral")
            else:
                if band == "ref":
                    t_tr = tadd(gen_at, hours=rng.uniform(24, 72))
                    t_open, actor = tadd(t_tr, hours=rng.uniform(1, 24)), ("reviewer", rng.choice(support))
                else:
                    t_open, actor = tadd(gen_at, hours=rng.uniform(2, 48)), ("system", None)
                plans.append(dict(sim=sims[-1], sub=s, asm=a, latent=latent, band=band, t_open=t_open, actor=actor))
        elif rng.random() < R.P_RESCAN:
            sims[-1]["is_current"] = False
            g2 = tadd(gen_at, days=rng.uniform(1, 5))
            adj2 = min(0.2499, max(0.0, round(adj_stored + rng.gauss(0, 0.01), 4)))
            raw2 = round(adj2 + q + t, 4)
            sid2 = f"SIM-{s['submission_id']}-02"
            sims.append(dict(sims[-1], similarity_id=sid2, report_version=2, generated_at=g2, raw_score=raw2,
                             adjusted_score=round(raw2 - q - t, 4), is_current=True, flag_status=None))
            ev("SimilarityReport", sid2, None, "generated", g2, "system", None, "Rescan completed")
    sim_by_id = {x["similarity_id"]: x for x in sims}

    # ---- 4. cases ---------------------------------------------------------
    plans.sort(key=lambda p: (p["t_open"], p["sim"]["similarity_id"]))
    cases, case_rev, evidence, decisions, appeals = [], [], [], [], []
    ctr = {"crv": 0}
    admins_ids = {r["reviewer_id"] for r in reviewers if r["role"] == "academic_administrator"}

    def pool(roles, at, lid, instr_id, exclude=()):
        return [r["reviewer_id"] for r in reviewers
                if r["role"] in roles and r["active_from"] <= at.date()
                and (r["active_to"] is None or r["active_to"] >= at.date())
                and r["reviewer_id"] not in exclude and r["reviewer_id"] != instr_id
                and (r["reviewer_id"], lid) not in conflict_set]

    for k, p in enumerate(plans, 1):
        cid = f"CSE-2026-{k:06d}"
        sim, sub, a, latent = p["sim"], p["sub"], p["asm"], p["latent"]
        lid, adj, t_open = sub["learner_id"], sim["adjusted_score"], p["t_open"]
        rule = rules_by_id[sim["rule_id"]]
        need = rule["reviewers_required"]
        cases.append(dict(
            case_id=cid, similarity_id=sim["similarity_id"], submission_id=sub["submission_id"],
            opened_by_rule_id=rule["rule_id"], opened_at=t_open, reviewers_required=need, reviewer_count=0,
            evidence_count=0, status=None, decided_at=None, closed_at=None, final_outcome=None,
            sla_due_at=None, sla_breached=None))
        if p["band"] == "ref":
            ev("SimilarityReport", sim["similarity_id"], "flagged", "case_opened", t_open, *p["actor"],
               f"Referred to case {cid} after triage review")
        else:
            ev("SimilarityReport", sim["similarity_id"], "flagged", "case_opened", t_open, "system", None,
               f"Case {cid} opened by rule {rule['rule_id']}")
        ev("Case", cid, None, "opened", t_open, *p["actor"], f"Opened under {rule['rule_id']}")

        ev_rows = []                       # evidence for this case, built then sorted
        eseq = [0]

        def add_evidence(etype, at, atype, aid, stage):
            ev_rows.append(dict(etype=etype, at=at, atype=atype, aid=aid, stage=stage))

        add_evidence("similarity_report_excerpt", tadd(t_open, seconds=5), "system", None, "pre_decision")

        t_asg = tadd(t_open, hours=rng.uniform(4, 48))
        t_rev = tadd(t_asg, hours=rng.uniform(2, 24))
        dur = rng.triangular(3, 26, 9)
        if need == 1:
            chosen = rng.sample(pool(("instructor", "academic_administrator"), t_asg, lid, a["instructor_id"]), 1)
            roles = ["primary"]
        elif need == 2:
            f1 = rng.sample(pool(("instructor",), t_asg, lid, a["instructor_id"]), 1)
            f2 = rng.sample(pool(("instructor", "academic_administrator"), t_asg, lid, a["instructor_id"], f1), 1)
            chosen, roles = f1 + f2, ["primary", "second"]
        else:
            adm = rng.sample(pool(("academic_administrator",), t_asg, lid, a["instructor_id"]), 1)
            ins2 = rng.sample(pool(("instructor",), t_asg, lid, a["instructor_id"], adm), 2)
            chosen, roles = adm + ins2, ["primary", "panel_member", "panel_member"]
        truth_v = latent == "genuine"

        def vote():
            acc = R.REVIEWER_ACCURACY_GENUINE if truth_v else R.REVIEWER_ACCURACY_OTHER
            return "violation" if (truth_v if rng.random() < acc else not truth_v) else "no_violation"
        recs = [(rid, vote(), tadd(t_rev, days=dur * rng.uniform(0.5, 1.0))) for rid in chosen]
        last_rec = max(r[2] for r in recs)
        tb = None
        if need == 2 and recs[0][1] != recs[1][1]:
            t_tb = tadd(last_rec, hours=rng.uniform(1, 24))
            if t_tb <= SNAP:
                tbr = rng.sample(pool(("instructor", "academic_administrator"), t_tb, lid, a["instructor_id"], chosen), 1)[0]
                tb = (tbr, vote(), tadd(t_tb, days=rng.uniform(1, 5)), t_tb)
                last_rec = tb[2]
        t_dec = tadd(last_rec, hours=rng.uniform(1, 36))

        # evidence times fall between assignment and the planned decision
        for etype in EVD_BY_LATENT[latent][:rng.randint(1, 4)]:
            at = tadd(t_asg, seconds=(t_dec - t_asg).total_seconds() * rng.uniform(0.05, 0.85))
            add_evidence(etype, at, "reviewer", chosen[0] if rng.random() < 0.6 else rng.choice(chosen), "pre_decision")

        ev("Case", cid, "opened", "assigned", t_asg, "system", None, f"{len(chosen)} reviewer(s) assigned after conflict check")
        for rid, role in zip(chosen, roles):
            ctr["crv"] += 1
            rv = next(r for r in recs if r[0] == rid)
            case_rev.append(dict(
                assignment_id=f"CRV-{ctr['crv']:06d}", case_id=cid, reviewer_id=rid, assignment_role=role,
                assigned_at=t_asg, recommendation=rv[1] if rv[2] <= SNAP else None,
                recommended_at=rv[2] if rv[2] <= SNAP else None, conflict_checked=True))
        if t_rev <= SNAP:
            ev("Case", cid, "assigned", "under_review", t_rev, "reviewer", chosen[0], "Review started")
        if tb:
            ctr["crv"] += 1
            case_rev.append(dict(
                assignment_id=f"CRV-{ctr['crv']:06d}", case_id=cid, reviewer_id=tb[0], assignment_role="tiebreak",
                assigned_at=tb[3], recommendation=tb[1] if tb[2] <= SNAP else None,
                recommended_at=tb[2] if tb[2] <= SNAP else None, conflict_checked=True))

        known = all(r[2] <= SNAP for r in recs) and (tb is None or tb[2] <= SNAP) and t_dec <= SNAP
        dec_id = None
        if known:
            allv = [r[1] for r in recs] + ([tb[1]] if tb else [])
            vv = sum(1 for v in allv if v == "violation")
            violation = vv * 2 > len(allv)
            outcome = R.violation_outcome(adj) if violation else R.NONVIOLATION_OUTCOME[latent]
            n_ev = sum(1 for e in ev_rows if e["at"] <= t_dec)
            dec_id = f"DEC-{cid}-01"
            decisions.append(dict(
                decision_id=dec_id, case_id=cid, decision_stage="initial", outcome=outcome,
                rationale=R.rationale(outcome, adj, rule["rule_id"], vv, len(allv), n_ev),
                decision_basis="reviewer_vote", decided_by=chosen[0], decided_at=t_dec, votes_violation=vv,
                votes_total=len(allv), evidence_count_at_decision=n_ev, supersedes_decision_id=None))
            ev("Case", cid, "under_review", "decided", t_dec, "reviewer", chosen[0], f"Decision {dec_id}: {outcome}")

        # post-decision: appeal or closure
        appeal_rows = []
        if known:
            adverse = violation
            p_app = (R.P_APPEAL_IF_WRONGLY_ACCUSED if latent != "genuine" else R.P_APPEAL_IF_GUILTY) if adverse else 0
            if adverse and rng.random() < p_app:
                t_f = tadd(t_dec, days=rng.uniform(1, R.APPEAL_WINDOW_DAYS - 1))
                if t_f <= SNAP:
                    if latent == "genuine":
                        grounds = rng.choice(["disproportionate_penalty", "new_evidence", "procedural_irregularity"])
                    elif rng.random() < 0.1:
                        grounds = "procedural_irregularity"
                    else:
                        grounds = {"legit_quote": "quotation_properly_cited", "shared_template": "template_overlap",
                                   "false_positive": "false_positive_evidence"}[latent]
                    aid = f"APL-{cid}-01"
                    ap = dict(appeal_id=aid, case_id=cid, original_decision_id=dec_id, filed_by_learner_id=lid,
                              filed_at=t_f, grounds=grounds, status=None, appeal_reviewer_id=None,
                              review_assigned_at=None, resolved_at=None, outcome=None,
                              independent_review_completed=False, resulting_decision_id=None, resolution_rationale=None)
                    appeals.append(ap)
                    ev("Appeal", aid, None, "filed", t_f, "learner", lid, f"Grounds: {grounds}")
                    ev("Case", cid, "decided", "appealed", t_f, "learner", lid, f"Appeal {aid} filed")
                    if grounds != "disproportionate_penalty" and rng.random() < 0.7:
                        add_evidence("learner_statement", tadd(t_f, hours=rng.uniform(1, 24)), "learner", lid, "appeal")
                    if rng.random() < R.P_APPEAL_WITHDRAWN:
                        t_w = tadd(t_f, days=rng.uniform(1, 7))
                        if t_w <= SNAP:
                            ap.update(resolved_at=t_w, outcome="withdrawn", resolution_rationale="Learner withdrew the appeal.")
                            ev("Appeal", aid, "filed", "withdrawn", t_w, "learner", lid, "Withdrawn by learner")
                            ev("Case", cid, "appealed", "closed", t_w, "learner", lid, "Closed after appeal withdrawn")
                    else:
                        t_aa = tadd(t_f, hours=rng.uniform(12, 72))
                        if t_aa <= SNAP:
                            used = set(chosen) | ({tb[0]} if tb else set())
                            arev = rng.sample(pool(("academic_administrator",), t_aa, lid, a["instructor_id"], used), 1)[0]
                            ap.update(appeal_reviewer_id=arev, review_assigned_at=t_aa)
                            ev("Appeal", aid, "filed", "under_review", t_aa, "reviewer", arev, "Independent reviewer assigned")
                            ev("Case", cid, "appealed", "appeal_under_review", t_aa, "reviewer", arev, "Independent appeal review began")
                            if rng.random() < 0.4:
                                add_evidence("citation_check", tadd(t_aa, hours=rng.uniform(2, 60)), "reviewer", arev, "appeal")
                            t_res = tadd(t_aa, days=rng.uniform(4, 20))
                            if t_res <= SNAP:
                                says_v = truth_v if rng.random() < R.APPEAL_ACCURACY else not truth_v
                                if says_v:
                                    reduced = (outcome == "major_violation_penalty" and truth_v and
                                       rng.random() < (0.6 if grounds == "disproportionate_penalty" else 0.15))
                                    ap_out = "reduced" if reduced else "upheld"
                                else:
                                    ap_out = "overturned"
                                ap.update(resolved_at=t_res, outcome=ap_out, independent_review_completed=True)
                                if ap_out == "upheld":
                                    ap["resolution_rationale"] = "Independent review upheld the original decision."
                                else:
                                    new_out = "minor_violation_warning" if ap_out == "reduced" else R.NONVIOLATION_OUTCOME[latent]
                                    nid = f"DEC-{cid}-02"
                                    ap.update(resulting_decision_id=nid, resolution_rationale=(
                                        "Penalty reduced on proportionality grounds." if ap_out == "reduced"
                                        else "Independent review found the original decision unsafe; outcome replaced."))
                                    decisions.append(dict(
                                        decision_id=nid, case_id=cid, decision_stage="appeal", outcome=new_out,
                                        rationale=f"Appeal {aid} {ap_out}: " + ap["resolution_rationale"],
                                        decision_basis="reviewer_vote", decided_by=arev, decided_at=t_res,
                                        votes_violation=None, votes_total=None, evidence_count_at_decision=0,
                                        supersedes_decision_id=dec_id))
                                ev("Appeal", aid, "under_review", "resolved", t_res, "reviewer", arev, f"Outcome: {ap_out}")
                                ev("Case", cid, "appeal_under_review", "closed", t_res, "reviewer", arev, f"Closed: appeal {ap_out}")
                    appeal_rows.append(ap)
            if not appeal_rows:
                t_close = tadd(t_dec, days=R.APPEAL_WINDOW_DAYS)
                if t_close <= SNAP:
                    ev("Case", cid, "decided", "closed", t_close, "system", None, "Appeal window lapsed (INT-2026-000007)")

        # materialise evidence rows in time order, with an audit event for each
        ev_rows.sort(key=lambda e: (e["at"], e["etype"]))
        for e in ev_rows:
            if e["at"] > SNAP:
                continue
            eseq[0] += 1
            eid = f"EVD-{cid}-{eseq[0]:03d}"
            evidence.append(dict(
                evidence_id=eid, case_id=cid, evidence_type=e["etype"], description=EVD_DESC[e["etype"]],
                source_ref=f"evidence://{cid}/{eseq[0]:03d}/{e['etype']}",
                content_sha256=hashlib.sha256(f"{seed}|{cid}|{eseq[0]}|{e['etype']}".encode()).hexdigest(),
                evidence_stage=e["stage"], added_at=e["at"], added_by_actor_type=e["atype"], added_by_actor_id=e["aid"]))
            ev("EvidenceItem", eid, None, "added", e["at"], e["atype"], e["aid"], f"{e['etype']} attached")

    case_by_id = {c["case_id"]: c for c in cases}

    # ---- 5. inject labelled anomalies (after the clean baseline exists) ---
    issues = inject(rng, SNAP, reviewers, conflicts, conflict_set, cases, case_rev, evidence, decisions, appeals,
                    events, case_by_id, sim_by_id, sub_by_id, asm_by_id, ev, rev_by_id)

    # ---- 6. derived values --------------------------------------------------
    derive(S, R, SNAP, submissions, sims, cases, case_rev, evidence, decisions, appeals, events, sim_by_id,
           asm_by_id, sub_by_id)
    tables = {"reviewers": reviewers, "learners": learners, "reviewer_conflicts": conflicts,
              "assessments": assessments, "integrity_rules": rule_rows, "submissions": submissions,
              "similarity_reports": sims, "cases": cases, "case_reviewers": case_rev,
              "evidence_items": evidence, "decisions": decisions, "appeals": appeals, "state_events": events}

    # ---- 7. ground truth (separate artefact) --------------------------------
    case_of_sim = {c["similarity_id"]: c["case_id"] for c in cases}
    gt = []
    for sid, latent in latent_of.items():
        sim = sim_by_id[sid]
        cid = case_of_sim.get(sid, "")
        iss = issues.get(cid, {}) if cid else {}
        gt.append(dict(
            similarity_id=sid, submission_id=sim["submission_id"], case_id=cid, latent_class=latent,
            flag_band=band_of_sim[sid], expected_outcome=R.expected_outcome(latent, sim["adjusted_score"]),
            issue_type=iss.get("issue_type", ""), issue_entity_type=iss.get("entity_type", ""),
            issue_entity_id=iss.get("entity_id", ""), issue_detail=iss.get("detail", "")))
    return tables, gt, dict(seed=seed, scale=scale, n_flag=n_flag, n_case=n_case)


# ------------------------------------------------------------ anomaly injection
def inject(rng, SNAP, reviewers, conflicts, conflict_set, cases, case_rev, evidence, decisions, appeals,
           events, case_by_id, sim_by_id, sub_by_id, asm_by_id, ev, rev_by_id):
    """Mutate only the targeted case's rows; record every mutation in the returned label map."""
    n = max(2, int(len(cases) * R.ANOMALY_RATE + 0.5))
    issues, used = {}, set()
    init_dec = {d["case_id"]: d for d in decisions if d["decision_stage"] == "initial"}
    appealed = {a["case_id"] for a in appeals}

    def cands(pred):
        return [c["case_id"] for c in cases if c["case_id"] not in used and pred(c)]

    # (1) flag automatically treated as guilt: threshold -> decision with no human review
    closed_ev = {e["entity_id"] for e in events if e["entity_type"] == "Case" and e["to_state"] == "closed"}
    pool_ = cands(lambda c: c["case_id"] in init_dec and c["case_id"] not in appealed and c["case_id"] in closed_ev)
    for cid in rng.sample(pool_, min(n, len(pool_))):
        used.add(cid)
        c, d = case_by_id[cid], init_dec[cid]
        sim = sim_by_id[c["similarity_id"]]
        case_rev[:] = [r for r in case_rev if r["case_id"] != cid]
        first = next(e for e in sorted((e for e in evidence if e["case_id"] == cid), key=lambda e: e["added_at"]))
        drop = {e["evidence_id"] for e in evidence if e["case_id"] == cid and e is not first}
        evidence[:] = [e for e in evidence if e["evidence_id"] not in drop]
        t_new = tadd(c["opened_at"], minutes=2)
        events[:] = [e for e in events if not (
            (e["entity_type"] == "Case" and e["entity_id"] == cid and e["to_state"] in ("assigned", "under_review"))
            or (e["entity_type"] == "EvidenceItem" and e["entity_id"] in drop))]
        for e in events:
            if e["entity_type"] == "Case" and e["entity_id"] == cid:
                if e["to_state"] == "decided":
                    e.update(from_state="opened", event_at=t_new, actor_type="system", actor_id=None,
                             note="Automatic determination from threshold")
                elif e["to_state"] == "closed":
                    e["event_at"] = tadd(t_new, days=R.APPEAL_WINDOW_DAYS)
        oc = R.violation_outcome(sim["adjusted_score"])
        d.update(outcome=oc, decision_basis="auto_threshold", decided_by=None, decided_at=t_new,
                 rationale=f"Automatic: adjusted score {sim['adjusted_score']:.2f} exceeded threshold {c['opened_by_rule_id']}.")
        issues[cid] = dict(issue_type="flag_auto_guilt", entity_type="Decision", entity_id=d["decision_id"],
                           detail="Decision produced from score alone; no reviewers, evidence or review stages")

    # (2) reviewer has a conflict of interest
    pool_ = cands(lambda c: any(r["case_id"] == c["case_id"] for r in case_rev))
    for cid in rng.sample(pool_, min(n, len(pool_))):
        used.add(cid)
        c = case_by_id[cid]
        lid = sub_by_id[c["submission_id"]]["learner_id"]
        on_case = {r["reviewer_id"] for r in case_rev if r["case_id"] == cid} | {a["appeal_reviewer_id"] for a in appeals if a["case_id"] == cid}
        ins_id = asm_by_id[sub_by_id[c["submission_id"]]["assessment_id"]]["instructor_id"]
        cand = [r["reviewer_id"] for r in reviewers if r["role"] in ("instructor", "academic_administrator")
                and r["active_to"] is None and r["reviewer_id"] not in on_case and r["reviewer_id"] != ins_id]
        new = rng.choice(cand)
        victim = next(r for r in case_rev if r["case_id"] == cid)
        old = victim["reviewer_id"]
        victim.update(reviewer_id=new, conflict_checked=False)
        if (new, lid) not in conflict_set:
            conflict_set.add((new, lid))
            conflicts.append(dict(conflict_id=f"CNF-{len(conflicts) + 1:05d}", reviewer_id=new, learner_id=lid,
                                  conflict_type=rng.choice(S.CONFLICT_TYPES),
                                  declared_at=date(2025, 1, 1) + timedelta(days=rng.randint(0, 500))))
        for d in decisions:
            if d["case_id"] == cid and d["decided_by"] == old:
                d["decided_by"] = new
        for e in evidence:
            if e["case_id"] == cid and e["added_by_actor_id"] == old:
                e["added_by_actor_id"] = new
        for e in events:
            if e["actor_id"] == old and ((e["entity_type"] == "Case" and e["entity_id"] == cid) or
                                         (e["entity_type"] == "EvidenceItem" and e["entity_id"].startswith(f"EVD-{cid}-"))):
                e["actor_id"] = new
        issues[cid] = dict(issue_type="reviewer_conflict", entity_type="CaseReviewer", entity_id=victim["assignment_id"],
                           detail=f"Reviewer {new} has a declared conflict with the learner but was assigned")

    # (3) evidence added after decision, without any history event
    pool_ = cands(lambda c: c["case_id"] in init_dec and c["case_id"] not in appealed
                  and init_dec[c["case_id"]]["decided_at"] <= tadd(SNAP, days=-7))
    for cid in rng.sample(pool_, min(n, len(pool_))):
        used.add(cid)
        d = init_dec[cid]
        nseq = 1 + max(int(e["evidence_id"][-3:]) for e in evidence if e["case_id"] == cid)
        eid = f"EVD-{cid}-{nseq:03d}"
        at = tadd(d["decided_at"], hours=rng.uniform(2, 120))
        by = next(r["reviewer_id"] for r in case_rev if r["case_id"] == cid)
        evidence.append(dict(
            evidence_id=eid, case_id=cid, evidence_type="source_match", description=EVD_DESC["source_match"],
            source_ref=f"evidence://{cid}/{nseq:03d}/source_match",
            content_sha256=hashlib.sha256(f"late|{cid}|{nseq}".encode()).hexdigest(),
            evidence_stage="pre_decision", added_at=at, added_by_actor_type="reviewer", added_by_actor_id=by))
        issues[cid] = dict(issue_type="evidence_added_after_decision_no_history", entity_type="EvidenceItem",
                           entity_id=eid, detail="Evidence added after the decision; no state_events row; not an appeal")

    # (4) appeal closed without independent review
    pool_ = cands(lambda c: any(a["case_id"] == c["case_id"] and a["outcome"] in ("upheld", "overturned", "reduced")
                                for a in appeals))
    for j, cid in enumerate(rng.sample(pool_, min(max(2, n - 2), len(pool_)))):
        used.add(cid)
        ap = next(a for a in appeals if a["case_id"] == cid)
        if j % 2 == 0 and ap["outcome"] == "upheld":              # variant A: closed with no reviewer at all
            old_rev = ap["appeal_reviewer_id"]
            gone = {e["evidence_id"] for e in evidence if e["case_id"] == cid and e["evidence_stage"] == "appeal"
                    and e["added_by_actor_id"] == old_rev}
            evidence[:] = [e for e in evidence if e["evidence_id"] not in gone]
            events[:] = [e for e in events if not (
                (e["entity_type"] == "Appeal" and e["entity_id"] == ap["appeal_id"] and e["to_state"] == "under_review")
                or (e["entity_type"] == "Case" and e["entity_id"] == cid and e["to_state"] == "appeal_under_review")
                or (e["entity_type"] == "EvidenceItem" and e["entity_id"] in gone))]
            for e in events:
                if e["entity_type"] == "Case" and e["entity_id"] == cid and e["to_state"] == "closed":
                    e.update(from_state="appealed", actor_type="system", actor_id=None, note="Administratively closed")
                if e["entity_type"] == "Appeal" and e["entity_id"] == ap["appeal_id"] and e["to_state"] == "resolved":
                    e.update(from_state="filed", actor_type="system", actor_id=None, note="Administratively closed")
            ap.update(appeal_reviewer_id=None, review_assigned_at=None, independent_review_completed=False)
            detail = "Appeal closed administratively; no reviewer assigned"
        else:                                                      # variant B: original reviewer re-reviews own decision
            prim = next(r["reviewer_id"] for r in case_rev if r["case_id"] == cid and r["assignment_role"] == "primary")
            old = ap["appeal_reviewer_id"]
            ap["appeal_reviewer_id"] = prim
            for e in events:
                if e["actor_id"] == old and (e["entity_id"] in (ap["appeal_id"], cid)):
                    e["actor_id"] = prim
            for d in decisions:
                if d["decision_id"] == ap["resulting_decision_id"]:
                    d["decided_by"] = prim
            for e in evidence:
                if e["case_id"] == cid and e["added_by_actor_id"] == old:
                    e["added_by_actor_id"] = prim
            detail = "Appeal reviewed by a reviewer from the original case; recorded as independent"
        issues[cid] = dict(issue_type="appeal_closed_without_independent_review", entity_type="Appeal",
                           entity_id=ap["appeal_id"], detail=detail)
    return issues


# ------------------------------------------------------------------ derivation
def derive(S, R, SNAP, submissions, sims, cases, case_rev, evidence, decisions, appeals, events, sim_by_id,
           asm_by_id, sub_by_id):
    events.sort(key=lambda e: (e["event_at"], e["_seq"]))
    for i, e in enumerate(events, 1):
        e["event_id"] = f"EVT-{i:07d}"
    last = {}
    for e in events:
        last[(e["entity_type"], e["entity_id"])] = e
    for s in sims:
        s["flag_status"] = last[("SimilarityReport", s["similarity_id"])]["to_state"]
    for a in appeals:
        a["status"] = last[("Appeal", a["appeal_id"])]["to_state"]
    closed_at = {e["entity_id"]: e["event_at"] for e in events if e["entity_type"] == "Case" and e["to_state"] == "closed"}
    dec_by_case = {}
    for d in decisions:
        dec_by_case.setdefault(d["case_id"], []).append(d)
    for c in cases:
        cid = c["case_id"]
        c["reviewer_count"] = sum(1 for r in case_rev if r["case_id"] == cid)
        c["evidence_count"] = sum(1 for e in evidence if e["case_id"] == cid)
        c["status"] = last[("Case", cid)]["to_state"]
        ds = sorted(dec_by_case.get(cid, []), key=lambda d: d["decided_at"])
        init = [d for d in ds if d["decision_stage"] == "initial"]
        c["decided_at"] = init[0]["decided_at"] if init else None
        c["final_outcome"] = ds[-1]["outcome"] if ds else None
        c["closed_at"] = closed_at.get(cid)
        c["sla_due_at"] = tadd(c["opened_at"], days=R.SLA_DAYS)
        c["sla_breached"] = (c["decided_at"] or SNAP) > c["sla_due_at"]
    for d in decisions:
        d["evidence_count_at_decision"] = sum(1 for e in evidence if e["case_id"] == d["case_id"] and e["added_at"] <= d["decided_at"])
        if d["decision_stage"] == "initial":
            rs = [r for r in case_rev if r["case_id"] == d["case_id"] and r["recommendation"]]
            d["votes_total"] = len(rs)
            d["votes_violation"] = sum(1 for r in rs if r["recommendation"] == "violation")
    case_of_sub = {c["submission_id"]: c for c in cases}
    cur = {s["submission_id"]: s for s in sims if s["is_current"]}
    for s in submissions:
        c = case_of_sub.get(s["submission_id"])
        flag = cur[s["submission_id"]]
        if c is None:
            s["integrity_status"] = "flag_closed" if flag["flag_status"] == "triaged_closed" else "not_flagged"
        elif c["status"] != "closed":
            s["integrity_status"] = "case_in_progress"
        else:
            s["integrity_status"] = "sanctioned" if c["final_outcome"] in S.VIOLATION_OUTCOMES else "cleared"


# ----------------------------------------------------------------------- export
def export(tables, gt, meta, out):
    os.makedirs(f"{out}/csv", exist_ok=True)
    os.makedirs(f"{out}/json", exist_ok=True)
    os.makedirs(f"{out}/sql", exist_ok=True)
    os.makedirs(f"{out}/ground_truth", exist_ok=True)
    counts = {}
    for name, t in S.T.items():
        cols = [f["name"] for f in t["fields"]]
        rows = tables[name]
        counts[name] = len(rows)
        with open(f"{out}/csv/{name}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(cols)
            for r in rows:
                w.writerow([fmt(r[c]) for c in cols])
        with open(f"{out}/json/{name}.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump([{c: jsonable(r[c]) for c in cols} for r in rows], fh, indent=1)
            fh.write("\n")
    gcols = list(gt[0].keys())
    with open(f"{out}/ground_truth/ground_truth.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(gcols)
        for r in gt:
            w.writerow([fmt(r[c]) for c in gcols])
    with open(f"{out}/ground_truth/ground_truth.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(gt, fh, indent=1)
        fh.write("\n")
    with open(f"{out}/sql/schema.sql", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- SQLite-compatible DDL generated from src/schema.py\n" + S.ddl() + "\n")
    with open(f"{out}/sql/seed.sql", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- Seed data. Load schema.sql first. PRAGMA foreign_keys=ON is safe: parents are inserted first.\nBEGIN;\n")
        for name, t in S.T.items():
            cols = [f["name"] for f in t["fields"]]
            rows = tables[name]
            for i in range(0, len(rows), 250):
                vals = ",\n".join("(" + ",".join(sqlval(r[c]) for c in cols) + ")" for r in rows[i:i + 250])
                fh.write(f"INSERT INTO {name} ({', '.join(cols)}) VALUES\n{vals};\n")
        fh.write("COMMIT;\n")
    manifest = dict(
        generator="src/generate.py", seed=meta["seed"], scale=meta["scale"],
        command=f"python src/generate.py --seed {meta['seed']} --scale {meta['scale']} --out data",
        snapshot_date=R.SNAPSHOT.isoformat(), row_counts=counts,
        external_sources=[], external_data_used=False,
        provenance=("All records are procedurally generated from a seeded PRNG. No external dataset, scraped content "
                    "or personal data is used. Names are random combinations from a built-in list of common given "
                    "names and surnames; emails use the reserved example.edu domain."),
        schema_inspiration="Generic similarity-report / case-management concepts only; no vendor schema copied.")
    with open(f"{out}/manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    sums = {}
    for root, _, files in sorted(os.walk(out)):
        for f in sorted(files):
            if f == "checksums.sha256":
                continue
            p = os.path.join(root, f)
            sums[os.path.relpath(p, out)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    with open(f"{out}/checksums.sha256", "w", encoding="utf-8", newline="\n") as fh:
        for k in sorted(sums):
            fh.write(f"{sums[k]}  {k}\n")
    return counts


def data_dictionary_md():
    L = ["# Data dictionary", "", "Generated from `src/schema.py` (the same spec the validator uses).",
         "Types: `str`, `text`, `int`, `float`, `bool`, `date` (YYYY-MM-DD), `datetime` (YYYY-MM-DDTHH:MM:SS, UTC).",
         "**Derived** columns are recomputed from source rows, never drawn independently.", ""]
    for name, t in S.T.items():
        L += [f"## `{name}`", "", t["desc"], "", f"Primary key: `{t['pk']}`" + (
            "; composite uniqueness: " + ", ".join("(" + ", ".join(u) + ")" for u in t["unique"] if len(u) > 1)
            if any(len(u) > 1 for u in t["unique"]) else ""), "",
            "| Field | Type | Required | Allowed values / pattern | Unit | Unique | FK | Derived | Validation rule |",
            "|---|---|---|---|---|---|---|---|---|"]
        for f in t["fields"]:
            allowed = ", ".join(f["allowed"]) if f["allowed"] else (f"`{f['pattern']}`" if f["pattern"] else "")
            L.append(f"| {f['name']} | {f['type']} | {'yes' if f['required'] else 'no'} | {allowed} | {f['unit']} | "
                     f"{'yes' if f['unique'] or f['name'] == t['pk'] else ''} | {f['fk'] or ''} | "
                     f"{'yes' if f['derived'] else ''} | {f['rule']} |")
        L.append("")
    return "\n".join(L)


def run(seed, scale, out):
    tables, gt, meta = generate(seed, scale)
    counts = export(tables, gt, meta, out)
    return counts, tables, gt


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--scale", type=float, default=1.0, help="1.0 = 10,000 submissions / 1,000 flags / 300 cases")
    ap.add_argument("--out", default="data")
    ap.add_argument("--docs", default="docs", help="where to write the data dictionary")
    ap.add_argument("--no-docs", action="store_true", help="skip writing the data dictionary (use for starter sets)")
    a = ap.parse_args()
    counts, _, _ = run(a.seed, a.scale, a.out)
    if a.docs and not a.no_docs:
        os.makedirs(a.docs, exist_ok=True)
        with open(f"{a.docs}/data_dictionary.md", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data_dictionary_md() + "\n")
    print(json.dumps(counts, indent=2))
