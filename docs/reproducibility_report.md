# Reproducibility report

Seed `20261022`, scale `1.0`. Each run regenerates every CSV/JSON/SQL/ground-truth file in a fresh directory.

- Run 1 vs run 2 identical (row counts and all 31 file checksums): **True**
- Run 1 vs committed `data/`: **True**
- Seed 20261023 produces different data (sanity check that the seed matters): **True**

| File | SHA-256 (run 1) | Run 2 matches |
|---|---|---|
| csv/appeals.csv | `42ca57e2870d6a9a…` | True |
| csv/assessments.csv | `1d3a2ddec3cdfb9a…` | True |
| csv/case_reviewers.csv | `3feb590a0efc70d5…` | True |
| csv/cases.csv | `1855684cac10c827…` | True |
| csv/decisions.csv | `3755c4fbe5174dca…` | True |
| csv/evidence_items.csv | `21578d4c9f0b26e8…` | True |
| csv/integrity_rules.csv | `71b8dc1749272330…` | True |
| csv/learners.csv | `96ed958dea018678…` | True |
| csv/reviewer_conflicts.csv | `02cbc4e4aa375807…` | True |
| csv/reviewers.csv | `885d721ea2048ef4…` | True |
| csv/similarity_reports.csv | `45d661f5b0e3dbdf…` | True |
| csv/state_events.csv | `c402b06547d33cd0…` | True |
| csv/submissions.csv | `60e6a91635dc9c50…` | True |
| ground_truth/ground_truth.csv | `6eb61362eaf03b11…` | True |
| ground_truth/ground_truth.json | `35662394e8850154…` | True |
| json/appeals.json | `a7c91909ec357940…` | True |
| json/assessments.json | `fb2b28a946ef6093…` | True |
| json/case_reviewers.json | `c0307710e6d0842e…` | True |
| json/cases.json | `1e77bc6a5ade25cb…` | True |
| json/decisions.json | `c0320b0f2f7848b4…` | True |
| json/evidence_items.json | `1ac4d85ad28d79ba…` | True |
| json/integrity_rules.json | `59a934bf8ea3861e…` | True |
| json/learners.json | `bb03ed8d2ca49cdf…` | True |
| json/reviewer_conflicts.json | `63e39097c4ec489d…` | True |
| json/reviewers.json | `3d219188f47e6adb…` | True |
| json/similarity_reports.json | `86747085d02279f1…` | True |
| json/state_events.json | `5b7adb6420217144…` | True |
| json/submissions.json | `51aef498e2035764…` | True |
| manifest.json | `120e070ca8bd767a…` | True |
| sql/schema.sql | `780a8d6bc83a361a…` | True |
| sql/seed.sql | `02bf18111aaf24b9…` | True |

| Table | Run 1 rows | Run 2 rows |
|---|---|---|
| reviewers | 38 | 38 |
| learners | 2500 | 2500 |
| reviewer_conflicts | 207 | 207 |
| assessments | 160 | 160 |
| integrity_rules | 9 | 9 |
| submissions | 10000 | 10000 |
| similarity_reports | 10173 | 10173 |
| cases | 300 | 300 |
| case_reviewers | 641 | 641 |
| evidence_items | 1032 | 1032 |
| decisions | 308 | 308 |
| appeals | 46 | 46 |
| state_events | 14883 | 14883 |
