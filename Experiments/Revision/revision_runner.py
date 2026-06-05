#!/usr/bin/env python3
"""
Revision runner — execute one B3 configuration over the Case I query set (Task 2 core).

Wraps the *existing* Case I evaluation (`Experiments/Case_I/run_evaluation.py::run_b3`,
the real Layer-2 controller + deterministic judge) and exposes two knobs needed by the
revision experiments:

  * config       'full'    → validation gates ON  (RCP_DISABLE_VALIDATION=0)
                 'no_gate' → validation gates OFF (RCP_DISABLE_VALIDATION=1)  [B3- ablation]
  * temperature  overrides the Ollama generation temperature for this process by mutating
                 the in-memory CONFIG (0.0 = deterministic; 0.7 = the variance sweep).

Everything else — model (llama3.2:3b), harvested.db, strategies, functions, prompts,
embeddings (qwen3-embedding:8b) — is identical to the shipped Case I B3 evaluation.

Scope note: the gate-bypass flag lives in the Layer-2 controller, which is the B3 system
for *Case I*. Case II's B3 is a separate standalone pipeline
(`Experiments/Case_II/RCP_Framework/rcp_baseline_company_b.py`) and is not driven by this
flag; only Case I supports the no-gate ablation here.

CLI (single config; mainly for smoke-testing):
  python Experiments/Revision/revision_runner.py --config no_gate --temperature 0.0 --limit 2
"""

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CASE_I = PROJECT_ROOT / "Experiments" / "Case_I"
QUESTIONS = CASE_I / "test_questions.json"


def _set_temperature(temperature: float) -> None:
    """Override the Ollama temperature for every model tier (mutate CONFIG in place)."""
    from Layer_2_Agentic_Reasoning.config import config_loader
    for tier, cfg in config_loader.CONFIG.get("llms", {}).items():
        cfg["temperature"] = temperature


def run_config(config: str = "full", temperature: float = 0.0, seed: int = 0,
               limit=None, questions_path: Path = QUESTIONS):
    """Run Case I B3 under the given config; return per-query records (with metrics)."""
    if config not in ("full", "no_gate"):
        raise ValueError("config must be 'full' or 'no_gate'")

    # 1) gate flag (read at call time by the controller's validation nodes)
    os.environ["RCP_DISABLE_VALIDATION"] = "1" if config == "no_gate" else "0"

    # 2) make the Case I evaluation importable, then set temperature
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(CASE_I))
    _set_temperature(temperature)

    import run_evaluation as ev  # noqa: E402  (its import sets up the Case I paths)

    questions = json.load(open(questions_path, encoding="utf-8"))
    if limit:
        questions = questions[:limit]
    strat_by_id = {q["id"]: q.get("strategy", "") for q in questions}

    records = ev.run_b3(questions)
    for r in records:
        r["config"] = config
        r["temperature"] = temperature
        r["seed"] = seed
        r["strategy"] = strat_by_id.get(r.get("question_id"), "")
    return records


def _summary(records):
    n = len(records) or 1
    keys = ("answer_correct", "citation_accurate", "unit_fidelity", "hallucination")
    return {k: round(100 * sum(int(bool(r.get(k))) for r in records) / n, 1) for k in keys}


def main():
    ap = argparse.ArgumentParser(description="Run one Case I B3 configuration")
    ap.add_argument("--config", choices=["full", "no_gate"], default="full")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="optional path to write the per-query JSON")
    args = ap.parse_args()

    records = run_config(args.config, args.temperature, args.seed, args.limit)
    print(f"\nconfig={args.config} temp={args.temperature} seed={args.seed} "
          f"n={len(records)} -> {_summary(records)}")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump(records, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"records written to {args.out}")


if __name__ == "__main__":
    sys.exit(main())
