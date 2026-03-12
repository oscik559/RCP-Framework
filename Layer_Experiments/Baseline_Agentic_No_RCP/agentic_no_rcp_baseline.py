#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agentic Baseline Pipeline (No RCP)
==================================
A multi-step agentic baseline that uses tool-calling but without:
  1. Relational state persistence (no agentic.db)
  2. Multi-stage validation gates (no Stage 4-6)
  3. Structured goal/strategy tracking

This represents the "standard" agentic approach where an LLM is given 
tools and a loop to solve a query.
"""

import json
import logging
import os
import sys
import time
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path setup to include Layer_2_Agentic and other modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the function library from Layer_2_Agentic
try:
    from Layer_2_Agentic.logic import function_library as fl
    from Layer_2_Agentic.config.config_loader import CONFIG
    from langchain_ollama import ChatOllama
except ImportError as e:
    print(f"Error importing agentic components: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AGENTIC_NO_RCP_BASELINE")

# ── Database Shims (Current harvested.db schema) ─────────────────────

def shim_table_search(params: dict) -> tuple[bool, dict | str]:
    """Shim for table_search working with current products/knowledge tables."""
    kw_raw = params.get("Keyword Output", "").strip()
    if not kw_raw:
        return (False, "No keywords provided")
    
    keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
    db_path = str(PROJECT_ROOT / "database" / "harvested.db")
    
    results = []
    filenames = set()
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        for k in keywords:
            like_pat = f"%{k}%"
            # Search in products
            cursor = conn.execute(
                "SELECT product_code, page_number, specifications FROM products WHERE product_code LIKE ? OR specifications LIKE ?",
                (like_pat, like_pat)
            )
            for row in cursor:
                results.append({
                    "filename": row["product_code"],
                    "page_number": row["page_number"],
                    "table_data": row["specifications"]
                })
                filenames.add(row["product_code"])
            
            # Search in product_knowledge
            cursor = conn.execute(
                "SELECT pdf_name, page_number, content FROM product_knowledge WHERE content LIKE ?",
                (like_pat,)
            )
            for row in cursor:
                results.append({
                    "filename": row["pdf_name"],
                    "page_number": row["page_number"],
                    "table_data": row["content"]
                })
                filenames.add(row["pdf_name"])
        
        return (True, {
            "Table Output": json.dumps(results[:20]), # Cap results
            "Document Name": ", ".join(list(filenames)[:5])
        })
    except Exception as e:
        return (False, f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

def shim_document_search(params: dict) -> tuple[bool, dict | str]:
    """Shim for document_search working with current schema."""
    kw_raw = params.get("Keyword Output", "").strip()
    doc_name = params.get("Latest Document Name", "").strip()
    
    if not kw_raw or not doc_name:
        return (False, "Missing keywords or document name")
    
    keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
    db_path = str(PROJECT_ROOT / "database" / "harvested.db")
    
    results = []
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        for k in keywords:
            like_pat = f"%{k}%"
            # Search in products for this document
            cursor = conn.execute(
                "SELECT product_code, page_number, specifications FROM products WHERE (product_code LIKE ? OR specifications LIKE ?) AND product_code LIKE ?",
                (like_pat, like_pat, f"%{doc_name}%")
            )
            for row in cursor:
                results.append({"filename": row["product_code"], "page_number": row["page_number"], "table_data": row["specifications"]})
            
            # Search in knowledge for this document
            cursor = conn.execute(
                "SELECT pdf_name, page_number, content FROM product_knowledge WHERE content LIKE ? AND pdf_name LIKE ?",
                (like_pat, f"%{doc_name}%")
            )
            for row in cursor:
                results.append({"filename": row["pdf_name"], "page_number": row["page_number"], "table_data": row["content"]})
                
        return (True, {"Table Output": json.dumps(results[:20]), "Document Name": doc_name})
    except Exception as e:
        return (False, f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

class AgenticNoRCPBaseline:
    """
    Implements a multi-step agentic loop without RCP features.
    """
    
    def __init__(self, model: str = "llama3.2:latest", max_steps: int = 5):
        self.model_name = model
        self.max_steps = max_steps
        self.llm = ChatOllama(
            model=model,
            temperature=0.0,
            num_ctx=8192,
        )
        
        # Tools mapping (using shims for better compatibility with current schema)
        self.available_tools = {
            "table_search": shim_table_search,
            "document_search": shim_document_search,
            "find_latest_doc": fl.func_find_latest_document,
            "filter_table": fl.func_filter_table,
            "image_search": fl.func_image_search,
        }
        
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Run the agentic reasoning loop for a given query.
        """
        start_time = time.time()
        
        # Initialize context/history
        context = []
        steps_taken = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        # System prompt defining tools and behavior
        system_prompt = f"""You are a technical assistant for Hydroscand hydraulic products.
Your goal is to answer the user query as accurately as possible using the provided tools.

AVAILABLE TOOLS:
1. table_search(keyword_output: str): Search for keywords across all tables.
2. document_search(keyword_output: str, latest_document_name: str): Search for keywords in specific documents.
3. find_latest_doc(document_name: str): Find the most recent version of a document.
4. filter_table(table_output: str, filter_keywords: str): Filter existing table results.
5. image_search(keyword_output: str): Search for technical images.

RESPONSE FORMAT:
If you need to call a tool, respond with:
TOOL: tool_name
PARAMS: {{"param_name": "value", ...}}

If you have enough information to answer, respond with:
FINAL_ANSWER: your detailed answer here, including citations of filenames and article numbers.

REASONING GUIDELINES:
- Start by searching for product codes or keywords in the query.
- Use article numbers (e.g., 9005-01-04) as keywords.
- Always include the source filename in your final answer.
- If you find multiple tables, filter them for the specific property requested.
"""

        current_prompt = f"{system_prompt}\n\nUSER QUERY: {user_query}\n\nTHOUGHT:"
        
        final_answer = ""
        sources = []
        
        for step in range(self.max_steps):
            logger.info(f"Step {step+1}/{self.max_steps} for: {user_query[:50]}...")
            
            # 1. Get LLM response
            try:
                response = self.llm.invoke(current_prompt)
                content = response.content
                
                # Estimate tokens (simplistic)
                total_prompt_tokens += len(current_prompt) // 4
                total_completion_tokens += len(content) // 4
                
                steps_taken.append({"step": step + 1, "content": content})
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                final_answer = f"Error during reasoning: {e}"
                break
            
            # 2. Check for Final Answer
            if "FINAL_ANSWER:" in content:
                final_answer = content.split("FINAL_ANSWER:")[1].strip()
                break
                
            # 3. Check for Tool Call
            tool_match = re.search(r"TOOL:\s*(\w+)", content)
            params_match = re.search(r"PARAMS:\s*(\{.*\})", content)
            
            if tool_match and params_match:
                tool_name = tool_match.group(1).strip()
                try:
                    params = json.loads(params_match.group(1).strip())
                except Exception as e:
                    logger.warning(f"Error parsing params: {e}")
                    current_prompt += f"\n\nOBSERVATION: Error parsing tool parameters. Please try again with valid JSON."
                    continue
                
                if tool_name in self.available_tools:
                    # Map LLM names to function keys
                    param_mapping = {
                        "keyword_output": "Keyword Output",
                        "latest_document_name": "Latest Document Name",
                        "document_name": "Document Name",
                        "table_output": "Table Output",
                        "filter_keywords": "Filter Keywords"
                    }
                    
                    mapped_params = {param_mapping.get(k, k): v for k, v in params.items()}
                    
                    logger.info(f"Executing tool {tool_name} with {mapped_params}")
                    success, result = self.available_tools[tool_name](mapped_params)
                    
                    if success:
                        # Extract source documents if present
                        if isinstance(result, dict) and "Document Name" in result:
                            new_sources = [s.strip() for s in result["Document Name"].split(",") if s.strip()]
                            sources.extend([s for s in new_sources if s not in sources])
                        
                        # Observation
                        obs = str(result)[:2000] # Cap length
                        current_prompt += f"\n{content}\nOBSERVATION: {obs}\nTHOUGHT:"
                    else:
                        current_prompt += f"\n{content}\nOBSERVATION: Tool failed: {result}\nTHOUGHT:"
                else:
                    current_prompt += f"\n{content}\nOBSERVATION: Tool '{tool_name}' not recognized.\nTHOUGHT:"
            else:
                # LLM didn't format correctly or just rambled
                current_prompt += f"\n{content}\nOBSERVATION: Please use the specified TOOL/PARAMS or FINAL_ANSWER format.\nTHOUGHT:"

        if not final_answer:
            final_answer = "Maximum reasoning steps reached without a final answer."
            if steps_taken:
                # Try to salvage a response from the last step
                final_answer += f" Last thought: {steps_taken[-1]['content']}"

        latency = time.time() - start_time
        
        return {
            "answer": final_answer,
            "sources": sources,
            "latency_s": round(latency, 2),
            "token_estimate": total_prompt_tokens + total_completion_tokens,
            "prompt_tokens": total_prompt_tokens,
            "response_tokens": total_completion_tokens,
            "steps": steps_taken
        }

if __name__ == "__main__":
    # Smoke test
    pipeline = AgenticNoRCPBaseline()
    test_q = "What is the working pressure of the 9005-01-04 hose?"
    print(f"Testing Query: {test_q}")
    result = pipeline.query(test_q)
    print(f"Result: {result['answer']}")
    print(f"Sources: {result['sources']}")
    print(f"Latency: {result['latency_s']}s")
