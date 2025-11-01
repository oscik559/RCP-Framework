# agentic_reasoning/logic/workflow_helpers.py

"""
Workflow orchestration utilities for the agentic reasoning system.

Provides lightweight, commonly-used capabilities for workflow nodes and 
function execution. These utilities handle data type inference, output 
collection/merging, and robust JSON parsing from LLM responses.

Key Functions:
- infer_sql_type(): Auto-detect SQL types from string values using heuristics
- collect_outputs(): Fetch function outputs from database for parameter resolution  
- merge_values(): Combine multiple outputs with type-specific merging rules
- handler_from_name(): Resolve function names to callable handlers via FUNCTION_MAP
- parse_json_response(): Extract JSON from noisy LLM text with multiple fallbacks

Type Inference Heuristics:
- Integers: Numeric strings without decimals
- Reals: Numeric strings with decimals  
- Booleans: "true"/"false" strings
- JSON: Strings starting with '[' or '{'
- DateTime: ISO format strings
- Lists: Comma-separated values
- Default: String type for everything else

Output Merging Rules:
- Keywords: Deduplicate comma-separated lists, use latest value
- Tables: Parse as JSON arrays and concatenate rows  
- Documents: Deduplicate document references
- Default: Use most recent value with debug logging

JSON Parsing Strategies:
1. Direct JSON parsing
2. Markdown code block extraction  
3. First braced substring extraction
4. Fallback to None on all failures

Design Principles:
- Resilient to messy LLM outputs and inconsistent tool responses
- Lightweight utilities with minimal dependencies
- Comprehensive debug logging for workflow tracing
- Type-safe operations with graceful fallbacks
"""

# ─── Workflow Helpers ──────────────────────────────────────────────────────
import subprocess
from pathlib import Path
import ast
import json
import re
from typing import Any, Dict, List, Optional

from agentic_reasoning.logic.database_manager import DatabaseManager
from agentic_reasoning.config.debug_config import debug


def infer_sql_type(value: str) -> str:
    """
    Infer SQL data type from string value for database storage.

    Args:
        value: String value to analyze

    Returns:
        Appropriate SQL type: 'integer', 'real', 'boolean', 'json', 'datetime', or 'string'
    """
    import re
    import json
    from datetime import datetime

    # Handle empty or None values
    if not value or value.lower() in ("none", "null", ""):
        return "string"

    # Check for comma-separated lists (multiple values)
    if "," in value and len(value.split(",")) > 1:
        return "string"

    # Check for boolean values
    if value.lower() in ("true", "false"):
        return "boolean"

    # Check for JSON structures (objects and arrays) - BEFORE numeric checks
    if value.strip().startswith(("[", "{")):
        try:
            json.loads(value)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

    # Check for integer values (single numeric value only)
    if value.strip().isdigit() or (
        value.strip().startswith("-") and value.strip()[1:].isdigit()
    ):
        return "integer"

    # Check for float/real values (single numeric value only)
    # First ensure it doesn't contain letters (except for scientific notation 'e')
    if not any(c.isalpha() for c in value.lower() if c != "e"):
        try:
            float(value)
            # Make sure it's not just an integer that could be parsed as float
            if "." in value or "e" in value.lower():
                return "real"
        except ValueError:
            pass

    # Check for datetime patterns (ISO format, common formats)
    datetime_patterns = [
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO datetime
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # SQL datetime
        r"\d{4}-\d{2}-\d{2}",  # Date only
        r"\d{2}:\d{2}:\d{2}",  # Time only
    ]

    for pattern in datetime_patterns:
        if re.match(pattern, value):
            try:
                # Try to parse as datetime to validate
                datetime.fromisoformat(value.replace("T", " "))
                return "datetime"
            except ValueError:
                continue

    # Default to string for everything else
    return "string"


def collect_outputs(
    session_id: int, goal_id: int, output_name: str, strategy_id: int = None
) -> List[str]:
    """
    Collect output values from previously executed functions.

    Searches for successful function outputs within the same session and goal
    that match the specified output name. This enables functions to build
    upon results from earlier functions in the workflow.

    Args:
        session_id: Current session identifier
        goal_id: Current goal identifier
        output_name: Name of the output to collect (e.g., "Keyword Output")
        strategy_id: If provided, only collect outputs from this specific strategy.
                    If None, collect from current strategy only (recommended)

    Returns:
        List of output values from successful functions
    """
    db = DatabaseManager()
    return db.collect_outputs(session_id, goal_id, output_name, strategy_id)


