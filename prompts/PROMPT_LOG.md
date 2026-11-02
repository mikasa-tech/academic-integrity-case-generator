# Prompt history

Every prompt I sent to an AI tool for this project, in order. AI responses are not included (optional per the FAQ).
Terminal output that I pasted into the chat is summarised in brackets, and my Windows username/path is redacted
(`C:\Users\<user>\...`) because this repository is public.

**Tool:** Claude (claude.ai chat), one conversation, 2026-11-01 to 2026-11-02.
**Attachments sent with my first message:** the three YottaFlex files (problem statement, FAQ, submission guidelines).

## Part 1: Claude, building the generator

1. [Message with the three YottaFlex attachments. **TODO: if you typed any text with it, paste it here exactly. If it was attachments only, leave this line as is.**]
2. `yes`
3. `build the project end to end. as explained in problem statement, amke sure it satisfies all the requirements in the statement. ask questions if needed. download if required something`

## Part 2: learning how to run and explain it

4. `how to run it, how to explain the full project to someone end to end, how to use the project, its pros and cons, features everything.`
5. [Pasted a PowerShell error: `py src/generate.py --scale 0.1 --out starter --docs ""` failed with `argument --docs: expected one argument`.]
6. `how to install sqlite`
7. `which one is the best option, sqlite or mysql`
8. [Pasted a PowerShell error: running the SQLite load command from the wrong folder gave `FileNotFoundError: data/sql/schema.sql`.]
9. [Pasted the successful SQLite output `[('panel_escalation', 80), ('priority_review', 170), ('standard_review', 750)]` and a `dir` listing, then asked:] `what to do next`
10. [Pasted Python console lines (`py`, `import sqlite3`, `c.execute(...)`) with no question; I was following the instructions I had been given.]
11. [Pasted a Python console session where `py` was typed inside Python (`NameError: name 'py' is not defined`) and then `>>>` lines pasted into PowerShell (`The term '>>' is not recognized`). The SQL queries inside it ran correctly.]
12. [Pasted the output of `py src/validate.py --data data` (112/112 and 5/5 passed, four detectors exact) and `py src/repro_check.py` (`run1==run2: True | run1==committed: True | different seed differs: True`).]
13. `but i couldnt get how to use the project, what its main purpose, how is it solving the problem, and what i did from last 10 mins. pls help me understand everything`
14. `so i dont need to upload any document to the system, it automatically generates random files and checks for its plagarism/cheating. and i can regenrate the random datas so that i can show different demos. right? but why there is no home page kind of thing, i mean do i have show uts demo by running commands at vs code terminal only? clarify`
15. `can u read the website, like if i give u a link or localhost link, can u check it properly and go throgh that to help me make changes in that`

## Part 3: comparing with another implementation, then the dashboard

16. [Uploaded a zip and screen recording of a separate React/TypeScript app I had built with another tool, and wrote:] `i built the same project using some other tools, check it, its code, its video to know how its working, whether should i go for this project or project built by u to submit. be honest, which one works the best`
17. `i trust u and i will use the one given by u only. but i want my project's interface to look impressive and cool, since its the slection round of the company i genuinely want it to imprss the recruiters.  help`
18. `check the file once again, run it, check if its running accurately without anything wrong or wrong data, check if its each feature working correctly, and what improvements we can do`
19. [Uploaded `integrity-case-dataset.zip` (my local copy, with my own edits) with no text.]
20. `dp both` (a typo for "do both": write the walkthrough document and help me prepare the prompt log).

## Part 4: other AI tools (fill in honestly)

- **Tool used to build the separate React app (item 16):** `<name of tool, e.g. Google AI Studio>`. That app is **not** part of this submission and none of its code was copied here. If you want full transparency, paste the prompts you sent to it below, or state that you can't export them.
  - `<paste prompts, or write "not exportable; I did not reuse any of its code or data">`
- **Tool used for my local edits to the dashboard template and `repro_check.py` (backup files, Prettier-style formatting):** `<name the tool or say "edited by hand">`. Paste its prompts here if it was an AI tool.

## Limitations of this record
Copied manually from the chat. Pasted terminal output is summarised rather than reproduced in full, and my username in file paths is redacted. Attachments are not included in the repository (the YottaFlex files are the company's, and my other app is out of scope).
