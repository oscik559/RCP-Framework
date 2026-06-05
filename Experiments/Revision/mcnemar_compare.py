#!/usr/bin/env python3
"""
McNemar comparison utility (Reviewer 2 #2 — ablation statistics; Task 3).

Takes two result files containing matched per-query binary judgements and reports
McNemar's chi-square, p-value, and the Wilson (Newcombe) 95% CI on the matched-
proportion change — the same method used in the paper's significance table. The
intended use is comparing the full system (B3) against the no-gate ablation (B3-),
but it works for any two matched result files.

Inputs are JSON lists of per-query records that share a question id and contain the
metric field (default: answer_correct). Records are matched by question id so the
two files may be in any order, but they must cover the same questions.

Usage:
  python Experiments/Revision/mcnemar_compare.py \
      --a Experiments/Case_I/results/b3_rcp_latest.json \
      --b Experiments/Revision/out/b3_nogate.json \
      --metric answer_correct --label-a B3 --label-b "B3- (no-gate)"

Smoke test (no LLM needed): compare the two shipped baselines, e.g.
  --a .../b2_sql_latest.json --b .../b3_rcp_latest.json
"""

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _stats import mcnemar_chi2, discordant_counts, newcombe_paired_diff_ci, wilson_ci


def _qid(rec):
    for k in ("question_id", "id", "Q#", "qid"):
        if k in rec:
            return rec[k]
    raise KeyError("no question id field in record")


def _to_int(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip().lower()
    return 1 if s in ("1", "true", "yes", "y") else 0


def load_labels(path: str, metric: str):
    data = json.load(open(path, encoding="utf-8"))
    return {_qid(r): _to_int(r.get(metric, 0)) for r in data}


def main():
    ap = argparse.ArgumentParser(description="McNemar + Wilson CI for two matched result files")
    ap.add_argument("--a", required=True, help="result JSON for system A")
    ap.add_argument("--b", required=True, help="result JSON for system B")
    ap.add_argument("--metric", default="answer_correct",
                    help="binary field to compare (answer_correct, hallucination, ...)")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--out", default=None, help="optional path to write a JSON summary")
    args = ap.parse_args()

    la = load_labels(args.a, args.metric)
    lb = load_labels(args.b, args.metric)
    shared = sorted(set(la) & set(lb), key=lambda x: (str(type(x)), x))
    if not shared:
        sys.exit("ERROR: no shared question ids between the two files")
    only_a, only_b = set(la) - set(lb), set(lb) - set(la)
    if only_a or only_b:
        print(f"[warn] {len(only_a)} ids only in A, {len(only_b)} only in B — using {len(shared)} matched pairs")

    a = [la[q] for q in shared]
    b = [lb[q] for q in shared]
    n = len(shared)

    n11, n10, n01, n00 = discordant_counts(a, b)
    chi, p = mcnemar_chi2(n10, n01)
    delta, lo, hi = newcombe_paired_diff_ci(a, b)
    pa = sum(a) / n
    pb = sum(b) / n
    la_lo, la_hi = wilson_ci(sum(a), n)
    lb_lo, lb_hi = wilson_ci(sum(b), n)

    print("=" * 64)
    print(f"McNemar comparison on '{args.metric}'  (n = {n} matched pairs)")
    print("=" * 64)
    print(f"  {args.label_a}: {pa*100:5.1f}%   95% CI [{la_lo*100:.1f}, {la_hi*100:.1f}]")
    print(f"  {args.label_b}: {pb*100:5.1f}%   95% CI [{lb_lo*100:.1f}, {lb_hi*100:.1f}]")
    print(f"  discordant cells:  A>B (1,0) = {n10}   B>A (0,1) = {n01}")
    print(f"  Δ ({args.label_b} − {args.label_a}) = {delta*100:+.1f} pp"
          f"   95% CI [{lo*100:+.1f}, {hi*100:+.1f}]")
    sig = "n.s." if p >= 0.05 else ("p<0.001" if p < 0.001 else f"p={p:.3f}")
    print(f"  McNemar χ² = {chi:.2f}   p = {p:.4f}   ({sig})")
    print("=" * 64)

    if args.out:
        summary = {
            "metric": args.metric, "n": n,
            "label_a": args.label_a, "rate_a": pa, "ci_a": [la_lo, la_hi],
            "label_b": args.label_b, "rate_b": pb, "ci_b": [lb_lo, lb_hi],
            "discordant_a_over_b": n10, "discordant_b_over_a": n01,
            "delta": delta, "delta_ci": [lo, hi],
            "mcnemar_chi2": chi, "p_value": p,
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump(summary, open(args.out, "w", encoding="utf-8"), indent=2)
        print(f"  summary written to {args.out}")


if __name__ == "__main__":
    main()
