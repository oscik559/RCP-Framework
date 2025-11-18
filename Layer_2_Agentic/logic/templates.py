"""
Template library definitions for agentic workflow system.

Defines strategy templates, function definitions, and their parameter/output
schemas for the LangGraph-based reasoning pipeline. Templates are stored in
SQLite for dynamic workflow execution and can be modified without code changes.

Components:
- Strategy Templates: High-level reasoning approaches with function sequences
- Function Templates: Executable operations with type categorization
- Parameter/Output Schemas: Type definitions for function interfaces
- Template Population: Database initialization and update utilities

Strategy Function Plans:
- Use comma-separated function names for sequential execution
- Use [Func1 || Func2] syntax for parallel execution groups
- Support complex multi-step workflows with branching logic
"""

import logging
from pathlib import Path

from Layer_2_Agentic.db.connection import get_agentic_connection
from Layer_2_Agentic.db.schema_manager import init_db

logger = logging.getLogger("TEMPLATE")

# ── Strategy Templates ─────────────────────────────────────────────────────
# High-level reasoning approaches with function execution plans
# Format: (StrategyName, StrategyTarget, StrategyDescription, PlanSteps)

strategies = [
    # ── CORE PRODUCTION STRATEGIES (5 total) ──────────────────────────────
    # These are the primary strategies that cover 100% of use cases
    
    (
        "DIRECT SPECIFICATION LOOKUP",  
        "lookup",
        "Direct database lookup for specific product specifications. Fast deterministic path for product ID → specs queries.",
        "Extract Product Number, Query Database, Extract Attributes, Analyze With LLM",
    ),
    
    (
        "CONTEXTUAL PRODUCT SEARCH",  
        "search",
        "Multi-criteria product search with semantic understanding. Handles application-based queries (e.g., 'hose for hot water + high pressure').",
        "Extract Requirements, Semantic Search, Filter Items, Extract Attributes, Analyze With LLM",
    ),
    
    (
        "TECHNICAL CALCULATION",  
        "calculate",
        "Hydraulic engineering calculations (flow rate, pressure drop, hose sizing). Pure mathematical computations with product recommendations.",
        "Extract Calculation Inputs, Calculate, Convert Units, Search Products, Analyze With LLM",
    ),
    
    (
        "STANDARD & COMPLIANCE LOOKUP",  
        "compliance",
        "Search products by standards (EN, ISO, SAE) and certifications (FDA, DNV, MED). Database-driven compliance checking.",
        "Extract Standard Code, Query Database, Extract Attributes, Analyze With LLM",
    ),
    
    (
        "KNOWLEDGE BASE & RAG",  
        "knowledge",
        "Retrieval Augmented Generation for procedural and general knowledge. Handles assembly instructions, standards definitions, FAQ.",
        "Semantic Search Knowledge Base, Retrieve Documents, Extract Relevant Content, Analyze With LLM",
    ),
    
    # ── OPTIMIZATION PATTERNS (Future - keeps for Phase 2+) ────────────────
    # These patterns improve performance and are kept for future implementation
    
    (
        "PARALLEL ENHANCED LOOKUP",  
        "parallel",
        "Concurrent function execution for performance optimization. Independent functions run in parallel to reduce total execution time.",
        "Extract Product Number, Query Database, [Extract Attributes || Search Products], Filter Items, [Analyze With LLM || Convert Units], Aggregate Results, Analyze With LLM",
    ),
]

# ── Function Templates ──────────────────────────────────────────────────────
# Executable function definitions with type categorization
# Format: (FunctionName, StrategyType, FunctionDescription)
# ACTIVE ONLY: Functions required by the 6 core strategies (no legacy/experimental functions)

