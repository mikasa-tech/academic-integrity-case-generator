#!/usr/bin/env python3
"""Regenerate the dataset twice with the same seed and compare row counts and SHA-256 checksums.
Also compares against the committed data/ folder, and shows that a different seed really differs.

    python src/repro_check.py --seed 20261022 --scale 1.0
"""
import argparse
import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402


def sums(root):
    out = {}
    text_extensions = {".csv", ".json", ".sql", ".md", ".txt", ".html"}

    for d, _, files in sorted(os.walk(root)):
        for f in sorted(files):
            if f == "checksums.sha256":
                continue

            p = os.path.join(d, f)
            with open(p, "rb") as file:
                content = file.read()

            # Normalize Windows and Unix line endings for text files.
            if os.path.splitext(f)[1].lower() in text_extensions:
                content = content.replace(b"\r\n", b"\n")

            relative_path = os.path.relpath(p, root)
            out[relative_path] = hashlib.sha256(content).hexdigest()

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--committed", default="data")
    ap.add_argument("--out", default="docs/reproducibility_report.md")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        c1, _, _ = generate.run(a.seed, a.scale, f"{t}/run1")
        c2, _, _ = generate.run(a.seed, a.scale, f"{t}/run2")
        c3, _, _ = generate.run(a.seed + 1, a.scale, f"{t}/other_seed")
        s1, s2, s3 = sums(f"{t}/run1"), sums(f"{t}/run2"), sums(f"{t}/other_seed")
    committed = sums(a.committed) if os.path.isdir(a.committed) else {}
    same12 = s1 == s2 and c1 == c2
    same_committed = (s1 == committed) if committed else None
    differs = s1 != s3
    lines = ["# Reproducibility report", "",
             f"Seed `{a.seed}`, scale `{a.scale}`. Each run regenerates every CSV/JSON/SQL/ground-truth file in a fresh directory.", "",
             f"- Run 1 vs run 2 identical (row counts and all {len(s1)} file checksums): **{same12}**",
             f"- Run 1 vs committed `{a.committed}/`: **{same_committed}**",
             f"- Seed {a.seed + 1} produces different data (sanity check that the seed matters): **{differs}**", "",
             "| File | SHA-256 (run 1) | Run 2 matches |", "|---|---|---|"]
    for k in sorted(s1):
        lines.append(f"| {k} | `{s1[k][:16]}…` | {s1[k] == s2.get(k)} |")
    lines += ["", "| Table | Run 1 rows | Run 2 rows |", "|---|---|---|"] + [f"| {k} | {c1[k]} | {c2[k]} |" for k in c1]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print(f"run1==run2: {same12} | run1==committed: {same_committed} | different seed differs: {differs}")
    sys.exit(0 if same12 and differs and same_committed is not False else 1)


if __name__ == "__main__":
    main()
