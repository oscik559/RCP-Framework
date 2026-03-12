#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Baseline Evaluator
======================
Runs all test questions through the RAG baseline pipeline and collects
metrics for the paper (Sections 5.2–5.4).

Metrics:
  - Answer Correctness (LLM-judge)
  - Citation Accuracy (heuristic + LLM-judge)
  - Unit Fidelity (LLM-judge)
  - Hallucination Detection (LLM-judge)
  - Latency and token counts
  - Error class categorization

Usage:
  python evaluate_rag.py               # Run all questions
  python evaluate_rag.py --limit 5     # Run first 5 questions
  python evaluate_rag.py --category A  # Run only Category A
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

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_baseline import RAGBaseline

from langchain_ollama import ChatOllama

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RAG_EVALUATOR")

# ---------------------------------------------------------------------------
# Results directory
# ---------------------------------------------------------------------------
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# QUESTION PARSER
# ═══════════════════════════════════════════════════════════════════════════

def parse_test_questions(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse test_questions_categorized.txt into structured question records.
    
    Returns list of dicts with keys:
      - id: question number
      - question: the question text (Column 1)
      - ground_truth: expected answer (Column 2)
      - expert_comment: domain expert feedback (Column 3, if present)
      - category: A, B, C, or D
      - difficulty: Easy, Medium, or Hard (inferred from category/type)
    """
    questions: List[Dict[str, Any]] = []
    current_category = "Unknown"
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Detect category headers
    category_map = {
        "CATEGORY A": "A",
        "CATEGORY B": "B",
        "CATEGORY C": "C",
        "CATEGORY D": "D",
    }
    
    # Split into question blocks
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for category header
        for header, cat_code in category_map.items():
            if header in line:
                current_category = cat_code
                break
        
        # Check for question start
        match = re.match(r"^Question\s+(\d+)\s*:", line)
        if match:
            q_id = int(match.group(1))
            question_text = ""
            ground_truth = ""
            expert_comment = ""
            
            # Read subsequent lines for Column 1, 2, 3
            i += 1
            while i < len(lines):
                cline = lines[i].strip()
                
                # Next question or category => stop
                if re.match(r"^Question\s+\d+\s*:", cline):
                    break
                if any(h in cline for h in category_map.keys()):
                    break
                if cline.startswith("=" * 10):
                    break
                
                if cline.startswith("Column 1:"):
                    question_text = cline[len("Column 1:"):].strip()
                elif cline.startswith("Column 2:"):
                    ground_truth = cline[len("Column 2:"):].strip()
                elif cline.startswith("Column 3:"):
                    expert_comment = cline[len("Column 3:"):].strip()
                
                i += 1
            
            # Skip questions without actual question text or ground truth
            if question_text and ground_truth:
                questions.append({
                    "id": q_id,
                    "question": question_text,
                    "ground_truth": ground_truth,
                    "expert_comment": expert_comment,
                    "category": current_category,
                })
            elif question_text and not ground_truth:
                # System-level / generic questions without ground truth
                questions.append({
                    "id": q_id,
                    "question": question_text,
                    "ground_truth": "",
                    "expert_comment": expert_comment,
                    "category": current_category,
                })
            
            continue  # Don't increment again
        
        i += 1
    
    logger.info(f"Parsed {len(questions)} questions from {filepath}")
    return questions


# ═══════════════════════════════════════════════════════════════════════════
# LLM-AS-JUDGE SCORING
# ═══════════════════════════════════════════════════════════════════════════

class LLMJudge:
    """
    Uses llama3.2 to score RAG answers against ground truth.
    
    Evaluates:
      1. Answer Correctness (0 or 1)
      2. Citation Accuracy (0 or 1) 
      3. Unit Fidelity (0 or 1)
      4. Hallucination (0 or 1)
    """
    
    def __init__(self, model: str = "llama3.2:latest"):
        self.llm = ChatOllama(model=model, temperature=0.0)
    
    def score(
        self,
        question: str,
        rag_answer: str,
        ground_truth: str,
        expert_comment: str = "",
    ) -> Dict[str, Any]:
        """
        Score a single RAG answer using LLM-as-judge.
        
        Returns dict with:
          - answer_correct: 0 or 1
          - citation_accurate: 0 or 1
          - unit_fidelity: 0 or 1
          - hallucination: 0 or 1
          - error_class: one of [none, hallucination, partial_answer, 
                                  field_mismatch, revision_error]
          - judge_reasoning: brief explanation
        """
        prompt = f"""You are an expert evaluator judging the quality of an AI-generated answer 
about hydraulic engineering products against a ground truth answer.

QUESTION: {question}

GROUND TRUTH ANSWER: {ground_truth}

{f'EXPERT COMMENT ON GROUND TRUTH: {expert_comment}' if expert_comment else ''}

AI-GENERATED ANSWER: {rag_answer}

Score the AI answer on these 4 criteria. For each, give a score of 0 or 1:

1. ANSWER_CORRECT: Does the AI answer convey the same core facts as the ground truth?
   1 = Substantially correct (even if not word-for-word identical)
   0 = Incorrect, misleading, or missing key information

2. CITATION_ACCURATE: Does the AI answer reference a specific product code, article number, 
   table, page, or section from the source documentation?
   1 = At least one specific, verifiable reference is provided
   0 = No specific references, or references are vague/generic

3. UNIT_FIDELITY: If the answer involves numerical values, units, or measurements — 
   are they correct and properly stated?
   1 = Units/values are correct, OR the answer has no numerical content
   0 = Units/values are wrong, missing, or improperly converted

4. HALLUCINATION: Does the AI answer contain factual claims NOT supported by the ground truth?
   1 = Contains at least one unsupported or fabricated claim
   0 = All claims are supported or the answer acknowledges limitations

5. ERROR_CLASS: If the answer is wrong, classify the primary error:
   - "none" if the answer is correct
   - "hallucination" if the model asserts false values
   - "partial_answer" if correct topic but missing required specificity
   - "field_mismatch" if correct source found but wrong field extracted
   - "revision_error" if wrong revision/version referenced

Respond ONLY in this exact JSON format (no extra text):
{{
  "answer_correct": 0 or 1,
  "citation_accurate": 0 or 1, 
  "unit_fidelity": 0 or 1,
  "hallucination": 0 or 1,
  "error_class": "none|hallucination|partial_answer|field_mismatch|revision_error",
  "judge_reasoning": "brief one-line explanation"
}}"""

        try:
            response = self.llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            
            # Extract JSON from response
            json_match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure all keys are present with defaults
                return {
                    "answer_correct": int(result.get("answer_correct", 0)),
                    "citation_accurate": int(result.get("citation_accurate", 0)),
                    "unit_fidelity": int(result.get("unit_fidelity", 1)),
                    "hallucination": int(result.get("hallucination", 0)),
                    "error_class": result.get("error_class", "unknown"),
                    "judge_reasoning": result.get("judge_reasoning", ""),
                }
            else:
                logger.warning(f"Could not parse judge response: {text[:200]}")
                return self._default_scores("Judge response not parseable")
                
        except Exception as e:
            logger.error(f"LLM judge error: {e}")
            return self._default_scores(f"Judge error: {str(e)}")
    
    @staticmethod
    def _default_scores(reason: str) -> Dict[str, Any]:
        return {
            "answer_correct": 0,
            "citation_accurate": 0,
            "unit_fidelity": 0,
            "hallucination": 0,
            "error_class": "unknown",
            "judge_reasoning": reason,
        }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN EVALUATION LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_evaluation(
    questions: List[Dict[str, Any]],
    pipeline: RAGBaseline,
    judge: LLMJudge,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate the RAG baseline on the provided questions.
    """
    results: List[Dict[str, Any]] = []
    
    if limit:
        questions = questions[:limit]
    
    total = len(questions)
    logger.info(f"Running evaluation on {total} questions")
    print(f"\n{'='*70}")
    print(f"  RAG BASELINE EVALUATION — {total} questions")
    print(f"{'='*70}\n")
    
    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        question_text = q["question"]
        ground_truth = q["ground_truth"]
        expert_comment = q.get("expert_comment", "")
        category = q.get("category", "?")
        
        print(f"[{idx}/{total}] Q{q_id} (Cat {category}): {question_text[:60]}...")
        
        # Skip questions without ground truth (system-level questions)
        if not ground_truth:
            print(f"  ⏭  Skipped (no ground truth)")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "rag_answer": "",
                "skipped": True,
                "skip_reason": "No ground truth available",
            })
            continue
        
        # Run RAG pipeline
        try:
            rag_result = pipeline.query(question_text)
        except Exception as e:
            logger.error(f"  Pipeline error for Q{q_id}: {e}")
            results.append({
                "question_id": q_id,
                "category": category,
                "question": question_text,
                "ground_truth": ground_truth,
                "rag_answer": "",
                "error": str(e),
                "skipped": True,
                "skip_reason": f"Pipeline error: {e}",
            })
            continue
        
        # Score with LLM judge
        try:
            scores = judge.score(
                question=question_text,
                rag_answer=rag_result["answer"],
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
            "rag_answer": rag_result["answer"],
            "sources": rag_result["sources"],
            "retrieved_chunks": rag_result["retrieved_chunks"],
            "latency_s": rag_result["latency_s"],
            "token_estimate": rag_result["token_estimate"],
            "prompt_tokens": rag_result["prompt_tokens"],
            "response_tokens": rag_result["response_tokens"],
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
            f"{halluc} | "
            f"{rag_result['latency_s']}s"
        )
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def save_results(results: List[Dict[str, Any]], output_dir: Path) -> None:
    """Save detailed JSON and summary CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ── Full JSON ─────────────────────────────────────────────────────
    json_path = output_dir / f"rag_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Full results saved to: {json_path}")
    
    # Also save as latest
    latest_json = output_dir / "rag_results.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # ── Summary CSV ───────────────────────────────────────────────────
    csv_path = output_dir / f"rag_summary_{timestamp}.csv"
    fieldnames = [
        "question_id", "category", "question", "answer_correct",
        "citation_accurate", "unit_fidelity", "hallucination",
        "error_class", "latency_s", "token_estimate", "judge_reasoning",
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if not r.get("skipped", False):
                writer.writerow(r)
    
    logger.info(f"Summary CSV saved to: {csv_path}")
    
    # Also save as latest
    latest_csv = output_dir / "rag_summary.csv"
    with open(latest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if not r.get("skipped", False):
                writer.writerow(r)


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print aggregate metrics to console."""
    evaluated = [r for r in results if not r.get("skipped", False)]
    n = len(evaluated)
    
    if n == 0:
        print("\nNo questions were evaluated.")
        return
    
    # Aggregate metrics
    correct = sum(r.get("answer_correct", 0) for r in evaluated)
    citation = sum(r.get("citation_accurate", 0) for r in evaluated)
    units = sum(r.get("unit_fidelity", 0) for r in evaluated)
    halluc = sum(r.get("hallucination", 0) for r in evaluated)
    
    avg_latency = sum(r.get("latency_s", 0) for r in evaluated) / n
    avg_tokens = sum(r.get("token_estimate", 0) for r in evaluated) / n
    total_tokens = sum(r.get("token_estimate", 0) for r in evaluated)
    
    # Error class distribution
    error_classes: Dict[str, int] = {}
    for r in evaluated:
        ec = r.get("error_class", "unknown")
        error_classes[ec] = error_classes.get(ec, 0) + 1
    
    # Per-category breakdown
    categories: Dict[str, List[Dict]] = {}
    for r in evaluated:
        cat = r.get("category", "?")
        categories.setdefault(cat, []).append(r)
    
    print(f"\n{'='*70}")
    print(f"  RAG BASELINE — EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Questions evaluated: {n}")
    print(f"  Questions skipped:  {len(results) - n}")
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
    print(f"  │ Total Tokens             │ {total_tokens:>7,}  │")
    print(f"  │ Avg Function Calls       │     ---  │")
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
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG baseline on test questions"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to first N questions (for quick testing)"
    )
    parser.add_argument(
        "--category", type=str, default=None, choices=["A", "B", "C", "D"],
        help="Filter to a specific question category"
    )
    parser.add_argument(
        "--questions-file", type=str,
        default=str(PROJECT_ROOT / "questions" / "test_questions_categorized.txt"),
        help="Path to test questions file"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=800,
        help="Chunk size for text splitting (default: 800)"
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="Number of chunks to retrieve (default: 5)"
    )
    args = parser.parse_args()
    
    # Parse questions
    questions = parse_test_questions(args.questions_file)
    
    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
        logger.info(f"Filtered to Category {args.category}: {len(questions)} questions")
    
    if not questions:
        print("No questions found. Check the questions file path.")
        return 1
    
    # Initialize RAG pipeline
    config = {
        "chunk_size": args.chunk_size,
        "top_k": args.top_k,
    }
    pipeline = RAGBaseline(config=config)
    pipeline.initialize()
    
    # Initialize LLM judge
    judge = LLMJudge()
    
    # Run evaluation
    results = run_evaluation(
        questions=questions,
        pipeline=pipeline,
        judge=judge,
        limit=args.limit,
    )
    
    # Save and summarize
    save_results(results, RESULTS_DIR)
    print_summary(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
