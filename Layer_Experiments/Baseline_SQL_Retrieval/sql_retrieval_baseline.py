#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL-backed Retrieval Baseline (B2)
===================================
Single-step structured retrieval against harvested.db → LLM generation.

Unlike Naive RAG (B1) which chunks text and retrieves via embeddings,
this baseline queries the relational schema directly:
  1. Parse query to extract product codes via regex
  2. Run SQL queries against harvested.db (categories, families, products, knowledge)
  3. Assemble structured context from query results
  4. Single LLM call to generate answer

This isolates the value of structured extraction (objectification)
without multi-step reasoning, validation gates, or persistent state.
"""

import json
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_ollama import ChatOllama

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SQL_RETRIEVAL")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "llm_model": "llama3.2:latest",
    "llm_temperature": 0.0,
    "harvested_db": str(PROJECT_ROOT / "database" / "harvested.db"),
    "max_products": 20,
    "max_knowledge": 5,
}

# ---------------------------------------------------------------------------
# Product code patterns for Hydroscand catalogue
# ---------------------------------------------------------------------------
PRODUCT_CODE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2}(?:-\d{2})?)\b"),  # e.g. 1103-03-04, 1105-10-04-30
    re.compile(r"\b(\d{4}-\d{2})\b"),                      # family code e.g. 1103-03
]


# ═══════════════════════════════════════════════════════════════════════════
# SQL RETRIEVAL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

class SQLRetrievalBaseline:
    """
    Structured retrieval over harvested.db: parse → SQL → LLM.

    No chunking, no vectorstore, no multi-step reasoning, no validation.
    Tests the value of relational data representation alone.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.llm: Optional[ChatOllama] = None
        self._total_tokens = 0

    def initialize(self) -> None:
        logger.info("=" * 60)
        logger.info("INITIALIZING SQL RETRIEVAL BASELINE")
        logger.info("=" * 60)
        logger.info(f"LLM: {self.config['llm_model']}")
        logger.info(f"Database: {self.config['harvested_db']}")

        self.llm = ChatOllama(
            model=self.config["llm_model"],
            temperature=self.config["llm_temperature"],
        )

        # Verify DB exists and has data
        db_path = self.config["harvested_db"]
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        conn.close()
        logger.info(f"  Products in database: {count}")
        logger.info("=" * 60)

    # ── Query extraction ──────────────────────────────────────────────

    def _extract_codes(self, query: str) -> Dict[str, List[str]]:
        """Extract product codes and family codes from the query string."""
        product_codes = []
        family_codes = []

        # Full product codes (4-2-2 or 4-2-2-2)
        for m in PRODUCT_CODE_PATTERNS[0].finditer(query):
            product_codes.append(m.group(1))

        # Family codes (4-2) — only if not already part of a product code
        for m in PRODUCT_CODE_PATTERNS[1].finditer(query):
            code = m.group(1)
            if not any(code in pc for pc in product_codes):
                family_codes.append(code)

        return {"product_codes": product_codes, "family_codes": family_codes}

    # ── SQL retrieval ─────────────────────────────────────────────────

    def _retrieve_structured(self, query: str) -> Dict[str, Any]:
        """
        Query harvested.db using extracted codes and keyword matching.
        Returns structured context dict.
        """
        codes = self._extract_codes(query)
        db_path = self.config["harvested_db"]
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        context = {"products": [], "families": [], "knowledge": []}

        try:
            # ── Direct product lookup by code ─────────────────────────
            for pc in codes["product_codes"]:
                rows = conn.execute("""
                    SELECT p.product_code, p.specifications, p.page_number,
                           p.configuration_type, p.variant_suffix,
                           pf.name AS family_name, pf.family_code,
                           pf.description AS family_desc,
                           pf.construction_details, pf.applications,
                           c.name AS category_name
                    FROM products p
                    LEFT JOIN product_families pf ON p.family_id = pf.id
                    LEFT JOIN categories c ON pf.category_id = c.id
                    WHERE p.product_code = ?
                """, (pc,)).fetchall()

                for row in rows:
                    context["products"].append(dict(row))

            # ── Family-level lookup ───────────────────────────────────
            for fc in codes["family_codes"]:
                # Family metadata
                fam_rows = conn.execute("""
                    SELECT pf.family_code, pf.name, pf.subtitle, pf.description,
                           pf.construction_details, pf.applications, pf.page_number,
                           c.name AS category_name
                    FROM product_families pf
                    LEFT JOIN categories c ON pf.category_id = c.id
                    WHERE pf.family_code = ?
                """, (fc,)).fetchall()

                for row in fam_rows:
                    context["families"].append(dict(row))

                # All products in family
                prod_rows = conn.execute("""
                    SELECT p.product_code, p.specifications, p.page_number
                    FROM products p
                    JOIN product_families pf ON p.family_id = pf.id
                    WHERE pf.family_code = ?
                    LIMIT ?
                """, (fc, self.config["max_products"])).fetchall()

                for row in prod_rows:
                    context["products"].append(dict(row))

            # ── Keyword fallback (when no codes found) ────────────────
            if not codes["product_codes"] and not codes["family_codes"]:
                # Extract meaningful keywords from the query
                keywords = self._extract_keywords(query)
                if keywords:
                    context = self._keyword_search(conn, keywords, context)

            # ── Knowledge base search ─────────────────────────────────
            # Always search knowledge for supplementary context
            search_terms = codes["product_codes"] + codes["family_codes"]
            if not search_terms:
                search_terms = self._extract_keywords(query)

            for term in search_terms[:3]:  # Limit to avoid huge context
                know_rows = conn.execute("""
                    SELECT pdf_name, page_number, category, knowledge_type,
                           section_title, content
                    FROM product_knowledge
                    WHERE content LIKE ?
                    LIMIT ?
                """, (f"%{term}%", self.config["max_knowledge"])).fetchall()

                for row in know_rows:
                    context["knowledge"].append(dict(row))

        finally:
            conn.close()

        return context

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract search keywords from a query without product codes."""
        # Remove common stop words and short words
        stop_words = {
            "what", "which", "how", "does", "the", "for", "can", "you",
            "have", "are", "with", "that", "this", "from", "and", "or",
            "is", "it", "in", "of", "to", "a", "an", "do", "at", "by",
            "its", "be", "was", "were",
            # Swedish common words
            "vad", "vilken", "hur", "har", "kan", "du", "den", "det",
            "för", "med", "som", "och", "eller", "ett", "en", "av",
        }
        words = re.findall(r"\b[a-zA-ZåäöÅÄÖ]{3,}\b", query.lower())
        keywords = [w for w in words if w not in stop_words]
        return keywords[:5]

    def _keyword_search(
        self, conn: sqlite3.Connection, keywords: List[str], context: Dict
    ) -> Dict[str, Any]:
        """Search products and families by keyword when no codes are found."""
        for kw in keywords:
            like = f"%{kw}%"

            # Search product families
            fam_rows = conn.execute("""
                SELECT pf.family_code, pf.name, pf.subtitle, pf.description,
                       pf.construction_details, pf.applications, pf.page_number,
                       c.name AS category_name
                FROM product_families pf
                LEFT JOIN categories c ON pf.category_id = c.id
                WHERE pf.name LIKE ? OR pf.description LIKE ?
                   OR pf.applications LIKE ? OR pf.construction_details LIKE ?
                LIMIT 5
            """, (like, like, like, like)).fetchall()

            for row in fam_rows:
                context["families"].append(dict(row))

            # Search products by specifications
            prod_rows = conn.execute("""
                SELECT p.product_code, p.specifications, p.page_number,
                       pf.name AS family_name, pf.family_code
                FROM products p
                LEFT JOIN product_families pf ON p.family_id = pf.id
                WHERE p.specifications LIKE ?
                LIMIT ?
            """, (like, self.config["max_products"])).fetchall()

            for row in prod_rows:
                context["products"].append(dict(row))

        return context

    # ── Context formatting ────────────────────────────────────────────

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format structured SQL results into LLM-readable context."""
        parts = []

        # Deduplicate products by code
        seen_products = set()
        for p in context["products"]:
            pc = p.get("product_code", "")
            if pc in seen_products:
                continue
            seen_products.add(pc)

            entry = [f"Product: {pc}"]
            if p.get("family_name"):
                entry.append(f"  Family: {p['family_name']} ({p.get('family_code', '')})")
            if p.get("category_name"):
                entry.append(f"  Category: {p['category_name']}")
            if p.get("page_number"):
                entry.append(f"  Page: {p['page_number']}")
            if p.get("specifications"):
                try:
                    specs = json.loads(p["specifications"]) if isinstance(p["specifications"], str) else p["specifications"]
                    for k, v in specs.items():
                        entry.append(f"  {k}: {v}")
                except (json.JSONDecodeError, TypeError, AttributeError):
                    entry.append(f"  Specifications: {p['specifications']}")
            parts.append("\n".join(entry))

        # Families
        seen_families = set()
        for f in context["families"]:
            fc = f.get("family_code", "")
            if fc in seen_families:
                continue
            seen_families.add(fc)

            entry = [f"Product Family: {f.get('name', '')} ({fc})"]
            if f.get("category_name"):
                entry.append(f"  Category: {f['category_name']}")
            if f.get("description"):
                entry.append(f"  Description: {f['description'][:300]}")
            if f.get("applications"):
                entry.append(f"  Applications: {f['applications'][:200]}")
            if f.get("construction_details"):
                try:
                    cd = json.loads(f["construction_details"]) if isinstance(f["construction_details"], str) else f["construction_details"]
                    for k, v in cd.items():
                        entry.append(f"  {k}: {v}")
                except (json.JSONDecodeError, TypeError, AttributeError):
                    entry.append(f"  Construction: {str(f['construction_details'])[:200]}")
            parts.append("\n".join(entry))

        # Knowledge
        seen_knowledge = set()
        for k in context["knowledge"]:
            content = k.get("content", "")
            content_key = content[:100]
            if content_key in seen_knowledge:
                continue
            seen_knowledge.add(content_key)

            entry = []
            if k.get("section_title"):
                entry.append(f"[{k['section_title']}]")
            entry.append(content[:500])
            if k.get("pdf_name"):
                entry.append(f"  (Source: {k['pdf_name']}, p.{k.get('page_number', '?')})")
            parts.append("\n".join(entry))

        if not parts:
            return "No matching records found in the database."

        return "\n\n".join(parts)

    # ── Main query method ─────────────────────────────────────────────

    def query(self, question: str) -> Dict[str, Any]:
        """
        Run the SQL retrieval pipeline on a single question.

        Returns:
            Dict with keys: answer, context_summary, latency_s, token_estimate,
                           sql_queries, products_found, families_found
        """
        if self.llm is None:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        start_time = time.perf_counter()

        # 1. Retrieve structured data via SQL
        context = self._retrieve_structured(question)

        products_found = len(set(p.get("product_code", "") for p in context["products"]))
        families_found = len(set(f.get("family_code", "") for f in context["families"]))
        knowledge_found = len(context["knowledge"])

        # 2. Format context
        formatted_context = self._format_context(context)

        # 3. Generate answer with single LLM call
        prompt = (
            "You are a technical assistant for Hydroscand hydraulic engineering products. "
            "Answer the question based ONLY on the structured data provided below. "
            "Include specific product codes, values with units, and page references when available. "
            "If the data does not contain the answer, say so clearly.\n\n"
            f"STRUCTURED DATA:\n{formatted_context}\n\n"
            f"QUESTION: {question}\n\n"
            "ANSWER:"
        )

        prompt_tokens = len(prompt) // 4
        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
        response_tokens = len(answer) // 4
        total_tokens = prompt_tokens + response_tokens
        self._total_tokens += total_tokens

        elapsed = time.perf_counter() - start_time

        return {
            "answer": answer,
            "products_found": products_found,
            "families_found": families_found,
            "knowledge_found": knowledge_found,
            "latency_s": round(elapsed, 3),
            "token_estimate": total_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
        }

    @property
    def total_tokens(self) -> int:
        return self._total_tokens


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SQL RETRIEVAL BASELINE — Quick Smoke Test")
    print("=" * 60 + "\n")

    pipeline = SQLRetrievalBaseline()
    pipeline.initialize()

    test_questions = [
        "Vilken gängstorlek har en 4201-16-16?",
        "What is the maximum working pressure for hose 1103-03-04?",
        "Which products are approved for food use?",
        "Compare the weight of 1102-14-04 and 1103-03-04.",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        result = pipeline.query(q)
        print(f"A: {result['answer'][:200]}...")
        print(
            f"   Products: {result['products_found']} | "
            f"Families: {result['families_found']} | "
            f"Knowledge: {result['knowledge_found']} | "
            f"Latency: {result['latency_s']}s"
        )
        print("-" * 60)

    print(f"\nTotal tokens used: {pipeline.total_tokens}")
