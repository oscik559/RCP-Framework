#!/usr/bin/env python3
"""
Multi-run variance + bootstrap-CI harness (Reviewer 2 #1; Task 2, reused by Task 8).

Runs a chosen Case I B3 configuration N times and aggregates:
  * per-metric mean ± SD across the N runs (answer correctness, citation accuracy,
    unit fidelity, hallucination rate), and
  * a percentile bootstrap 95% CI (10k resamples of the per-query binary labels) for
    answer correctness and hallucination.

Two modes:
  run  (default): execute the config live (needs Ollama + the pinned models).
       python Experiments/Revision/run_variance.py --config no_gate \
              --temperature 0.0 --repeats 3 --limit 100 --out Experiments/Revision/out

  from-results: skip execution and aggregate existing per-run result JSONs (no LLM) —
       useful for re-aggregating or for smoke tests.
       python Experiments/Revision/run_variance.py --from-results out/run_*.json

Outputs: per-run JSONs (run mode), a tidy long-format CSV (one row per run×metric), and
a JSON summary with mean/SD and bootstrap CIs. Run artefacts are namespaced by
config/temperature/seed so nothing is overwritten.
"""

import argparse
import csv
import glob
import json
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _stats import bootstrap_ci

METRICS = ["answer_correct", "citation_accurate", "unit_fidelity", "hallucination"]
BOOTSTRAP_METRICS = ["answer_correct", "hallucination"]


def labels(records, metric):
    return [int(bool(r.get(metric))) for r in records]


def rate(records, metric):
    return 100 * sum(labels(records, metric)) / (len(records) or 1)


def aggregate(runs, n_boot=10000):
    """runs: list of (tag, records). Return summary dict."""
    summary = {"n_runs": len(runs), "per_run": [], "metrics": {}}
    for tag, recs in runs:
        summary["per_run"].append({"tag": tag, "n": len(recs),
                                    **{m: round(rate(recs, m), 1) for m in METRICS}})
    for m in METRICS:
        per_run_rates = [rate(recs, m) for _, recs in runs]
        mean = statistics.mean(per_run_rates) if per_run_rates else 0.0
        sd = statistics.pstdev(per_run_rates) if len(per_run_rates) > 1 else 0.0
        entry = {"mean": round(mean, 1), "sd": round(sd, 2)}
        if m in BOOTSTRAP_METRICS and runs:
            # bootstrap CI on the per-query labels of each run; report run-0 + range
            cis = []
            for _, recs in runs:
                pt, lo, hi = bootstrap_ci(labels(recs, m), n_boot=n_boot)
                cis.append((100 * pt, 100 * lo, 100 * hi))
            entry["bootstrap_ci_run0"] = [round(cis[0][1], 1), round(cis[0][2], 1)]
            entry["bootstrap_ci_all"] = [[round(c[1], 1), round(c[2], 1)] for c in cis]
        summary["metrics"][m] = entry
    return summary


def write_outputs(summary, runs, out_dir, label):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # tidy long CSV
    csv_path = out / f"variance_{label}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "metric", "rate_pct"])
        for tag, recs in runs:
            for m in METRICS:
                w.writerow([tag, m, round(rate(recs, m), 1)])
    json_path = out / f"variance_{label}.summary.json"
    json.dump(summary, open(json_path, "w", encoding="utf-8"), indent=2)
    return csv_path, json_path


def print_summary(summary, label):
    print("=" * 64)
    print(f"Variance summary [{label}] — {summary['n_runs']} run(s)")
    print("=" * 64)
    print(f"  {'metric':<20}{'mean%':>8}{'SD':>8}   bootstrap 95% CI (run0)")
    for m in METRICS:
        e = summary["metrics"][m]
        ci = e.get("bootstrap_ci_run0")
        ci_s = f"[{ci[0]}, {ci[1]}]" if ci else ""
        print(f"  {m:<20}{e['mean']:>8}{e['sd']:>8}   {ci_s}")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser(description="Multi-run variance + bootstrap CI")
    ap.add_argument("--from-results", nargs="+", default=None,
                    help="aggregate existing per-run JSONs instead of executing")
    ap.add_argument("--config", choices=["full", "no_gate"], default="full")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0, help="base seed; run r uses seed+r")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default="Experiments/Revision/out")
    ap.add_argument("--n-boot", type=int, default=10000)
    args = ap.parse_args()

    runs = []
    if args.from_results:
        paths = []
        for pat in args.from_results:
            paths.extend(sorted(glob.glob(pat)) or [pat])
        for p in paths:
            runs.append((Path(p).stem, json.load(open(p, encoding="utf-8"))))
        label = "from_results"
    else:
        from revision_runner import run_config
        for r in range(args.repeats):
            seed = args.seed + r
            tag = f"{args.config}_t{args.temperature}_s{seed}"
            print(f"\n>>> run {r+1}/{args.repeats}: {tag}")
            recs = run_config(args.config, args.temperature, seed, args.limit)
            Path(args.out).mkdir(parents=True, exist_ok=True)
            json.dump(recs, open(Path(args.out) / f"run_{tag}.json", "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            runs.append((tag, recs))
        label = f"{args.config}_t{args.temperature}"

    if not runs:
        sys.exit("no runs to aggregate")
    summary = aggregate(runs, n_boot=args.n_boot)
    csv_path, json_path = write_outputs(summary, runs, args.out, label)
    print_summary(summary, label)
    print(f"  CSV     -> {csv_path}")
    print(f"  summary -> {json_path}")


if __name__ == "__main__":
    main()
