# AI use disclosure

I used Claude (claude.ai chat) as my main tool. This file says plainly what it did, what I did, and what I checked.

## Where AI did the work

- Claude designed and wrote essentially all the code: `src/schema.py`, `src/rules.py`, `src/generate.py`,
  `src/validate.py`, `src/repro_check.py`, `src/build_dashboard.py`, the dashboard template, and the README and docs.
- Claude chose the model: a latent "true cause" for each flag, reviewer/appeal error rates, rule bands, the four anomaly
  injections, and the detectors.
- Claude assisted in developing the validation logic and test procedures, and provided analysis of test results.
  I independently ran the generator, validator, reproducibility check and SQLite checks in my Windows environment.

## Where I relied on it heavily

- The event-simulation loop in `generate.py` and the anomaly injection functions.
- The SQL load, the validation checks and the dashboard.

## What I personally did

- Ran the generator, validator and reproducibility checks on Windows using PowerShell and the Python `py` launcher.
- Independently verified the reported validation results: 112/112 structural checks and 5/5 process checks.
- Loaded the SQL schema and seed data into SQLite and checked database integrity.
- Queried the generated records and compared the anomaly counts against the separate ground-truth data.
- Modified `dashboard/template.html` to improve case-list filtering and navigation from Audit Findings.
- Modified `src/repro_check.py` and verified that the generated data was reproducible against the committed dataset.

## Problems found and fixed during development

- The first manifest embedded the output path, so two identical runs had different checksums. Fixed by recording a fixed command string.
- The validator crashed on a dangling foreign key instead of reporting it. Fixed: it now stops with a clear report.
- A PowerShell quirk dropped the empty string in `--docs ""`. Fixed with a `--no-docs` flag.
- The dashboard builder read a stale validation summary. Fixed: it now validates the data it embeds.
- Text files could be written with Windows line endings, risking checksum mismatches. Fixed with explicit `\n` writes and `.gitattributes`.
- A README sentence misdescribed the 20 outcome differences. Corrected after breaking them down.

## Engineering decisions and trade-offs

1. Synthetic data:
   Used synthetic records to avoid dependence on private or confidential student information.

2. Deterministic generation:
   Used a fixed random seed so the same input parameters produce reproducible outputs.

3. Relational modelling:
   Used primary keys, foreign keys and bridge tables to maintain relationships between records.

4. Append-only audit history:
   Represented important workflow changes as events rather than relying only on the latest status.

5. Ground-truth separation:
   Stored deliberately injected anomaly labels separately from the input data used by detectors.

6. Static dashboard:
   Chose a zero-dependency HTML dashboard to make the generated records and audit findings easy to inspect without deploying a backend service.

## Verification performed

The following checks were performed on the generated
project data:

- 112/112 structural validation checks passed.
- 5/5 process validation checks passed.
- Same-seed reproducibility verified.
- Regenerated data matched the committed dataset.
- Different seed produced different output.
- Dashboard was rebuilt successfully.
- Four planted anomaly categories were detected against separate ground-truth labels.

## Known limitations

- The case count is constrained to the challenge's target volume rather than emerging entirely from
  the simulated triage process.
- Reviewer accuracy rates and other behavioural probabilities are synthetic modelling assumptions.
- The system does not perform real document-level text matching or plagiarism detection.
- The anomaly detectors target the four deliberately planted failure patterns and do not establish
  general real-world detection performance.
- Conflict declaration dates are not applied to assignments made before the conflict was declared.
- The dashboard is a static, read-only audit console; it is not a fully interactive case-management system.
- There are no automated unit tests. Verification relies on the validator, reproducibility checks
  and manual negative testing.

## Technical ownership

I used AI-assisted implementation, but I treated the generated code as something that required verification.

I reviewed the generated architecture and data model, ran the project locally, examined the generated records, checked the SQL relationships, investigated development issues and made local modifications.
