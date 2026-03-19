#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agentic No-RCP Baseline Evaluator
=================================
Runs all test questions through the Agentic No-RCP baseline pipeline 
and collects metrics for the paper (Sections 5.2–5.4).
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Add Baseline_RAG to path so evaluate_rag can find its own local imports
RAG_BASELINE_DIR = PROJECT_ROOT / "Layer_Experiments" / "Baseline_RAG"
sys.path.insert(0, str(RAG_BASELINE_DIR))

# Import the baseline and the judge logic (reusing LLMJudge from evaluate_rag)
from Layer_Experiments.Baseline_Agentic_No_RCP.agentic_no_rcp_baseline import AgenticNoRCPBaseline
from Layer_Experiments.Baseline_RAG.evaluate_rag import LLMJudge, parse_test_questions

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AGENTIC_EVALUATOR")

# Results directory
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

def run_evaluation(
    questions: List[Dict[str, Any]],
    pipeline: AgenticNoRCPBaseline,
    judge: LLMJudge,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    
    if limit:
        questions = questions[:limit]
    
    total = len(questions)
    logger.info(f"Running evaluation on {total} questions")
    print(f"\n{'='*70}")
    print(f"  AGENTIC NO-RCP BASELINE EVALUATION — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        question_text = q["question"]
        ground_truth = q["ground_truth"]
        expert_comment = q.get("expert_comment", "")
        category = q.get("category", "?")
        
        print(f"[{idx}/{total}] Q{q_id} (Cat {category}): {question_text[:60]}...")
        
        if not ground_truth:
            print(f"  ⏭  Skipped (no ground truth)")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "answer": "",
                "skipped": True,
                "skip_reason": "No ground truth available",
            })
            continue
        
        # Run Agentic pipeline
        try:
            agent_result = pipeline.query(question_text)
        except Exception as e:
            logger.error(f"  Pipeline error for Q{q_id}: {e}")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "answer": "",
                "error": str(e),
                "skipped": True,
                "skip_reason": f"Pipeline error: {e}",
            })
            continue
        
        # Score with LLM judge
        try:
            scores = judge.score(
                question=question_text,
                rag_answer=agent_result["answer"],
                ground_truth=ground_truth,
                expert_comment=expert_comment,
            )
        except Exception as e:
            logger.error(f"  Judge error for Q{q_id}: {e}")
            scores = LLMJudge._default_scores(f"Judge error: {e}")
        
        # Combine result
        record = {
            "question_id": q_id,
            "category": category,
            "question": question_text,
            "ground_truth": ground_truth,
            "expert_comment": expert_comment,
            "answer": agent_result["answer"],
            "sources": agent_result["sources"],
            "latency_s": agent_result["latency_s"],
            "token_estimate": agent_result["token_estimate"],
            "prompt_tokens": agent_result["prompt_tokens"],
            "response_tokens": agent_result["response_tokens"],
            "steps_count": len(agent_result.get("steps", [])),
            "skipped": False,
            **scores,
        }
        results.append(record)
        
        # Status
        correct = "✅" if scores["answer_correct"] else "❌"
        halluc = "⚠️ Hallucination" if scores["hallucination"] else ""
        print(
            f"  {correct} Correct={scores['answer_correct']} | "
            f"Citation={scores['citation_accurate']} | "
            f"Units={scores['unit_fidelity']} | "
            f"Steps={len(agent_result.get('steps', []))} | "
            f"{halluc} | "
            f"{agent_result['latency_s']}s"
        )
    
    return results

def save_results(results: List[Dict[str, Any]], output_dir: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Full JSON
    json_path = output_dir / f"agentic_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Summary CSV
    csv_path = output_dir / f"agentic_summary_{timestamp}.csv"
    fieldnames = [
        "question_id", "category", "answer_correct",
        "citation_accurate", "unit_fidelity", "hallucination",
        "latency_s", "token_estimate", "steps_count"
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if not r.get("skipped", False):
                writer.writerow(r)

def print_summary(results: List[Dict[str, Any]]) -> None:
    evaluated = [r for r in results if not r.get("skipped", False)]
    n = len(evaluated)
    if n == 0: return

    correct = sum(r.get("answer_correct", 0) for r in evaluated)
    citation = sum(r.get("citation_accurate", 0) for r in evaluated)
    units = sum(r.get("unit_fidelity", 0) for r in evaluated)
    halluc = sum(r.get("hallucination", 0) for r in evaluated)
    
    avg_latency = sum(r.get("latency_s", 0) for r in evaluated) / n
    avg_tokens = sum(r.get("token_estimate", 0) for r in evaluated) / n
    avg_steps = sum(r.get("steps_count", 0) for r in evaluated) / n
    
    print(f"\n{'='*70}")
    print(f"  AGENTIC NO-RCP — EVALUATION SUMMARY")
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
    print(f"  │ Avg Steps/Query          │ {avg_steps:>7.1f}  │")
    print(f"  └──────────────────────────┴──────────┘")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", type=str, choices=["A", "B", "C", "D"])
    parser.add_argument("--questions-file", type=str, default=str(PROJECT_ROOT / "questions" / "test_questions_categorized.txt"))
    args = parser.parse_args()
    
    questions = parse_test_questions(args.questions_file)
    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    
    pipeline = AgenticNoRCPBaseline()
    judge = LLMJudge()
    
    results = run_evaluation(questions, pipeline, judge, limit=args.limit)
    save_results(results, RESULTS_DIR)
    print_summary(results)
    return 0

if __name__ == "__main__":
    sys.exit(main())
