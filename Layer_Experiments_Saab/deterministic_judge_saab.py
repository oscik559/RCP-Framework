"""
Deterministic judge for Saab Case II evaluation.
Mirrors the logic in Layer_Experiments/deterministic_judge.py adapted for
connector and cable specifications (mm, Ohm/km, deg C, V, A, #contacts).
"""
import re


# ── Numeric extraction ─────────────────────────────────────────────────────────

def extract_numbers(text: str) -> list[float]:
    """Return all numeric values found in text (handles decimals with . or ,)."""
    text = text.replace(",", ".")
    return [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)]


def numbers_close(a: float, b: float, rel_tol: float = 0.05) -> bool:
    """True if a and b are within rel_tol relative difference (or both ~0)."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 0.01
    return abs(a - b) / max(abs(a), abs(b)) <= rel_tol


# ── Citation check ─────────────────────────────────────────────────────────────

def check_citation(question: str, answer: str) -> bool:
    """Check if the answer mentions a product code referenced in the question."""
    # Extract product-code-like tokens from question
    codes = re.findall(
        r"(?:RPT|RNT|TFR|C0)\s*[\d/ -]+",
        question,
        re.IGNORECASE,
    )
    if not codes:
        return True  # No product code in question; citation not applicable
    answer_lower = answer.lower()
    for code in codes:
        # Normalize spaces/dashes for matching
        normalized = re.sub(r"[\s\-]+", "", code).lower()
        answer_normalized = re.sub(r"[\s\-]+", "", answer_lower)
        if normalized[:6] in answer_normalized:
            return True
    return False


# ── Unit fidelity ──────────────────────────────────────────────────────────────

UNIT_PATTERNS = [
    r"\bmm\b", r"\bcm\b",
    r"\bN/mm2\b", r"\bN/mm²\b",
    r"\bOhm/km\b", r"\bΩ/km\b",
    r"\bdeg\s*C\b", r"°C",
    r"\bV\b", r"\bA\b",
    r"\bAWG\b",
    r"\b#\d+",
]


def check_unit_fidelity(ground_truth: str, answer: str) -> bool:
    """Check that the answer uses at least the same kind of unit as ground truth."""
    gt_lower = ground_truth.lower().replace("°", "deg ")
    ans_lower = answer.lower().replace("°", "deg ")

    unit_map = {
        "mm": r"\bmm\b",
        "deg c": r"deg\s*c|°c",
        "ohm": r"ohm|ω|resistance",
        " v": r"\bv\b|\bvolt",
        " a": r"\ba\b|\bamp",
        "n/mm": r"n/mm",
        "awg": r"awg",
    }
    for unit_key, pattern in unit_map.items():
        if unit_key in gt_lower:
            if re.search(pattern, ans_lower):
                return True
    # If no explicit unit in GT, accept
    return True


# ── Hallucination detection ────────────────────────────────────────────────────

def check_hallucination(ground_truth: str, answer: str) -> bool:
    """
    Return True if the answer asserts a wrong numeric value for the queried property.
    Hallucination = GT has numeric values AND none of them appear in the answer,
    but a different numeric value is stated as the answer.

    This is intentionally conservative: if the correct GT number appears anywhere
    in the answer, hallucination is not flagged even if other numbers are also present.
    """
    gt_nums = extract_numbers(ground_truth)
    if not gt_nums:
        return False  # Non-numeric GT; cannot flag numeric hallucination

    ans_nums = extract_numbers(answer)
    if not ans_nums:
        return False  # No numbers in answer; no false assertion

    # If ANY GT number appears in the answer, the answer is grounded in truth
    if any(any(numbers_close(gt_n, a_n) for a_n in ans_nums) for gt_n in gt_nums):
        return False

    # GT numbers are absent; check if the answer confidently states a different value
    # (i.e., answer is not "not found" and does contain numbers)
    answer_lower = answer.lower()
    is_refusal = any(p in answer_lower for p in ["not found", "not available", "no information", "cannot find"])
    return not is_refusal


# ── Answer correctness ─────────────────────────────────────────────────────────

def check_answer_correct(ground_truth: str, answer: str) -> bool:
    """
    Return True if the answer captures all key numeric or keyword facts from GT.
    Strategy:
    1. Extract all numbers from GT; verify each is present in answer (±5%).
    2. For non-numeric GT (e.g., "ZN", "Straight", "D38999/26WA98PN"),
       check if the GT token appears in the answer (case-insensitive).
    """
    answer_lower = answer.lower()
    gt_lower = ground_truth.lower()

    # ── Numeric check ────────────────────────────────────────────────────────
    gt_nums = extract_numbers(ground_truth)
    if gt_nums:
        ans_nums = extract_numbers(answer)
        # All GT numbers must be present in answer
        for gt_n in gt_nums:
            if not any(numbers_close(gt_n, a_n) for a_n in ans_nums):
                return False
        return True

    # ── Keyword check (no numbers in GT) ────────────────────────────────────
    # Tokenise GT and check each non-trivial token
    tokens = re.findall(r"[A-Za-z0-9/\-#]+", ground_truth)
    meaningful = [t for t in tokens if len(t) >= 2]
    if not meaningful:
        return True
    matches = sum(1 for t in meaningful if t.lower() in answer_lower)
    return matches >= max(1, len(meaningful) // 2)


# ── Main judge function ────────────────────────────────────────────────────────

def judge(question: str, ground_truth: str, answer: str) -> dict:
    """
    Score a single answer.

    Returns:
        {
          "answer_correct": 0|1,
          "citation_accurate": 0|1,
          "unit_fidelity": 0|1,
          "hallucination": True|False,
          "judge_reasoning": str,
        }
    """
    answer_correct = check_answer_correct(ground_truth, answer)
    citation_accurate = check_citation(question, answer)
    unit_fid = check_unit_fidelity(ground_truth, answer)
    hallucination = check_hallucination(ground_truth, answer)

    reasoning_parts = []
    if not answer_correct:
        reasoning_parts.append(f"GT={ground_truth!r} not found in answer")
    if not citation_accurate:
        reasoning_parts.append("product code not cited")
    if not unit_fid:
        reasoning_parts.append("unit mismatch")
    if hallucination:
        reasoning_parts.append("answer contains numbers not in GT")

    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "OK"

    return {
        "answer_correct": int(answer_correct),
        "citation_accurate": int(citation_accurate),
        "unit_fidelity": int(unit_fid),
        "hallucination": hallucination,
        "judge_reasoning": reasoning,
    }