templates = [
    # ── CORE ACTIVE FUNCTIONS (used by at least one active strategy) ────────
    
    # Category 1: Query & Search
    (
        "Query Database",
        "search",
        "SQL Agent for executing custom database queries with joins, filters, aggregations, and complex conditions. Used by DIRECT SPECIFICATION LOOKUP and STANDARD & COMPLIANCE LOOKUP.",
    ),
    (
        "Search Products",
        "search",
        "Multi-criteria product search with flexible filtering by category, keywords, specifications, and certifications. Used by TECHNICAL CALCULATION and PARALLEL ENHANCED LOOKUP.",
    ),
    (
        "Semantic Search",
        "search",
        "Natural language search with synonym expansion using embeddings. Used by CONTEXTUAL PRODUCT SEARCH and KNOWLEDGE BASE & RAG.",
    ),
    
    # Category 2: Extract Operations
    (
        "Extract Product Number",
        "extract",
        "Extract product codes from user queries using LLM. First function in DIRECT SPECIFICATION LOOKUP and PARALLEL ENHANCED LOOKUP.",
    ),
    (
        "Extract Attributes",
        "extract",
        "Deterministic attribute extraction from product data with schema-aware parsing (no LLM, pure data extraction). Used by DIRECT SPECIFICATION LOOKUP, STANDARD & COMPLIANCE LOOKUP, CONTEXTUAL PRODUCT SEARCH, PARALLEL ENHANCED LOOKUP.",
    ),
    
    # Category 3: Data Processing
    (
        "Filter Items",
        "filter",
        "Generic filtering engine with complex conditions for any list of items. Used by CONTEXTUAL PRODUCT SEARCH and PARALLEL ENHANCED LOOKUP.",
    ),
    (
        "Aggregate Results",
        "aggregate",
        "GROUP BY operations with aggregation functions (count, sum, avg, min, max). Used by PARALLEL ENHANCED LOOKUP for result aggregation.",
    ),
    
    # Category 4: Calculations & Conversions
    (
        "Calculate",
        "calculate",
        "Technical calculations for hydraulic systems including hose dimensions, flow rates, and pressure. Core function of TECHNICAL CALCULATION strategy.",
    ),
    (
        "Convert Units",
        "convert",
        "Unit conversion with LLM assistance for complex or context-dependent conversions. Used by TECHNICAL CALCULATION and PARALLEL ENHANCED LOOKUP.",
    ),
    
    # Category 5: Analysis
    (
        "Analyze With LLM",
        "analyze",
        "Dual-mode LLM analysis: accepts direct context (small data) or queries temp.db (large assembled data). Final function in all 6 strategies.",
    ),
]


# ── Function Parameter Schemas ──────────────────────────────────────────────
# Input parameter definitions for each ACTIVE function
# Format: (ParameterName, DefaultValue, Type)

params = {
    # Category 1: Query & Search
    "Query Database": [
        ("query_type", "select", "string"),  # "select", "count", "distinct", "custom"
        ("table", "products", "string"),
        ("Keyword Output", "", "string"),  # Product codes from Extract Product Number
        ("fields", "[]", "json"),
        ("joins", "[]", "json"),
        ("order_by", "", "string"),
        ("limit", "100", "integer"),
        ("custom_sql", "", "string"),
    ],
    "Search Products": [
        ("category", "", "string"),
        ("keywords", "Input", "string"),
        ("filters", "{}", "json"),
        ("limit", "50", "integer"),
    ],
    "Semantic Search": [
        ("query", "Input", "string"),
        ("top_k", "10", "integer"),
        ("filters", "{}", "json"),
    ],
    
    # Category 2: Extract Operations
    "Extract Product Number": [
        ("Input", "", "string"),
    ],
    "Extract Attributes": [
        ("items", "", "json"),
        ("extraction_type", "auto", "string"),
        ("config", "{}", "json"),
    ],
    
    # Category 3: Data Processing
    "Filter Items": [
        ("items", "[]", "json"),
        ("conditions", "[]", "json"),
        ("mode", "AND", "string"),
    ],
    "Aggregate Results": [
        ("items", "[]", "json"),
        ("group_by", "", "string"),
        ("aggregations", "[]", "json"),
    ],
    
    # Category 4: Calculations & Conversions
    "Calculate": [
        ("calculation_type", "", "string"),
        ("inputs", "{}", "json"),
    ],
    "Convert Units": [
        ("value", "0", "number"),
        ("from_unit", "", "string"),
        ("to_unit", "", "string"),
        ("context", "", "string"),
    ],
    
    # Category 5: Analysis
    "Analyze With LLM": [
        ("task", "advice", "string"),
        ("extracted_data", "", "json"),
        ("Assembled Data", "", "json"),
        ("question", "Input", "string"),
    ],
}

