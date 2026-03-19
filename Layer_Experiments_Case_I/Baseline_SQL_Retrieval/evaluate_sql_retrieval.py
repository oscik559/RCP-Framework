#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL-backed Retrieval Evaluator (B2)
====================================
Runs test questions through the SQL retrieval baseline and collects
metrics using the same LLM-as-judge framework as the RAG evaluator.

Usage:
  python evaluate_sql_retrieval.py               # Run all questions
  python evaluate_sql_retrieval.py --limit 5      # First 5 questions
  python evaluate_sql_retrieval.py --category A   # Category A only
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJECT_ROOT / "Layer_Experiments" / "Baseline_RAG"))

from sql_retrieval_baseline import SQLRetrievalBaseline
from evaluate_rag import parse_test_questions, LLMJudge

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SQL_EVALUATOR")

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# EVALUATION LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_evaluation(
    questions: List[Dict[str, Any]],
    pipeline: SQLRetrievalBaseline,
    judge: LLMJudge,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    if limit:
        questions = questions[:limit]

    total = len(questions)
    logger.info(f"Running evaluation on {total} questions")
    print(f"\n{'='*70}")
    print(f"  SQL RETRIEVAL BASELINE (B2) — {total} questions")
    print(f"{'='*70}\n")

    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        question_text = q["question"]
        ground_truth = q["ground_truth"]
        expert_comment = q.get("expert_comment", "")
        category = q.get("category", "?")

        print(f"[{idx}/{total}] Q{q_id} (Cat {category}): {question_text[:60]}...")

        if not ground_truth:
            print("  ⏭  Skipped (no ground truth)")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "sql_answer": "",
                "skipped": True,
                "skip_reason": "No ground truth available",
            })
            continue

        # Run SQL retrieval pipeline
        try:
            sql_result = pipeline.query(question_text)
        except Exception as e:
            logger.error(f"  Pipeline error for Q{q_id}: {e}")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "sql_answer": "",
                "error": str(e),
                "skipped": True,
                "skip_reason": f"Pipeline error: {e}",
            })
            continue

        # Score with LLM judge
        try:
            scores = judge.score(
                question=question_text,
                rag_answer=sql_result["answer"],
                ground_truth=ground_truth,
                expert_comment=expert_comment,
            )
        except Exception as e:
            logger.error(f"  Judge error for Q{q_id}: {e}")
            scores = LLMJudge._default_scores(f"Judge error: {e}")

        record = {
            "question_id": q_id,
            "category": category,
            "question": question_text,
            "ground_truth": ground_truth,
            "expert_comment": expert_comment,
            "sql_answer": sql_result["answer"],
            "products_found": sql_result["products_found"],
            "families_found": sql_result["families_found"],
            "knowledge_found": sql_result["knowledge_found"],
            "latency_s": sql_result["latency_s"],
            "token_estimate": sql_result["token_estimate"],
            "prompt_tokens": sql_result["prompt_tokens"],
            "response_tokens": sql_result["response_tokens"],
            "skipped": False,
            **scores,
        }
        results.append(record)

        correct = "✅" if scores["answer_correct"] else "❌"
        halluc = "⚠️ Hallucination" if scores["hallucination"] else ""
        print(
            f"  {correct} Correct={scores['answer_correct']} | "
            f"Citation={scores['citation_accurate']} | "
            f"Units={scores['unit_fidelity']} | "
            f"{halluc} | "
            f"Products={sql_result['products_found']} | "
            f"{sql_result['latency_s']}s"
        )

    return results


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def save_results(results: List[Dict[str, Any]], output_dir: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"sql_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Full results: {json_path}")

    latest_json = output_dir / "sql_results.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    csv_path = output_dir / f"sql_summary_{timestamp}.csv"
    fieldnames = [
        "question_id", "category", "question", "answer_correct",
        "citation_accurate", "unit_fidelity", "hallucination",
        "error_class", "latency_s", "token_estimate", "products_found",
        "families_found", "judge_reasoning",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if not r.get("skipped", False):
                writer.writerow(r)
    logger.info(f"Summary CSV: {csv_path}")


def print_summary(results: List[Dict[str, Any]]) -> None:
    evaluated = [r for r in results if not r.get("skipped", False)]
    n = len(evaluated)

    if n == 0:
        print("\nNo questions were evaluated.")
        return

    correct = sum(r.get("answer_correct", 0) for r in evaluated)
    citation = sum(r.get("citation_accurate", 0) for r in evaluated)
    units = sum(r.get("unit_fidelity", 0) for r in evaluated)
    halluc = sum(r.get("hallucination", 0) for r in evaluated)
    avg_latency = sum(r.get("latency_s", 0) for r in evaluated) / n
    avg_tokens = sum(r.get("token_estimate", 0) for r in evaluated) / n
    avg_products = sum(r.get("products_found", 0) for r in evaluated) / n

    error_classes: Dict[str, int] = {}
    for r in evaluated:
        ec = r.get("error_class", "unknown")
        error_classes[ec] = error_classes.get(ec, 0) + 1

    categories: Dict[str, List[Dict]] = {}
    for r in evaluated:
        cat = r.get("category", "?")
        categories.setdefault(cat, []).append(r)

    print(f"\n{'='*70}")
    print(f"  SQL RETRIEVAL BASELINE (B2) — EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Questions evaluated: {n}")
    print(f"\n  ┌──────────────────────────┬──────────┬──────────┐")
    print(f"  │ Metric                   │ Count    │ Rate     │")
    print(f"  ├──────────────────────────┼──────────┼──────────┤")
    print(f"  │ Answer Correctness       │ {correct:>4}/{n:<4} │ {correct/n*100:>6.1f}%  │")
    print(f"  │ Citation Accuracy        │ {citation:>4}/{n:<4} │ {citation/n*100:>6.1f}%  │")
    print(f"  │ Unit Fidelity            │ {units:>4}/{n:<4} │ {units/n*100:>6.1f}%  │")
    print(f"  │ Hallucination Rate ↓     │ {halluc:>4}/{n:<4} │ {halluc/n*100:>6.1f}%  │")
    print(f"  └──────────────────────────┴──────────┴──────────┘")
    print(f"\n  ┌──────────────────────────┬──────────┐")
    print(f"  │ Operational Cost         │ Value    │")
    print(f"  ├──────────────────────────┼──────────┤")
    print(f"  │ Avg Latency (s)          │ {avg_latency:>7.2f}  │")
    print(f"  │ Avg Tokens/Query         │ {avg_tokens:>7.0f}  │")
    print(f"  │ Avg Products Retrieved   │ {avg_products:>7.1f}  │")
    print(f"  │ Avg Function Calls       │     1–2  │")
    print(f"  └──────────────────────────┴──────────┘")

    print(f"\n  Error Class Distribution:")
    for ec, count in sorted(error_classes.items(), key=lambda x: -x[1]):
        print(f"    {ec:<25} {count:>3} ({count/n*100:.1f}%)")

    print(f"\n  Per-Category Breakdown:")
    for cat in sorted(categories.keys()):
        cat_results = categories[cat]
        cat_n = len(cat_results)
        cat_correct = sum(r.get("answer_correct", 0) for r in cat_results)
        cat_halluc = sum(r.get("hallucination", 0) for r in cat_results)
        print(
            f"    Category {cat}: {cat_n:>2} questions | "
            f"Correct: {cat_correct}/{cat_n} ({cat_correct/cat_n*100:.0f}%) | "
            f"Halluc: {cat_halluc}/{cat_n}"
        )

    print(f"\n{'='*70}\n")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate SQL retrieval baseline on test questions"
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", type=str, default=None, choices=["A", "B", "C", "D"])
    parser.add_argument(
        "--questions-file", type=str,
        default=str(PROJECT_ROOT / "questions" / "test_questions_categorized.txt"),
    )
    args = parser.parse_args()

    questions = parse_test_questions(args.questions_file)

    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
        logger.info(f"Filtered to Category {args.category}: {len(questions)} questions")

    if not questions:
        print("No questions found.")
        return 1

    pipeline = SQLRetrievalBaseline()
    pipeline.initialize()
    judge = LLMJudge()

    results = run_evaluation(questions, pipeline, judge, limit=args.limit)
    save_results(results, RESULTS_DIR)
    print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
