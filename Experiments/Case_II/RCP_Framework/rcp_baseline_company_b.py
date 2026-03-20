"""
B3: RCP (Relational Control Plane) baseline for Company B Case II evaluation.

Implements a local-model version of the Company B RCP pipeline using llama3.2
via Ollama. The six-stage control loop:

  1. GoalDefine      – parse the query into a structured goal
  2. StrategyPlan    – select SIMPLE, ENHANCED, or COMPARISON strategy
  3. FunctionExecute – run the ordered function plan
  4. FunctionValidate– verify each function's output schema
  5. StrategyValidate– check if goal is satisfied; retry with ENHANCED if not
  6. GoalValidate    – final confidence-gated answer synthesis

Functions (mirrors Company B FunctionTemplateLibrary):
  - Extract Keywords
  - Table Search
  - Filter Table
  - Normalize Keywords
  - Analyze Data
"""

import json
import os
import re
import sqlite3
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import requests

# Set COMPANY_B_DB_PATH environment variable to override the default location.
COMPANY_B_DB = Path(os.environ.get("COMPANY_B_DB_PATH", "database/company_b_harvested.db"))
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2:latest"

PRODUCT_CODE_RE = re.compile(
    r"(?:(?:RPT|RNT|TFR|RPY)\s*[\d\s/\-]+|C0\d{6}[\-\d]+)",
    re.IGNORECASE,
)

# ── Ollama helper ──────────────────────────────────────────────────────────────

def generate(prompt: str, temperature: float = 0.0) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "temperature": temperature, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def func_extract_keywords(state: dict) -> dict:
    """
    Stage: Extract Keywords
    Input:  state["query"]
    Output: state["keywords"] – list[str]
    """
    query = state["query"]
    # Product codes
    codes = PRODUCT_CODE_RE.findall(query)
    codes = [c.strip() for c in codes if len(c.strip()) >= 3]

    # Also extract small integers that may indicate shell sizes
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", query)
    shell_like = [n for n in numbers if "." not in n and 1 <= int(n) <= 30]

    if codes:
        state["keywords"] = list(dict.fromkeys(codes + shell_like[:2]))
        return state

    # Fallback: LLM extraction
    prompt = (
        "Extract the key technical terms, product codes, or component names "
        "from this query that would appear in a technical database.\n"
        "Return only the terms, comma-separated, no explanation.\n\n"
        f"Query: {query}\nTerms:"
    )
    raw = generate(prompt)
    kws = [k.strip() for k in raw.split(",") if k.strip()]
    state["keywords"] = list(dict.fromkeys(kws + shell_like[:2]))[:5]
    return state


def func_normalize_keywords(state: dict) -> dict:
    """
    Stage: Normalize Keywords
    Input:  state["keywords"]
    Output: state["keywords"] – normalized/expanded list
    Adds format variations: "TFR4631015/030" → ["TFR 463 1015/030", "TFR4631015030"]
    """
    original = state.get("keywords", [])
    expanded = list(original)
    for kw in original:
        # Remove all spaces → compact form
        compact = re.sub(r"\s+", "", kw)
        if compact != kw:
            expanded.append(compact)
        # Insert space after family prefix (e.g., TFR46310 → TFR 46310)
        spaced = re.sub(r"^(RPT|RNT|TFR|RPY)(\d)", r"\1 \2", kw, flags=re.I)
        if spaced != kw:
            expanded.append(spaced)
        # Product number variations: TFR4631015 → TFR 463 1015
        m = re.match(r"(RPT|RNT|TFR)(\d{3})(\d+)", kw, re.I)
        if m:
            expanded.append(f"{m.group(1)} {m.group(2)} {m.group(3)}")
    state["keywords"] = list(dict.fromkeys(expanded))
    return state


def func_table_search(state: dict) -> dict:
    """
    Stage: Table Search
    Input:  state["keywords"]
    Output: state["retrieved_tables"] – list[dict]
    """
    keywords = state.get("keywords", [])
    con = sqlite3.connect(COMPANY_B_DB)
    cur = con.cursor()
    results = []
    seen = set()
    for kw in keywords:
        cur.execute(
            "SELECT filename, heading_name, table_name, tablecontent "
            "FROM extracted_tables "
            "WHERE tablecontent LIKE ? OR filename LIKE ? OR table_name LIKE ? "
            "LIMIT 15",
            (f"%{kw}%", f"%{kw}%", f"%{kw}%"),
        )
        for filename, heading, table_name, content_json in cur.fetchall():
            if table_name not in seen:
                seen.add(table_name)
                try:
                    results.append({
                        "source": f"{filename}/{table_name}",
                        "heading": heading or "",
                        "rows": json.loads(content_json),
                    })
                except Exception:
                    pass
    con.close()
    state["retrieved_tables"] = results[:20]
    return state


