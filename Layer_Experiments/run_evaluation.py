#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Evaluation Runner (Appendix B)
=======================================
Runs all three baselines against the 50 curated Appendix B questions
using a deterministic judge instead of the LLM-based judge.

Usage:
  python run_evaluation.py --baseline b1          # B1: Naive RAG only
  python run_evaluation.py --baseline b2          # B2: SQL Retrieval only
  python run_evaluation.py --baseline b3          # B3: RCP only
  python run_evaluation.py --baseline all         # All three
  python run_evaluation.py --baseline b3 --limit 1  # Test with 1 question
"""

import argparse
import json
import logging
import sys

# Force UTF-8 output on Windows (avoids cp1252 errors from emoji in workflow logs)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJECT_ROOT / "Layer_Experiments" / "Baseline_RAG"))
sys.path.insert(0, str(PROJECT_ROOT / "Layer_Experiments" / "Baseline_SQL_Retrieval"))

from deterministic_judge import score_answer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("UNIFIED_EVAL")

RESULTS_DIR = Path(__file__).resolve().parent / "results_appendix_b"
RESULTS_DIR.mkdir(exist_ok=True)


def load_questions(path: str, limit: Optional[int] = None) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    if limit:
        questions = questions[:limit]
    return questions


# ═══════════════════════════════════════════════════════════════════════════
# B1: Naive RAG
# ═══════════════════════════════════════════════════════════════════════════

def run_b1(questions: List[Dict]) -> List[Dict]:
    """Run Naive RAG baseline using harvested.db."""
    from rag_baseline import RAGBaseline
    
    pipeline = RAGBaseline()
    pipeline.initialize()
    
    results = []
    total = len(questions)
    print(f"\n{'='*70}")
    print(f"  B1: NAIVE RAG — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        print(f"[{idx}/{total}] Q{q['id']}: {q['question'][:60]}...")
        
        try:
            start = time.time()
            rag_result = pipeline.query(q["question"])
            latency = round(time.time() - start, 2)
            answer = rag_result.get("answer", "")
        except Exception as e:
            logger.error(f"  B1 error Q{q['id']}: {e}")
            answer = ""
            latency = 0
        
        scores = score_answer(q["question"], answer, q["ground_truth"])
        record = {
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": latency,
            "baseline": "B1_RAG",
            **scores
        }
        results.append(record)
        
        mark = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {mark} correct={scores['answer_correct']} | latency={latency}s")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# B2: SQL-backed Retrieval
# ═══════════════════════════════════════════════════════════════════════════

def run_b2(questions: List[Dict]) -> List[Dict]:
    """Run SQL retrieval baseline."""
    sys.path.insert(0, str(PROJECT_ROOT / "Layer_Experiments" / "Baseline_SQL_Retrieval"))
    from sql_retrieval_baseline import SQLRetrievalBaseline
    
    pipeline = SQLRetrievalBaseline()
    pipeline.initialize()
    
    results = []
    total = len(questions)
    print(f"\n{'='*70}")
    print(f"  B2: SQL RETRIEVAL — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        print(f"[{idx}/{total}] Q{q['id']}: {q['question'][:60]}...")
        
        try:
            sql_result = pipeline.query(q["question"])
            answer = sql_result.get("answer", "")
            latency = sql_result.get("latency_s", 0)
        except Exception as e:
            logger.error(f"  B2 error Q{q['id']}: {e}")
            answer = ""
            latency = 0
        
        scores = score_answer(q["question"], answer, q["ground_truth"])
        record = {
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": latency,
            "baseline": "B2_SQL",
            **scores
        }
        results.append(record)
        
        mark = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {mark} correct={scores['answer_correct']} | latency={latency}s")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# B3: RCP Framework
# ═══════════════════════════════════════════════════════════════════════════

def run_b3(questions: List[Dict]) -> List[Dict]:
    """Run RCP framework evaluation."""
    from Layer_2_Agentic.logic.state_graph import get_graph
    from Layer_2_Agentic.logic.templates import populate_template_libraries
    from Layer_2_Agentic.logic.database_manager import DatabaseManager
    from Layer_2_Agentic.config.session_config import get_default_session_state, get_workflow_config
    
    populate_template_libraries()
    db = DatabaseManager()
    graph = get_graph()
    config = get_workflow_config()
    
    results = []
    total = len(questions)
    print(f"\n{'='*70}")
    print(f"  B3: RCP FRAMEWORK — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        print(f"[{idx}/{total}] Q{q['id']}: {q['question'][:60]}...")
        
        try:
            db.clear_all_sessions()
            start = time.time()
            forced_strategy = q.get("strategy")  # Use per-question strategy hint if provided
            init_state = get_default_session_state(query=q["question"], forced_strategy=forced_strategy)
            final_state = graph.invoke(init_state, config=config)
            latency = round(time.time() - start, 2)
            answer = final_state.get("finalAnswer", "No answer generated")
        except Exception as e:
            logger.error(f"  B3 error Q{q['id']}: {e}")
            answer = ""
            latency = 0
        
        scores = score_answer(q["question"], answer, q["ground_truth"])
        record = {
            "question_id": q["id"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": answer,
            "latency_s": latency,
            "baseline": "B3_RCP",
            "goal_satisfied": final_state.get("goalSatisfied", False) if 'final_state' in dir() else False,
            **scores
        }
        results.append(record)
        
        mark = "[OK]" if scores["answer_correct"] else "[--]"
        print(f"  {mark} correct={scores['answer_correct']} | latency={latency}s")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY + OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def print_summary(results: List[Dict], label: str):
    n = len(results)
    if n == 0:
        return
    
    correct = sum(r["answer_correct"] for r in results)
    citation = sum(r["citation_accurate"] for r in results)
    units = sum(r["unit_fidelity"] for r in results)
    halluc = sum(r["hallucination"] for r in results)
    avg_lat = sum(r["latency_s"] for r in results) / n
    
    print(f"\n{'='*70}")
    print(f"  {label} — SUMMARY ({n} questions)")
    print(f"{'='*70}")
    print(f"  Answer Correctness:  {correct}/{n} = {correct/n*100:.1f}%")
    print(f"  Citation Accuracy:   {citation}/{n} = {citation/n*100:.1f}%")
    print(f"  Unit Fidelity:       {units}/{n} = {units/n*100:.1f}%")
    print(f"  Hallucination Rate:  {halluc}/{n} = {halluc/n*100:.1f}%")
    print(f"  Avg Latency:         {avg_lat:.2f}s")
    print(f"{'='*70}\n")


def save_results(results: List[Dict], label: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"{label}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    # Also save as latest
    latest = RESULTS_DIR / f"{label}_latest.json"
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="Unified evaluation runner")
    parser.add_argument("--baseline", choices=["b1", "b2", "b3", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--questions", type=str, 
                       default=str(Path(__file__).resolve().parent / "test_questions_appendix_b.json"))
    args = parser.parse_args()
    
    questions = load_questions(args.questions, args.limit)
    print(f"\nLoaded {len(questions)} questions from {args.questions}\n")
    
    if args.baseline in ("b2", "all"):
        b2_results = run_b2(questions)
        print_summary(b2_results, "B2: SQL Retrieval")
        save_results(b2_results, "b2_sql")
    
    if args.baseline in ("b3", "all"):
        b3_results = run_b3(questions)
        print_summary(b3_results, "B3: RCP Framework")
        save_results(b3_results, "b3_rcp")
    
    if args.baseline in ("b1", "all"):
        b1_results = run_b1(questions)
        print_summary(b1_results, "B1: Naive RAG")
        save_results(b1_results, "b1_rag")


if __name__ == "__main__":
    sys.exit(main() or 0)