# ── Function Output Schemas ──────────────────────────────────────────────────
# Output definitions for each ACTIVE function
# Format: (OutputName, DefaultValue, Type)

outputs = {
    # Category 1: Query & Search
    "Query Database": [
        ("items", "[]", "json"),
        ("count", "0", "integer"),
    ],
    "Search Products": [
        ("Products", "[]", "json"),
        ("Count", "0", "integer"),
        ("items", "[]", "json"),
    ],
    "Semantic Search": [
        ("results", "[]", "json"),
        ("scores", "[]", "json"),
        ("count", "0", "integer"),
    ],
    
    # Category 2: Extract Operations
    "Extract Product Number": [
        ("Keyword Output", "", "string"),
    ],
    "Extract Attributes": [
        ("extracted_data", "[]", "json"),
        ("extraction_type", "auto", "string"),
        ("count", "0", "integer"),
    ],
    
    # Category 3: Data Processing
    "Filter Items": [
        ("filtered_items", "[]", "json"),
        ("count", "0", "integer"),
        ("conditions_applied", "[]", "json"),
    ],
    "Aggregate Results": [
        ("aggregated_results", "[]", "json"),
        ("group_field", "", "string"),
        ("total_groups", "0", "integer"),
    ],
    
    # Category 4: Calculations & Conversions
    "Calculate": [
        ("result", "0", "number"),
        ("calculation_type", "", "string"),
        ("units", "", "string"),
        ("formula_used", "", "string"),
    ],
    "Convert Units": [
        ("converted_value", "0", "number"),
        ("original_value", "0", "number"),
        ("from_unit", "", "string"),
        ("to_unit", "", "string"),
        ("explanation", "", "string"),
    ],
    
    # Category 5: Analysis
    "Analyze With LLM": [
        ("Analysis", "", "string"),
        ("Task", "", "string"),
        ("Context", "", "string"),
    ],
}


# ── Database Population Function ─────────────────────────────────────────────


def populate_template_libraries():
    """Initialize database with strategy and function templates."""
    logger.info("Initializing template libraries in agentic database...")
    init_db(drop_and_recreate=True)

    with get_agentic_connection() as conn:
        cur = conn.cursor()

        # Clear existing session data and templates
        cur.executescript(
            """
            DELETE FROM GoalInSession;
            DELETE FROM FunctionInSession;
            DELETE FROM FunctionOutputInSession;
            DELETE FROM FunctionParametersInSession;
            DELETE FROM StrategyInSession;
            DELETE FROM FunctionTemplateLibrary;
            DELETE FROM FunctionOutputLibrary;
            DELETE FROM FunctionParametersLibrary;
            DELETE FROM StrategyLibrary;
        """
        )

        # Populate strategy templates
        for sname, starg, sdesc, plan in strategies:
            cur.execute(
                """
                INSERT INTO StrategyLibrary (StrategyName, StrategyTarget, StrategyDescription, PlanSteps)
                VALUES (?, ?, ?, ?)
            """,
                (sname, starg, sdesc, plan),
            )

        # Populate function templates with parameters and outputs
        for fname, stype, fdesc in templates:
            cur.execute(
                """
                INSERT INTO FunctionTemplateLibrary (FunctionName, StrategyType, FunctionDescription)
                VALUES (?, ?, ?)
            """,
                (fname, stype, fdesc),
            )
            fid = cur.lastrowid

            # Add function outputs
            for oname, oval, otype in outputs.get(fname, []):
                cur.execute(
                    """
                    INSERT INTO FunctionOutputLibrary (FunctionTemplateID, OutputName, OutputValue, Type)
                    VALUES (?, ?, ?, ?)
                """,
                    (fid, oname, oval, otype),
                )

            # Add function parameters
            for pname, pval, ptype in params.get(fname, []):
                cur.execute(
                    """
                    INSERT INTO FunctionParametersLibrary (FunctionTemplateID, ParameterName, ParameterValue, Type)
                    VALUES (?, ?, ?, ?)
                """,
                    (fid, pname, pval, ptype),
                )

        conn.commit()
        logger.info("✅ Library tables populated in agentic database.")


if __name__ == "__main__":
    populate_template_libraries()
