"""
Unified evaluation runner for Saab Case II (B1 / B2 / B3).

Usage:
    python -m Layer_Experiments_Saab.run_evaluation_saab --baseline all
    python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b1
    python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b2
    python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b3
    python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b3 --limit 5
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)
QUESTIONS_FILE = HERE / "test_questions_saab.json"

# ── Import baselines ──────────────────────────────────────────────────────────
sys.path.insert(0, str(HERE.parent))
from Layer_Experiments_Saab.deterministic_judge_saab import judge


# ── Load questions ─────────────────────────────────────────────────────────────

def load_questions(limit: int | None = None) -> list[dict]:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        qs = json.load(f)
    return qs[:limit] if limit else qs


# ── Per-baseline runners ───────────────────────────────────────────────────────

def run_b1(questions: list[dict]) -> list[dict]:
    from Layer_Experiments_Saab.rag_baseline_saab import run_b1 as _run_b1

    results = []
    total = len(questions)
    for i, q in enumerate(questions, 1):
        print(f"[B1] Q{q['id']}/{total}: {q['question'][:70]}...")
        try:
            answer, latency = _run_b1(q["question"])
        except Exception as e:
            answer, latency = f"ERROR: {e}", 0.0

        scores = judge(q["question"], q["ground_truth"], answer)
        status = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {status} GT={q['ground_truth']!r}  Lat={latency:.1f}s")

        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": round(latency, 3),
            "baseline": "B1_RAG",
            **scores,
        })
    return results


def run_b2(questions: list[dict]) -> list[dict]:
    from Layer_Experiments_Saab.sql_retrieval_saab import run_b2 as _run_b2

    results = []
    total = len(questions)
    for i, q in enumerate(questions, 1):
        print(f"[B2] Q{q['id']}/{total}: {q['question'][:70]}...")
        try:
            answer, latency = _run_b2(q["question"])
        except Exception as e:
            answer, latency = f"ERROR: {e}", 0.0

        scores = judge(q["question"], q["ground_truth"], answer)
        status = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {status} GT={q['ground_truth']!r}  Lat={latency:.1f}s")

        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": round(latency, 3),
            "baseline": "B2_SQL",
            **scores,
        })
    return results


def run_b3(questions: list[dict]) -> list[dict]:
    from Layer_Experiments_Saab.rcp_baseline_saab import run_b3 as _run_b3

    results = []
    total = len(questions)
    for i, q in enumerate(questions, 1):
        print(f"[B3] Q{q['id']}/{total}: {q['question'][:70]}...")
        forced_strategy = q.get("strategy")
        try:
            answer, latency = _run_b3(q["question"], forced_strategy=forced_strategy)
        except Exception as e:
            answer, latency = f"ERROR: {e}", 0.0

        scores = judge(q["question"], q["ground_truth"], answer)
        status = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {status} GT={q['ground_truth']!r}  Lat={latency:.1f}s")

        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": round(latency, 3),
            "baseline": "B3_RCP",
            "forced_strategy": forced_strategy,
            **scores,
        })
    return results


# ── Save & summarise ───────────────────────────────────────────────────────────

def save_results(results: list[dict], tag: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"{tag}_{ts}.json"
    latest = RESULTS_DIR / f"{tag}_latest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {out_file}")
    return out_file


def print_summary(results: list[dict], label: str) -> None:
    n = len(results)
    if n == 0:
        return
    ac = sum(r["answer_correct"] for r in results) / n
    ca = sum(r["citation_accurate"] for r in results) / n
    uf = sum(r["unit_fidelity"] for r in results) / n
    hr = sum(1 for r in results if r["hallucination"]) / n
    lat = sum(r["latency_s"] for r in results) / n
    print(f"\n{'='*60}")
    print(f"  {label} — {n} questions")
    print(f"{'='*60}")
    print(f"  Answer Correctness : {ac:.1%}")
    print(f"  Citation Accuracy  : {ca:.1%}")
    print(f"  Unit Fidelity      : {uf:.1%}")
    print(f"  Hallucination Rate : {hr:.1%}")
    print(f"  Avg Latency        : {lat:.2f}s")
    print(f"{'='*60}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Saab Case II evaluation runner")
    parser.add_argument(
        "--baseline",
        choices=["b1", "b2", "b3", "all"],
        default="all",
        help="Which baseline to run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to first N questions (for quick testing)",
    )
    args = parser.parse_args()

    questions = load_questions(args.limit)
    print(f"Loaded {len(questions)} questions\n")

    run_all = args.baseline == "all"

    if run_all or args.baseline == "b1":
        t0 = time.time()
        r = run_b1(questions)
        print_summary(r, "B1: Naive RAG")
        save_results(r, "b1_rag")
        print(f"B1 total: {time.time()-t0:.0f}s")

    if run_all or args.baseline == "b2":
        t0 = time.time()
        r = run_b2(questions)
        print_summary(r, "B2: SQL Retrieval")
        save_results(r, "b2_sql")
        print(f"B2 total: {time.time()-t0:.0f}s")

    if run_all or args.baseline == "b3":
        t0 = time.time()
        r = run_b3(questions)
        print_summary(r, "B3: RCP")
        save_results(r, "b3_rcp")
        print(f"B3 total: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