def merge_values(out_name: str, values: List[str]) -> str:
    """
    Merge multiple output values according to output type-specific rules.

    Different output types require different merging strategies:
    - Keyword outputs: Deduplicate and join with commas
    - Table outputs: Merge JSON arrays
    - Document names: Deduplicate document references
    - Default: Join with newlines

    Args:
        out_name: Name of the output type
        values: List of string values to merge

    Returns:
        Single merged string value
    """
    if not values:
        return ""

    if len(values) == 1:
        debug.print_merge(f"Single {out_name.lower()} value: '{values[0]}'")
        return values[0]

    if "keyword" in out_name.lower():
        # For keyword outputs, deduplicate and join
        all_keywords = []
        for val in values:
            keywords = [k.strip() for k in val.split(",")]
            all_keywords.extend(keywords)

        unique_keywords = []
        seen = set()
        for kw in all_keywords:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)

        merged = ", ".join(unique_keywords)
        debug.print_merge(
            f"RESET: {len(values)} keyword values → using latest: '{values[-1]}'"
        )
        return values[-1]  # Use latest for keywords

    elif "table" in out_name.lower():
        # For table outputs, merge JSON arrays
        all_tables = []
        for val in values:
            try:
                if val.strip().startswith("["):
                    tables = json.loads(val)
                    all_tables.extend(tables)
                else:
                    # Handle multi-line concatenated arrays
                    lines = [line.strip() for line in val.split("\n") if line.strip()]
                    for line in lines:
                        if line.startswith("["):
                            try:
                                tables = json.loads(line)
                                all_tables.extend(tables)
                            except json.JSONDecodeError:
                                continue
            except json.JSONDecodeError:
                continue

        merged = json.dumps(all_tables)
        debug.print_merge(
            f"Merged {len(values)} table outputs: {len(all_tables)} total tables"
        )
        return merged

    elif "document" in out_name.lower():
        # For document names, deduplicate
        unique_docs = []
        seen = set()
        for val in values:
            docs = [d.strip() for d in val.split(",")]
            for doc in docs:
                if doc and doc not in seen:
                    unique_docs.append(doc)
                    seen.add(doc)

        merged = ", ".join(unique_docs)
        debug.print_merge(f"Merged {len(values)} document references: '{merged}'")
        return merged

    elif "filtered data" in out_name.lower():
        # For filtered data, combine all filtered tables from different filtering steps
        all_tables = []
        for val in values:
            if val.strip():
                try:
                    tables = json.loads(val)
                    if isinstance(tables, list):
                        all_tables.extend(tables)
                except json.JSONDecodeError:
                    continue

        merged = json.dumps(all_tables)
        debug.print_merge(
            f"Combined {len(all_tables)} filtered tables from {len(values)} filter operations"
        )
        return merged

    else:
        # Default: Join with newlines
        merged = "\n".join(values)
        debug.print_merge(f"Using latest {out_name} from {len(values)} outputs")
        return values[-1]  # Use latest for most outputs


def handler_from_name(fname: str):
    """
    Convert function template name to Python function handler.

    Args:
        fname: Function name from template (e.g., "Table Search")

    Returns:
        Callable function from function_library
    """
    from agentic_reasoning.logic.function_library import FUNCTION_MAP

    if fname in FUNCTION_MAP:
        return FUNCTION_MAP[fname]
    else:
        raise ValueError(f"Function '{fname}' not found in FUNCTION_MAP")


def parse_json_response(text: str) -> Optional[Dict]:
    """
    Clean and parse JSON from LLM response.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    # Remove code blocks
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()

    # Extract JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def safe_json_parse(txt: str) -> Optional[Dict]:
    """
    Safely parse JSON with multiple fallback strategies.

    Args:
        txt: Text that should contain JSON

    Returns:
        Parsed JSON dict or None if all strategies fail
    """
    if not txt:
        return None

    # Strategy 1: Direct parsing
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code block
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first complete JSON object
    json_match = re.search(r"\{.*\}", txt, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None
