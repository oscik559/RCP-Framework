#!/usr/bin/env python3
"""
Cohen's kappa from a completed grading sheet (Reviewer 2 #1; Task 4b).

Matches a human annotator's blind Y/N labels (from make_grading_sheet.py, now filled
in) against the original machine grades stored in the B3 result files, then reports
Cohen's kappa and raw percent agreement on the matched binary labels — overall and,
when a 'case' column is present, per case.

Matching is by (case, Q#). The original grade is read from the same result files used
to build the sheet (default: read them from the sheet's *.manifest.json; or pass
--results explicitly).

Usage:
  python Experiments/Revision/compute_kappa.py \
      --sheet Experiments/Revision/out/grading_sheet.csv
  # or specify the originals explicitly:
  python Experiments/Revision/compute_kappa.py --sheet sheet.csv \
      --results Experiments/Case_I/results/b3_rcp_latest.json \
                Experiments/Case_II/results/b3_rcp_latest.json
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _stats import cohens_kappa


def _qid(rec):
    for k in ("question_id", "id", "Q#", "qid"):
        if k in rec:
            return rec[k]
    raise KeyError("no question id field in record")


def _case_name(path: str) -> str:
    p = path.replace("\\", "/").lower()
    if "case_ii" in p or "company_b" in p:
        return "II"
    if "case_i" in p:
        return "I"
    return Path(path).stem


def _yn(v):
    s = str(v).strip().lower()
    if s in ("y", "yes", "1", "true", "correct"):
        return 1
    if s in ("n", "no", "0", "false", "incorrect"):
        return 0
    return None


def load_original_grades(result_paths):
    """Map (case, str(qid)) -> machine answer_correct (0/1)."""
    grades = {}
    for path in result_paths:
        case = _case_name(path)
        for r in json.load(open(path, encoding="utf-8")):
            grades[(case, str(_qid(r)))] = int(bool(r.get("answer_correct", 0)))
    return grades


def main():
    ap = argparse.ArgumentParser(description="Cohen's kappa for a completed grading sheet")
    ap.add_argument("--sheet", required=True, help="completed grading sheet CSV")
    ap.add_argument("--results", nargs="*", default=None,
                    help="original B3 result JSONs (default: from the sheet manifest)")
    ap.add_argument("--out", default=None, help="optional JSON summary path")
    args = ap.parse_args()

    sheet = Path(args.sheet)
    result_paths = args.results
    if not result_paths:
        man = sheet.with_suffix(".manifest.json")
        if not man.exists():
            sys.exit("ERROR: no --results given and no manifest found next to the sheet")
        result_paths = json.load(open(man, encoding="utf-8"))["files"]

    grades = load_original_grades(result_paths)

    human, machine, by_case = [], [], defaultdict(lambda: ([], []))
    missing, ungraded = 0, 0
    with open(sheet, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            case = (row.get("case") or "").strip()
            qid = str(row.get("Q#", "")).strip()
            hv = _yn(row.get("Correct (Y/N)", ""))
            if hv is None:
                ungraded += 1
                continue
            key = (case, qid)
            if key not in grades:
                missing += 1
                continue
            mv = grades[key]
            human.append(hv); machine.append(mv)
            by_case[case][0].append(hv); by_case[case][1].append(mv)

    if not human:
        sys.exit("ERROR: no graded rows matched the original results (check the sheet/manifest)")
    if ungraded:
        print(f"[warn] {ungraded} rows had no Y/N and were skipped")
    if missing:
        print(f"[warn] {missing} graded rows did not match any original grade and were skipped")

    kappa, agree = cohens_kappa(human, machine)
    print("=" * 56)
    print(f"Inter-annotator agreement (human vs machine grade)")
    print("=" * 56)
    print(f"  matched items:     {len(human)}")
    print(f"  raw agreement:     {agree*100:.1f}%")
    print(f"  Cohen's kappa:     {kappa:.3f}")
    if len(by_case) > 1:
        for case, (h, m) in sorted(by_case.items()):
            k, a = cohens_kappa(h, m)
            print(f"    case {case:>2}: n={len(h):<3} agree={a*100:5.1f}%  kappa={k:.3f}")
    print("=" * 56)

    if args.out:
        out = {"n": len(human), "raw_agreement": agree, "cohens_kappa": kappa,
               "per_case": {c: {"n": len(h), "kappa": cohens_kappa(h, m)[0],
                                "agreement": cohens_kappa(h, m)[1]}
                            for c, (h, m) in by_case.items()}}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
        print(f"  summary written to {args.out}")


if __name__ == "__main__":
    main()
