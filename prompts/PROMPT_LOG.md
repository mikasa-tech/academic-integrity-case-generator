# Prompt History & Engineering Log

A transparent, chronological log of all architectural, algorithmic, and verification prompts utilized during the design and development of the **YottaFlex Academic Integrity Case Management Generator**.

**Primary Tool:** Claude 3.5 Sonnet (claude.ai)  
**Methodology:** Spec-first prompt engineering with iterative schema synthesis, deterministic event simulation, anomaly injection, and automated validator generation.

## Phase 1: Architectural Formulation & Requirements Breakdown

**Prompt 1.1:**

I am attaching the three official YottaFlex specification documents (Problem Statement, FAQ, and Submission Guidelines) for the Academic Integrity Case Management challenge.

Please review the constraints thoroughly:

1. We need to model 10 core entities (Learners, Assessments, Submissions, Similarity Reports, Integrity Rules, Cases, Reviewers, Case Reviewers, Evidence Items, Decisions, Appeals, plus State Events audit trail and Conflict registry).
2. The dataset must be 100% deterministic, seeded, and reproducible across operating systems (Python 3 standard library only, zero external packages, no datetime clock calls).
3. Critical Rule: A high similarity score must NEVER imply automatic guilt; it only determines the level of human review required (Standard 1 reviewer, Priority 2 reviewers, Panel 3 reviewers).
4. Auto-guilt must be strictly prohibited (auto_guilt_permitted = false).

Before writing code, outline the relational entity schema, foreign key dependencies, and the lifecycle state machine for submissions, similarity reports, cases, decisions, and appeals.

**Prompt 1.2:**
Now implement src/rules.py and src/schema.py.
To avoid arbitrary dice-rolling, each similarity flag must originate from an underlying latent cause:

- 'genuine' (actual plagiarism or collusive copy)
- 'legit_quote' (properly attributed or cited material inflating raw score)
- 'shared_template' (boilerplate starter code or prompt instructions)
- 'false_positive' (statistical anomaly)

Define the rule bands based on adjusted score (raw score minus excluded quotes and templates).
Use 90% and 85% as explicitly documented synthetic reviewer-behaviour assumptions, not empirically
established real-world accuracy measurements.
Ensure decisions support an append-only design: when an appeal is upheld or overturned, never overwrite the existing decision row; append a new superseding decision and log an immutable state event.

## Phase 2: Generator Implementation & Timeline Simulation

**Prompt 2.1:** Deterministic Seeded Engine with Event Loop

Build src/generate.py using strictly Python standard library (random.Random(seed), csv, json, hashlib).
Parameters required:

- Default seed: 20261022
- Scale factor: 1.0 (generating exactly 10,000 submissions, 1,000 flags, 300 cases)
- Fast starter option: scale 0.1 (1,000 submissions, 100 flags, 30 cases)

Simulate realistic time-ordered workflows:

1. Submission timestamps clustered prior to deadline (with 7% late submissions).
2. Triage & rule-matching into standard, priority, and panel escalation.
3. Reviewer assignment with Conflict of Interest (COI) pre-checks.
4. Independent reviewer voting with tiebreak protocols on 1-1 splits.
5. Snapshot cutoff at 2026-10-31 so in-flight cases remain realistically open.

**Prompt 2.2:** Labelled Anomaly Injection for Compliance Auditing

A core requirement of the problem statement is testing whether an auditor can detect procedural violations.
Implement an inject() stage that executes after the baseline generation and targets isolated cases, recording each in an independent ground_truth directory:

1. Flag treated as auto-guilt (bypassing mandatory human reviewer assignment).
2. Reviewer assigned despite active Conflict of Interest with the learner.
3. Evidence item added after formal decision without a corresponding audit event.
4. Appeal closed without assigning an independent administrative reviewer.

Ensure these labels are stored strictly in data/ground_truth/ and never leaked into the input tables.

## Phase 3: Verification, Reproducibility & Audit Dashboard

**Prompt 3.1:** Automated Validator & Anomaly Detectors

Write src/validate.py and src/repro_check.py.
The validator must perform:

1. Structural integrity checks (112 checks: foreign keys, non-null constraints, unique identifiers, enum values, ISO 8601 formatting, date orderings).
2. Process integrity checks (5 checks: SLA compliance, tiebreak rules, appeal windows).
3. Four standalone anomaly detectors that query raw tables (without reading ground truth) and compute Precision and Recall against ground truth labels (must achieve 1.0 precision and recall).

src/repro_check.py must regenerate the dataset from scratch twice and verify byte-for-byte SHA-256 identity against the committed dataset. Ensure Unix LF newlines are enforced on Windows environments.

**Prompt 3.2:** Self-Contained Visual Audit Dashboard

Create src/build_dashboard.py and an HTML/CSS/JS template in dashboard/template.html.
It must generate a zero-dependency, single-file dashboard/index.html featuring:

- Threshold Lab: Interactive slider demonstrating how adjusting the exclusion threshold prevents over 500 false-positive investigations.
- Case Explorer: Timeline visualization with filterable cases, reviewer votes, evidence, and rationale.
- Audit Findings: Tabular comparison of algorithmic detector findings vs. ground truth labels with 100% precision/recall confirmation.

## Record accuracy

This document records the project-development prompts available to me. Prompts are reproduced from the available conversation history. Where wording has been reconstructed rather than copied verbatim, it is identified accordingly.

This log should not be interpreted as a complete verbatim export if any original conversations or prompts are unavailable.
