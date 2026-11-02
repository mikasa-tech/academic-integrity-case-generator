# AI use disclosure

I used **Claude (claude.ai chat)** as my main tool. This file says plainly what it did, what I did, and what I checked.
Items marked **[CONFIRM]** are my claims. Edit them so they are true for me before submitting.

## Where AI did the work
- Claude designed and wrote essentially all the code: `src/schema.py`, `src/rules.py`, `src/generate.py`,
  `src/validate.py`, `src/repro_check.py`, `src/build_dashboard.py`, the dashboard template, and the README and docs.
- Claude chose the model: a latent "true cause" for each flag, reviewer/appeal error rates, rule bands, the four anomaly
  injections, and the detectors.
- Claude ran its own tests in a Linux sandbox (validator, seed/scale sweep, negative tests, headless-browser test of the dashboard).

## Where I relied on it heavily
- The event-simulation loop in `generate.py` and the anomaly injection functions.
- The SQL load, the validation checks and the dashboard.

## What I did myself
- Ran the generator, validator, reproducibility check and SQLite load on **Windows (PowerShell, `py` launcher)**, and
  confirmed the results matched the numbers Claude reported (112/112 structural, 5/5 process, run1 == run2 == committed).
- Wrote and ran SQL queries against the generated database and confirmed the anomaly counts (8, 8, 8) against the answer key.
- Built a separate React app with another tool, asked Claude to compare it with this one, read the comparison,
  and chose to submit this project because of the validation and data-quality problems found in the other.
  **[CONFIRM]** None of that app's code or data is in this repository.
- Made local edits to `dashboard/template.html` (case-list filtering, jump-to-case from the Audit tab) and
  `src/repro_check.py` (Windows/Linux line-ending normalisation). **[CONFIRM: say whether you wrote these by hand or with a tool.]**

## What I reviewed, changed or validated
Tick only what is true:
- [ ] I read `src/rules.py` and can explain each threshold, probability and why it exists.
- [ ] I read the case-simulation loop and `inject()` in `src/generate.py` and can explain them.
- [ ] I changed a parameter in `src/rules.py`, regenerated, and confirmed validation still reconciles. Parameter: `<which>`; result: `<what>`.
- [ ] I corrupted a copy of the data and confirmed the validator fails.

## Problems found and fixed during development
- The first manifest embedded the output path, so two identical runs had different checksums. Fixed by recording a fixed command string.
- The validator crashed on a dangling foreign key instead of reporting it. Fixed: it now stops with a clear report.
- Early versions produced too few successful appeals. Reviewer error for benign overlap was raised to 15% (85% accuracy).
- A PowerShell quirk dropped the empty string in `--docs ""`. Fixed with a `--no-docs` flag.
- The dashboard builder read a stale validation summary. Fixed: it now validates the data it embeds.
- Text files could be written with Windows line endings, risking checksum mismatches. Fixed with explicit `\n` writes and `.gitattributes`.
- A README sentence misdescribed the 20 outcome differences. Corrected after breaking them down.

## Known limitations (also in the README)
- The case count is pinned to the brief rather than emerging from triage behaviour; rates are modelling assumptions.
- There is no real text matching. The detectors only know the four planted patterns.
- Conflict declaration dates are not applied to assignments made before the conflict was declared.
- There are no automated unit tests; verification is the validator, the reproducibility check and manual negative tests.
