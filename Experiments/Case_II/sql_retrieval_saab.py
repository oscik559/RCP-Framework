"""
B2: SQL-backed Retrieval baseline for Saab Case II evaluation.

1. Extracts product code / keyword from query using regex + LLM.
2. Queries extracted_tables via SQL LIKE on tablecontent.
3. Passes matching rows directly to LLM for answer synthesis.
"""

import json
import re
import sqlite3
import time
from pathlib import Path

import requests

SAAB_DB = Path(
    r"C:\Users\oscik35\Desktop\PROJECTS\Test_Projects_DELETE"
    r"\Project_Saab_fork\Project_Saab\data\database\harvested.db"
)
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2:latest"


# ── Ollama helper ──────────────────────────────────────────────────────────────

def generate(prompt: str, temperature: float = 0.0) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ── Keyword extraction ─────────────────────────────────────────────────────────

# Patterns for Saab product codes
PRODUCT_CODE_RE = re.compile(
    r"""
    (?:
        (?:RPT|RNT|TFR|RPY)\s*[\d\s/\-]+   # RPT/RNT/TFR/RPY codes
      | C0\d{6}[\-\d]+                        # C0-series
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

FALLBACK_KW_PROMPT = """\
Extract the key technical term or product code from this query that would help find it in a database.
Return only 1-3 keywords or product codes, comma-separated. No explanation.

Query: {query}
Keywords:"""


def extract_keywords(query: str) -> list[str]:
    """Return product codes or keywords to search the database with."""
    codes = PRODUCT_CODE_RE.findall(query)
    codes = [c.strip() for c in codes if len(c.strip()) >= 3]

    if codes:
        # Also add normalized variants (e.g., remove spaces)
        variants = []
        for code in codes:
            normalized = re.sub(r"\s+", "", code)
            variants.append(normalized)
        return list(dict.fromkeys(codes + variants))

    # Fallback: LLM-based extraction
    raw = generate(FALLBACK_KW_PROMPT.format(query=query))
    kws = [k.strip() for k in raw.split(",") if k.strip()]
    return kws[:3] if kws else [query[:50]]


# ── SQL retrieval ──────────────────────────────────────────────────────────────

def sql_search(keywords: list[str], max_rows: int = 10) -> list[dict]:
    """Return matching rows from extracted_tables for any of the given keywords."""
    con = sqlite3.connect(SAAB_DB)
    cur = con.cursor()
    results = []
    seen = set()

    for kw in keywords:
        # Search tablecontent, heading_name, filename, and table_name
        cur.execute(
            """
            SELECT filename, heading_name, table_name, tablecontent
            FROM extracted_tables
            WHERE tablecontent LIKE ? OR heading_name LIKE ?
               OR filename LIKE ? OR table_name LIKE ?
            LIMIT ?
            """,
            (f"%{kw}%", f"%{kw}%", f"%{kw}%", f"%{kw}%", max_rows),
        )
        for filename, heading, table_name, content_json in cur.fetchall():
            key = table_name
            if key not in seen:
                seen.add(key)
                try:
                    rows = json.loads(content_json)
                    results.append(
                        {
                            "source": f"{filename}/{table_name}",
                            "heading": heading or "",
                            "rows": rows,
                        }
                    )
                except Exception:
                    pass
    con.close()
    return results[:max_rows]


def format_results(results: list[dict]) -> str:
    """Format SQL results as readable text for LLM context."""
    parts = []
    for r in results:
        heading = f" [{r['heading']}]" if r["heading"] else ""
        parts.append(f"\nSource: {r['source']}{heading}")
        if r["rows"]:
            header = r["rows"][0]
            parts.append("  Columns: " + " | ".join(str(c).replace("\n", " ") for c in header))
            for row in r["rows"][1:25]:
                parts.append("  Row: " + " | ".join(str(c).replace("\n", " ") for c in row))
    return "\n".join(parts)


# ── Answer generation ──────────────────────────────────────────────────────────

ANSWER_PROMPT = """\
You are a technical documentation assistant for Saab aerospace connector and cable products.
Answer the question using ONLY the information in the provided database records.
Look carefully at each table row to find the specific value for the requested product or shell size.
Include the exact numeric value with units. Do NOT say "Not found" if you can see the value in the records.

Database records:
{context}

Question: {question}

Answer (provide the specific value with units):"""


def run_b2(query: str) -> tuple[str, float]:
    """Return (answer, latency_s)."""
    t0 = time.time()
    keywords = extract_keywords(query)
    results = sql_search(keywords)

    if not results:
        # Fallback: broader search with first noun-like words from query
        words = re.findall(r"[A-Za-z]{4,}", query)
        if words:
            results = sql_search(words[:2])

    context = format_results(results) if results else "No records found."
    prompt = ANSWER_PROMPT.format(context=context[:4000], question=query)
    answer = generate(prompt)
    return answer, time.time() - t0


if __name__ == "__main__":
    ans, lat = run_b2("What is the jacket diameter of TFR4631015/030?")
    print(f"Answer: {ans}")
    print(f"Latency: {lat:.2f}s")
