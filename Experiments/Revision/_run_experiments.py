#!/usr/bin/env python3
"""
Driver for the revision experiments (run on this machine).

Order (ablation first — the headline Reviewer 2 #2 result — then the variance sweep):

  1. Case I  B3-  (no_gate, temp 0, 100q)          -> out/run_no_gate_t0.0_s0.json
  2. Case II B3-  (no_gate, temp 0, 100q)          -> out/run_caseII_no_gate.json
  3. Case I  B3   (full, temp 0.7, 3 repeats)      -> out/run_full_t0.7_s{0,1,2}.json

The matched B3 (full, temp 0) arm for the ablation McNemar is the shipped
results/b3_rcp_latest.json of each case (reproduces the paper), so it is not re-run.

Case II reads the confidential Company B DB; this script points COMPANY_B_DB_PATH at the
local root ./harvested.db. All outputs land in out/ (git-ignored), so nothing confidential
is committed. Case II runs at temperature 0 only (its pipeline does not plumb temperature),
so the temperature-0.7 variance sweep is Case I.

Usage:  python Experiments/Revision/_run_experiments.py
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))

# Point Case II at the local (git-ignored) Company B database before any Case II import.
os.environ.setdefault("COMPANY_B_DB_PATH", str(PROJECT_ROOT / "harvested.db"))


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def save(recs, name):
    json.dump(recs, open(OUT / name, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    n = len(recs)
    correct = round(100 * sum(int(bool(r.get("answer_correct"))) for r in recs) / (n or 1), 1)
    log(f"saved {name}  (n={n}, correctness={correct}%)")


def run_case2_no_gate(limit=None):
    """Case II B3 with gates off (RCP_DISABLE_VALIDATION=1)."""
    os.environ["RCP_DISABLE_VALIDATION"] = "1"
    sys.path.insert(0, str(PROJECT_ROOT / "Experiments" / "Case_II"))
    import run_evaluation_company_b as ev2
    questions = ev2.load_questions(limit)
    recs = ev2.run_b3(questions)
    for r in recs:
        r["config"] = "no_gate"
        r["case"] = "II"
    return recs


def main():
    from revision_runner import run_config
    t0 = time.time()

    log("RUN 1/5: Case I  B3- (no_gate, temp 0, 100q)")
    save(run_config("no_gate", 0.0, 0, None), "run_no_gate_t0.0_s0.json")

    log("RUN 2/5: Case II B3- (no_gate, temp 0, 100q)")
    try:
        save(run_case2_no_gate(None), "run_caseII_no_gate.json")
    except Exception as e:
        log(f"Case II no_gate FAILED: {e!r} (continuing with Case I variance)")

    for r in range(3):
        log(f"RUN {r + 3}/5: Case I B3 (full, temp 0.7, repeat {r + 1}/3)")
        save(run_config("full", 0.7, r, None), f"run_full_t0.7_s{r}.json")

    (OUT / "_DONE.marker").write_text(f"done in {time.time() - t0:.0f}s")
    log(f"ALL DONE in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
