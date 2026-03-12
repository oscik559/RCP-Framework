#!/usr/bin/env python3
"""
Deterministic Judge for Hydroscand Evaluation
=============================================
Scores answers by checking if ground truth values appear in the response.
Much more reliable than LLM-based judging for factual product spec queries.
"""

import re
from typing import Dict, Any


def normalize_number(s: str) -> str:
    """Normalize Swedish/European number formats (comma → dot)."""
    return s.replace(",", ".").strip()


def extract_numbers(text: str) -> list:
    """Extract all numeric values from text."""
    # Match decimals, integers, and fractions
    nums = re.findall(r'\d+[.,]?\d*', text)
    return [normalize_number(n) for n in nums]


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = text.replace(",", ".")
    text = text.replace("''", '"').replace("''", '"').replace("'", '"')
    text = re.sub(r'\s+', ' ', text)
    return text


def score_answer(question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
    """
    Score an answer against ground truth using deterministic matching.
    
    Returns dict with:
        - answer_correct (0/1): GT value found in answer
        - citation_accurate (0/1): Article number mentioned
        - unit_fidelity (0/1): Correct units used
        - hallucination (0/1): Answer contains claims not in GT
    """
    if not answer or answer.strip() == "" or "No strategies" in answer or "No answer" in answer:
        return {
            "answer_correct": 0,
            "citation_accurate": 0,
            "unit_fidelity": 0,
            "hallucination": 0,
            "judge_reasoning": "Empty or failed answer"
        }
    
    ans_norm = normalize_text(answer)
    gt_norm = normalize_text(ground_truth)
    q_norm = normalize_text(question)
    
    # --- Answer Correctness ---
    # Extract key values from ground truth
    gt_numbers = extract_numbers(ground_truth)
    ans_numbers = extract_numbers(answer)
    
    correct = 0
    # Check if GT value(s) appear in answer
    if "vs" in gt_norm or "vs." in gt_norm:
        # Comparison question — both values must appear
        parts = re.split(r'\s+vs\.?\s+', gt_norm)
        values_found = 0
        for part in parts:
            part_nums = extract_numbers(part)
            for pn in part_nums:
                if pn in ans_numbers:
                    values_found += 1
        if values_found >= len(parts):
            correct = 1
    elif gt_numbers:
        # Single or multi-value — check if primary values present
        matches = sum(1 for gn in gt_numbers if gn in ans_numbers)
        if matches >= len(gt_numbers):
            correct = 1
        elif matches > 0 and len(gt_numbers) == 1:
            correct = 1
    else:
        # Text-based GT (e.g., article numbers)
        if gt_norm in ans_norm:
            correct = 1
    
    # Also check for article number in GT appearing in answer
    article_match = re.findall(r'\d{4}-\d{2}-\d{2}', ground_truth)
    if article_match:
        if any(a in answer for a in article_match):
            correct = 1
    
    # --- Citation Accuracy ---
    # Check if the article number from the question appears in the answer
    q_articles = re.findall(r'\d{4}-\d{2,3}-\d{2,3}(?:-\d{2})?', question)
    citation = 0
    if q_articles:
        citation = 1 if any(a in answer for a in q_articles) else 0
    else:
        citation = 1  # No specific article to cite
    
    # --- Unit Fidelity ---
    unit_ok = 1
    # Check if answer uses correct units when GT has units
    unit_patterns = {
        "mpa": r'(?:mpa|MPa)',
        "mm": r'(?:mm|millimeter)',
        "kg/m": r'(?:kg/m|kg per meter)',
        "''": r'(?:"|inch|tum|\'\')',
    }
    for unit_key, pattern in unit_patterns.items():
        if unit_key in gt_norm:
            if not re.search(pattern, answer, re.IGNORECASE):
                unit_ok = 0
                break
    
    # --- Hallucination ---
    halluc = 0
    # Check if answer contains values significantly different from GT
    if correct == 0 and ans_numbers and gt_numbers:
        # Answer has numbers but none match GT — possible hallucination
        halluc = 1
    
    return {
        "answer_correct": correct,
        "citation_accurate": citation,
        "unit_fidelity": unit_ok,
        "hallucination": halluc,
        "judge_reasoning": f"GT nums: {gt_numbers}, Ans nums: {ans_numbers}, correct={correct}"
    }
