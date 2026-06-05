#!/usr/bin/env python3
"""
Blind grading-sheet generator (Reviewer 2 #1 — inter-annotator agreement; Task 4a).

Emits a CSV that a second annotator fills in by hand to re-grade a random subset of
the stored B3 outputs. The original (machine) grade is deliberately *excluded* so the
re-grading is blind. A sidecar `*.manifest.json` records the seed and the exact ids
selected, so compute_kappa.py can match the completed sheet back to the original grades.

Sampling: a fixed seed (recorded), ~n/|files| rows per result file (one file per case),
stratified across difficulty tiers when a `difficulty`/`tier` field is present, else
uniform random.

Usage:
  python Experiments/Revision/make_grading_sheet.py \
      --results Experiments/Case_I/results/b3_rcp_latest.json \
                Experiments/Case_II/results/b3_rcp_latest.json \
      --n 40 --seed 20260602 --out Experiments/Revision/out/grading_sheet.csv

The annotator fills the final column with Y/N and returns the CSV unchanged otherwise.
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COLUMNS = ["case", "Q#", "Query", "Reference answer", "System output", "Correct (Y/N)"]


def _qid(rec):
    for k in ("question_id", "id", "Q#", "qid"):
        if k in rec:
            return rec[k]
    raise KeyError("no question id field in record")


def _tier(rec):
    for k in ("difficulty", "tier", "level"):
        if rec.get(k):
            return str(rec[k]).lower()
    return None


def _case_name(path: str) -> str:
    p = path.replace("\\", "/").lower()
    if "case_ii" in p or "company_b" in p:
        return "II"
    if "case_i" in p:
        return "I"
    return Path(path).stem


def sample_file(path: str, k: int, rng: random.Random):
    data = json.load(open(path, encoding="utf-8"))
    if k >= len(data):
        return list(data)
    # stratify by tier if available
    tiers = defaultdict(list)
    for r in data:
        tiers[_tier(r)].append(r)
    if len(tiers) > 1 and None not in tiers:
        chosen = []
        per = max(1, k // len(tiers))
        for t, rows in tiers.items():
            rng.shuffle(rows)
            chosen.extend(rows[:per])
        rng.shuffle(chosen)
        return chosen[:k]
    out = list(data)
    rng.shuffle(out)
    return out[:k]


def main():
    ap = argparse.ArgumentParser(description="Generate a blind grading sheet (CSV).")
    ap.add_argument("--results", nargs="+", required=True, help="one B3 result JSON per case")
    ap.add_argument("--n", type=int, default=40, help="total rows (split across files)")
    ap.add_argument("--seed", type=int, default=20260602)
    ap.add_argument("--out", default="Experiments/Revision/out/grading_sheet.csv")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    per_file = max(1, args.n // len(args.results))
    rows, manifest = [], []
    for path in args.results:
        case = _case_name(path)
        for r in sample_file(path, per_file, rng):
            qid = _qid(r)
            rows.append({
                "case": case, "Q#": qid,
                "Query": r.get("question", ""),
                "Reference answer": r.get("ground_truth", ""),
                "System output": (r.get("answer", "") or "").replace("\n", " ").strip(),
                "Correct (Y/N)": "",
            })
            manifest.append({"case": case, "qid": qid, "source": path})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    man = out.with_suffix(".manifest.json")
    json.dump({"seed": args.seed, "n": len(rows), "files": args.results, "items": manifest},
              open(man, "w", encoding="utf-8"), indent=2)

    print(f"Wrote {len(rows)} blind rows to {out}")
    print(f"Manifest (seed={args.seed}) -> {man}")
    print("NOTE: the 'Correct (Y/N)' column is intentionally blank; the original machine "
          "grade is NOT included (blind re-grading).")


if __name__ == "__main__":
    main()