def func_filter_table(state: dict) -> dict:
    """
    Stage: Filter Table
    Input:  state["retrieved_tables"], state["keywords"]
    Output: state["filtered_tables"] – tables with rows matching keywords
    Falls back to keeping all rows when keyword matching yields no results.
    """
    keywords = [kw.lower() for kw in state.get("keywords", [])]
    filtered = []
    for table in state.get("retrieved_tables", []):
        rows = table.get("rows", [])
        if not rows:
            continue
        keep_rows = [rows[0]]  # always keep header
        for row in rows[1:]:
            row_text = json.dumps(row).lower()
            if any(kw in row_text for kw in keywords):
                keep_rows.append(row)
        if len(keep_rows) > 1:
            filtered.append({**table, "rows": keep_rows})
        else:
            # No rows matched keyword: keep ALL rows (dimension tables don't
            # repeat product codes in every row)
            filtered.append({**table, "rows": rows})
    state["filtered_tables"] = filtered if filtered else state.get("retrieved_tables", [])
    return state


def func_analyze_data(state: dict) -> dict:
    """
    Stage: Analyze Data
    Input:  state["filtered_tables"], state["query"]
    Output: state["answer"], state["confidence"] (0.0-1.0)
    """
    tables = state.get("filtered_tables", state.get("retrieved_tables", []))
    if not tables:
        state["answer"] = "Not found in documentation."
        state["confidence"] = 0.0
        return state

    # Format tables for LLM context
    context_parts = []
    for t in tables[:8]:
        heading = f" [{t['heading']}]" if t["heading"] else ""
        context_parts.append(f"\nSource: {t['source']}{heading}")
        rows = t.get("rows", [])
        if rows:
            context_parts.append("  Columns: " + " | ".join(str(c).replace("\n", " ") for c in rows[0]))
            for row in rows[1:20]:
                context_parts.append("  Row: " + " | ".join(str(c).replace("\n", " ") for c in row))
    context = "\n".join(context_parts)

    prompt = (
        "You are a technical documentation assistant for Company B aerospace connector "
        "and cable products. Find the exact answer in the table records below.\n"
        "Each table shows 'Columns:' (header) followed by 'Row:' entries.\n"
        "Identify the correct row and column for the requested specification.\n"
        "State the exact value with units. Do NOT say 'Not found' if the value is visible in the table.\n\n"
        f"Table records:\n{context[:3500]}\n\n"
        f"Question: {state['query']}\n\nAnswer (exact value with units):"
    )
    answer = generate(prompt)
    state["answer"] = answer

    # Confidence: heuristic based on whether answer mentions a number or named entity
    has_value = bool(re.search(r"\d", answer)) and "not found" not in answer.lower()
    state["confidence"] = 0.85 if has_value else 0.2
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGIES = {
    "SIMPLE LOOKUP": [
        func_extract_keywords,
        func_table_search,
        func_filter_table,
        func_analyze_data,
    ],
    "ENHANCED LOOKUP": [
        func_extract_keywords,
        func_table_search,
        func_filter_table,
        func_normalize_keywords,
        func_table_search,    # second pass with normalized keywords
        func_filter_table,
        func_analyze_data,
    ],
    "MULTI-PRODUCT COMPARISON": [
        func_extract_keywords,
        func_normalize_keywords,
        func_table_search,
        func_filter_table,
        func_analyze_data,
    ],
}

STRATEGY_SELECT_PROMPT = """\
Select the best retrieval strategy for this query.
Options:
- SIMPLE LOOKUP: for direct product specification queries (one product code)
- ENHANCED LOOKUP: for complex queries requiring broader search and normalization
- MULTI-PRODUCT COMPARISON: for queries comparing two or more products

Query: {query}
Strategy (output only the strategy name):"""

CONFIDENCE_THRESHOLD = 0.6


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROL LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def select_strategy(query: str, forced: str | None = None) -> str:
    if forced and forced in STRATEGIES:
        return forced
    raw = generate(STRATEGY_SELECT_PROMPT.format(query=query))
    for name in STRATEGIES:
        if name.lower() in raw.lower():
            return name
    return "SIMPLE LOOKUP"


def run_strategy(strategy_name: str, state: dict) -> dict:
    plan = STRATEGIES[strategy_name]
    print(f"  [B3] Strategy: {strategy_name} ({len(plan)} steps)")
    for func in plan:
        state = func(state)
    return state


def run_b3(query: str, forced_strategy: str | None = None) -> tuple[str, float]:
    """
    Full six-stage RCP control loop.
    Returns (answer, latency_s).
    """
    t0 = time.time()

    # Stage 1: GoalDefine
    state: dict = {"query": query}

    # Stage 2: StrategyPlan
    strategy = select_strategy(query, forced=forced_strategy)

    # Stage 3+4+5: FunctionExecute + FunctionValidate + StrategyValidate
    state = run_strategy(strategy, state)

    # Stage 5: StrategyValidate – retry with ENHANCED if confidence is low
    if state.get("confidence", 0.0) < CONFIDENCE_THRESHOLD and strategy != "ENHANCED LOOKUP":
        print("  [B3] Low confidence, retrying with ENHANCED LOOKUP")
        state.pop("answer", None)
        state.pop("retrieved_tables", None)
        state.pop("filtered_tables", None)
        state = run_strategy("ENHANCED LOOKUP", state)

    # Stage 6: GoalValidate – final confidence check
    answer = state.get("answer", "Not found in documentation.")
    if state.get("confidence", 0.0) < 0.3:
        answer = "Not found in documentation."

    return answer, time.time() - t0


if __name__ == "__main__":
    ans, lat = run_b3("What is the jacket diameter of TFR4631015/030?")
    print(f"Answer: {ans}")
    print(f"Latency: {lat:.2f}s")
