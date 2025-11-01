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

from agentic_reasoning.db.connection import get_agentic_connection
from agentic_reasoning.db.schema_manager import init_db

logger = logging.getLogger("TEMPLATE")

# ── Strategy Templates ─────────────────────────────────────────────────────
# High-level reasoning approaches with function execution plans
# Format: (StrategyName, StrategyTarget, StrategyDescription, PlanSteps)

strategies = [
    (
        "SIMPLE LOOKUP",  # Fast path for direct product queries
        "search",
        "Direct product search and analysis for straightforward queries without complex processing.",
        "Extract Product Number, Table Search, Filter Table, Assemble Table, Analyze Data",
    ),
    (
        "ENHANCED LOOKUP",  # Comprehensive multi-step analysis
        "search",
        "Multi-step analysis: extract product code → normalize to family → suggest field keywords → cross-reference documents → assemble comprehensive data.",
        "Extract Product Number, Table Search, Filter Table, Normalize Product Number, Table Search, Filter Table, Suggest Keywords, Find Latest Document, Table Search On Document, Filter Table By Field, Assemble Table, Analyze Data",
    ),
    (
        "VISUAL LAYOUT",  # Image and document processing
        "image",
        "Product-focused visual query: extract product code → find product in tables → filter data → locate images from same document → generate visual layout → display images.",
        "Extract Product Number, Table Search, Filter Table, Generate Visual Layout, Display Images",
    ),
    (
        "PARALLEL ENHANCED LOOKUP",  # Concurrent processing for performance
        "parallel",
        "Concurrent data gathering: extract product code, then run independent preprocessing in parallel.",
        # Parallel groups: [Filter Table || Normalize Product Number] and [Filter Table || Suggest Keywords]
        "Extract Product Number, Table Search, [Filter Table || Normalize Product Number], Table Search, [Filter Table || Suggest Keywords], Find Latest Document, Table Search On Document, Filter Table By Field, Assemble Table, Analyze Data",
    ),
]

# ── Function Templates ──────────────────────────────────────────────────────
# Executable function definitions with type categorization
# Format: (FunctionName, StrategyType, FunctionDescription)

templates = [
    # Search Operations
    (
        "Table Search",
        "search",
        "Primary search function for extracting tables by keywords",
    ),
    (
        "Display Images",
        "display",
        "Display found images in VS Code editor for user viewing",
    ),
    (
        "Table Search On Document",
        "search",
        "Fetch tables from specific documents when data is insufficient",
    ),
    # Filter Operations
    (
        "Filter Table",
        "filter",
        "Remove irrelevant table rows based on keyword matching",
    ),
    (
        "Filter Table By Field",
        "filter",
        "Filter tables by field names in headers for field-based queries",
    ),
    # Extract Operations
    (
        "Extract Product Number",
        "extract",
        "Extract product codes from user queries - use first",
    ),
    (
        "Suggest Keywords",
        "extract",
        "Generate field/column keywords for enhanced searches",
    ),
    (
        "Normalize Product Number",
        "extract",
        "Convert product codes to family format (e.g., 'RPT 235 4309/350' → 'RPT2354')",
    ),
    (
        "Find Latest Document",
        "extract",
        "Identify most recent document for keyword-based retrieval",
    ),
    # Assembly Operations
    (
        "Assemble Table",
        "assemble",
        "Merge filtered tables into unified dataset with dynamic schema",
    ),
    # Analysis Operations
    (
        "Analyze Data",
        "analyze",
        "LLM-powered synthesis of assembled data to answer user queries",
    ),
    (
        "Generate Visual Layout",
        "visual",
        "Generate or retrieve visual layouts, diagrams, and technical illustrations with contextual information",
    ),
]


# ── Function Parameter Schemas ──────────────────────────────────────────────
# Input parameter definitions for each function
# Format: (ParameterName, DefaultValue, Type)

params = {
    # Search functions
    "Display Images": [("Image Output", "", "string")],
    "Table Search": [("Keyword Output", "", "string")],
    "Table Search On Document": [
        ("Latest Document Name", "", "string"),
        ("Keyword Output", "", "string"),
    ],
    # Filter functions
    "Filter Table": [("Keyword Output", "", "string"), ("Table Output", "", "string")],
    "Filter Table By Field": [
        ("Keyword Output", "", "string"),
        ("Table Output", "", "string"),
    ],
    # Extract functions
    "Extract Product Number": [("Input", "", "string")],
    "Suggest Keywords": [("Input", "", "string"), ("Keyword Output", "", "string")],
    "Normalize Product Number": [("Keyword Output", "", "string")],
    "Find Latest Document": [("Document Name", "", "string")],
    # Assembly functions
    "Assemble Table": [("Filtered Data", "", "string")],
    # Analysis functions
    "Analyze Data": [
        ("Assembled Data", "", "string"),
        ("Filtered Data", "", "string"),
        ("Input", "", "string"),
    ],
    "Generate Visual Layout": [
        ("Product Number Output", "", "string"),
        ("Filtered Data", "", "string"),
        ("Input", "", "string"),
    ],
}

# ── Function Output Schemas ──────────────────────────────────────────────────
# Output definitions for each function
# Format: (OutputName, DefaultValue, Type)

outputs = {
    # Search functions
    "Table Search": [("Document Name", "", "string"), ("Table Output", "", "json")],
    "Display Images": [
        ("Display Output", "", "string"),
        ("Images Shown", "", "string"),
        ("Image Output", "", "string"),
    ],
    "Table Search On Document": [("Table Output", "", "json")],
    # Filter functions
    "Filter Table": [("Filtered Data", "", "json")],
    "Filter Table By Field": [("Filtered Data", "", "json")],
    # Extract functions
    "Extract Product Number": [("Keyword Output", "", "string")],
    "Suggest Keywords": [("Keyword Output", "", "string")],
    "Normalize Product Number": [("Keyword Output", "", "string")],
    "Find Latest Document": [("Latest Document Name", "", "string")],
    # Assembly functions
    "Assemble Table": [("Assembled Data", "", "json")],
    # Analysis functions
    "Analyze Data": [("Analyze Output", "", "string")],
    "Generate Visual Layout": [
        ("Layout Output", "", "json"),
        ("Image Output", "", "json"),
        ("Document Name", "", "string"),
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
