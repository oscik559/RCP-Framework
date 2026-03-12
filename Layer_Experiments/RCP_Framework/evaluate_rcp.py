#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RCP Framework Evaluator
======================
Runs all test questions through the full RCP-enabled agentic pipeline.
Uses the same LLM-as-judge scoring as the baselines for comparison.
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
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# Add Baseline_RAG for LLMJudge reuse
sys.path.insert(0, str(PROJECT_ROOT / "Layer_Experiments" / "Baseline_RAG"))

from evaluate_rag import parse_test_questions, LLMJudge
from Layer_2_Agentic.logic.state_graph import get_graph
from Layer_2_Agentic.logic.templates import populate_template_libraries
from Layer_2_Agentic.logic.database_manager import DatabaseManager
from Layer_2_Agentic.config.session_config import get_default_session_state, get_workflow_config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RCP_EVALUATOR")

# ---------------------------------------------------------------------------
# Results directory
# ---------------------------------------------------------------------------
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

class RCPRunner:
    def __init__(self):
        populate_template_libraries()
        self.db = DatabaseManager()
        self.graph = get_graph()
        self.config = get_workflow_config()

    def query(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # Clear sessions for transparency and fresh start
        self.db.clear_all_sessions()
        
        init_state = get_default_session_state(query=user_query)
        
        # Execute RCP Graph
        final_state = self.graph.invoke(init_state, config=self.config)
        
        latency = time.time() - start_time
        
        # Extract metrics from RCP state/database
        # In the RCP system, we can count actual tool calls from the DB
        # But for this evaluation, we'll keep it simple and extract from final_state
        
        return {
            "answer": final_state.get("finalAnswer", "No answer generated"),
            "latency_s": round(latency, 2),
            "goal_satisfied": final_state.get("goalSatisfied", False),
            "strategy_satisfied": final_state.get("strategySatisfied", False),
            "session_id": final_state.get("sessionID"),
            # Mocking token counts for now as the direct graph invoke doesn't return them easily without wraps
            # We can use estimates or instrumentation later
            "token_estimate": 0 
        }

def run_evaluation(
    questions: List[Dict[str, Any]],
    runner: RCPRunner,
    judge: LLMJudge,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results = []
    if limit:
        questions = questions[:limit]
    
    total = len(questions)
    print(f"\n{'='*70}")
    print(f"  RCP FRAMEWORK EVALUATION — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        question_text = q["question"]
        ground_truth = q["ground_truth"]
        category = q.get("category", "?")
        
        print(f"[{idx}/{total}] Q{q_id} (Cat {category}): {question_text[:60]}...")
        
        if not ground_truth:
            print(f"  ⏭  Skipped (no ground truth)")
            continue
            
        try:
            rcp_result = runner.query(question_text)
            scores = judge.score(
                question=question_text,
                rag_answer=rcp_result["answer"],
                ground_truth=ground_truth,
                expert_comment=q.get("expert_comment", "")
            )
            
            record = {
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "rcp_answer": rcp_result["answer"],
                "latency_s": rcp_result["latency_s"],
                "goal_satisfied": rcp_result["goal_satisfied"],
                "token_estimate": 0,
                **scores
            }
            results.append(record)
            
            correct = "✅" if scores["answer_correct"] else "❌"
            print(f"  {correct} Correct={scores['answer_correct']} | Latency={rcp_result['latency_s']}s")
            
        except Exception as e:
            logger.error(f"Error on Q{q_id}: {e}")
            
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--questions-file", type=str, default=str(PROJECT_ROOT / "questions" / "test_questions_categorized.txt"))
    args = parser.parse_args()
    
    questions = parse_test_questions(args.questions_file)
    
    runner = RCPRunner()
    judge = LLMJudge()
    
    results = run_evaluation(questions, runner, judge, limit=args.limit)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"rcp_results_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save latest
    with open(RESULTS_DIR / "rcp_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    main()
