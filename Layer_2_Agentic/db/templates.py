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

import sys
import logging
from pathlib import Path

# Add Layer_2_Agentic to path when running as script
if __name__ == "__main__":
    layer2_root = str(Path(__file__).parent.parent)
    if layer2_root not in sys.path:
        sys.path.insert(0, layer2_root)

from db.connection import get_agentic_connection
from db.schema_manager import init_db

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
    # ── New Generic Hydroscand Strategies ──────────────────────────────────
    (
        "PRODUCT COMPARISON",  # Compare multiple products with detailed analysis
        "compare",
        "Compare multiple hydraulic products side-by-side: search products → extract attributes → compare items → analyze with LLM for recommendations.",
        "Search Products, Extract Attributes, Compare Items, Analyze With LLM",
    ),
    (
        "TECHNICAL CALCULATION",  # Hydraulic engineering calculations
        "calculate",
        "Perform hydraulic calculations: search products → extract specifications → calculate dimensions/flow/pressure → convert units → analyze results.",
        "Search Products, Extract Attributes, Calculate, Convert Units, Analyze With LLM",
    ),
    (
        "STANDARD COMPLIANCE",  # Standards and certification checking
        "compliance",
        "Check product compliance with standards: search products → lookup standards → extract attributes → compare items → analyze compatibility.",
        "Search Products, Lookup Standard, Extract Attributes, Compare Items, Analyze With LLM",
    ),
    (
        "SMART RECOMMENDATION",  # Intelligent product recommendations
        "recommendation",
        "Provide intelligent product recommendations: semantic search → filter items → get related items → aggregate data → analyze with LLM.",
        "Semantic Search, Filter Items, Get Related Items, Aggregate Data, Analyze With LLM",
    ),
    (
        "HIERARCHICAL NAVIGATION",  # Navigate product families and relationships
        "navigation",
        "Navigate product hierarchies and discover related items: navigate hierarchy → discover items → get metadata → filter items → transform data.",
        "Navigate Hierarchy, Discover Items, Get Metadata, Filter Items, Transform Data",
    ),
    (
        "SPECIFICATION ANALYSIS",  # Deep specification analysis with calculations
        "analysis",
        "Analyze product specifications with calculations: search products → extract attributes → calculate → convert units → compare items → analyze with LLM.",
        "Search Products, Extract Attributes, Calculate, Convert Units, Compare Items, Analyze With LLM",
    ),
    (
        "DIRECT SPECIFICATION LOOKUP",  # Fast path for small datasets (< 20 products)
        "lookup",
        "Direct database lookup for specific product specifications with direct LLM analysis: query database → extract attributes → analyze with LLM (direct mode).",
        "Query Database, Extract Attributes, Analyze With LLM",
    ),
    (
        "ASSEMBLED SPECIFICATION LOOKUP",  # Scalable path for large datasets (20+ products)
        "lookup",
        "Scalable database lookup with temp.db assembly for large datasets: query database → extract attributes → assemble product data → analyze with LLM (assembly mode).",
        "Query Database, Extract Attributes, Assemble Product Data, Analyze With LLM",
    ),
    (
        "PRODUCT LOCATION",  # Find where product is located in catalogue
        "location",
        "Locate product in catalogue: search products → get metadata → extract location information (page number, chapter, category).",
        "Search Products, Get Metadata, Transform Data",
    ),
    # ── New Modular Strategic Patterns ──────────────────────────────────────
    (
        "APPLICATION SEARCH PATTERN",  # Semantic application-based search
        "application_search",
        "Semantic search for product applications: find products by use case, environment, industry, or compatibility requirements using intelligent semantic matching.",
        "Semantic Search, Extract Attributes, Search Products, Filter Items, Aggregate Data, Analyze With LLM",
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
    # New Generic Hydroscand Functions
    # Category 1: Search & Discovery
    (
        "Search Products",
        "search",
        "Multi-criteria product search with flexible filtering by category, keywords, specifications, and certifications",
    ),
    (
        "Query Database",
        "search",
        "SQL Agent for executing custom database queries with joins, filters, aggregations, and complex conditions",
    ),
    (
        "Get Related Items",
        "search",
        "Find related products by relationship type (compatible, alternatives, accessories, replacements)",
    ),
    (
        "Semantic Search",
        "search",
        "Natural language search with synonym expansion using embeddings",
    ),
    # Category 2: Data Processing
    (
        "Filter Items",
        "filter",
        "Generic filtering engine with complex conditions for any list of items",
    ),
    (
        "Aggregate Data",
        "aggregate",
        "GROUP BY operations with aggregation functions (count, sum, avg, min, max)",
    ),
    (
        "Transform Data",
        "transform",
        "Format transformation (flatten, extract, rename fields)",
    ),
    # Category 3: Comparison & Analysis
    (
        "Compare Items",
        "compare",
        "Compare multiple items across specified fields with side-by-side analysis",
    ),
    (
        "Extract Attributes",
        "extract",
        "Deterministic attribute extraction from product data with schema-aware parsing (no LLM, pure data extraction)",
    ),
    (
        "Assemble Product Data",
        "assemble",
        "Universal assembler that stores extracted data in temp.db for scalable LLM analysis with large datasets",
    ),
    (
        "Analyze With LLM",
        "analyze",
        "Dual-mode LLM analysis: accepts direct context (small data) or queries temp.db (large assembled data)",
    ),
    # Category 4: Calculations & Conversions
    (
        "Calculate",
        "calculate",
        "Technical calculations for hydraulic systems including hose dimensions, flow rates, and pressure",
    ),
    (
        "Convert Units",
        "convert",
        "Unit conversion with LLM assistance for complex or context-dependent conversions",
    ),
    (
        "Lookup Standard",
        "lookup",
        "Standard reference lookup (ISO, SAE, DIN, thread sizes)",
    ),
    # Category 5: Navigation & Discovery
    (
        "Navigate Hierarchy",
        "navigate",
        "Hierarchical traversal (parent→children, siblings, ancestors)",
    ),
    (
        "Discover Items",
        "search",
        "Pattern-based discovery with wildcards and fuzzy matching",
    ),
    (
        "Get Metadata",
        "metadata",
        "Domain metadata retrieval (families, categories, statistics, schema)",
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
    # New Generic Hydroscand Functions
    # Category 1: Search & Discovery
    "Search Products": [
        ("category", "", "string"),
        ("keywords", "Input", "string"),  # Use user query to extract product names/keywords
        ("filters", "{}", "json"),
        ("limit", "50", "integer"),
    ],
    "Query Database": [
        ("query_type", "select", "string"),  # "select", "count", "distinct", "custom"
        ("table", "products", "string"),
        ("filters", "Input", "string"),  # Smart mode: Can accept natural language query to extract product names
        ("fields", "[]", "json"),
        ("joins", "[]", "json"),
        ("order_by", "", "string"),
        ("limit", "100", "integer"),
        ("custom_sql", "", "string"),
    ],
    "Get Related Items": [
        ("product_id", "", "string"),
        ("relationship_type", "compatible", "string"),
        ("limit", "20", "integer"),
    ],
    "Semantic Search": [
        ("query", "Input", "string"),
        ("top_k", "10", "integer"),
        ("filters", "{}", "json"),
    ],
    # Category 2: Data Processing
    "Filter Items": [
        ("items", "[]", "json"),
        ("conditions", "[]", "json"),
        ("mode", "AND", "string"),
    ],
    "Aggregate Data": [
        ("items", "[]", "json"),
        ("group_by", "", "string"),
        ("aggregations", "[]", "json"),
    ],
    "Transform Data": [
        ("items", "[]", "json"),
        ("operation", "flatten", "string"),
        ("config", "{}", "json"),
    ],
    # Category 3: Comparison & Analysis
    "Compare Items": [
        ("items", "[]", "json"),
        ("fields", "[]", "json"),
    ],
    "Extract Attributes": [
        ("items", "", "json"),
        ("extraction_type", "auto", "string"),  # Changed to "auto" for deterministic schema-aware extraction
        ("config", "{}", "json"),
    ],
    "Assemble Product Data": [
        ("extracted_data", "", "json"),  # Collect extracted_data from Extract Attributes
        ("source_type", "product_specifications", "string"),
    ],
    "Analyze With LLM": [
        ("task", "advice", "string"),  # Technical advice/analysis
        ("extracted_data", "", "json"),  # Auto-collect from Extract Attributes (direct mode)
        ("Assembled Data", "", "json"),  # Auto-collect from Assemble Product Data (assembly mode) - MUST match output key exactly
        ("question", "Input", "string"),  # Use user's original query
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
    "Lookup Standard": [
        ("standard_type", "", "string"),
        ("identifier", "", "string"),
    ],
    # Category 5: Navigation & Discovery
    "Navigate Hierarchy": [
        ("start_node", "", "string"),
        ("direction", "children", "string"),
        ("hierarchy_type", "product_family", "string"),
        # Note: Default path used for template initialization only
        # Runtime uses CONFIG["harvested_db"] in function_library.py
        ("database_path", "database/harvested.db", "string"),
    ],
    "Discover Items": [
        ("pattern", "", "string"),
        ("match_type", "wildcard", "string"),
        ("threshold", "0.8", "number"),
    ],
    "Get Metadata": [
        ("metadata_type", "", "string"),
        ("scope", "", "string"),
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
    # New Generic Hydroscand Functions
    # Category 1: Search & Discovery
    "Search Products": [
        ("Products", "[]", "json"),
        ("Count", "0", "integer"),
        ("items", "[]", "json"),  # For compatibility with downstream functions like Extract Attributes
    ],
    "Query Database": [
        ("results", "[]", "json"),
        ("count", "0", "integer"),
        ("fields", "[]", "json"),
        ("items", "[]", "json"),  # For compatibility with Extract Attributes
    ],
    "Get Related Items": [
        ("related_items", "[]", "json"),
        ("relationship_type", "", "string"),
        ("count", "0", "integer"),
    ],
    "Semantic Search": [
        ("results", "[]", "json"),
        ("scores", "[]", "json"),
        ("count", "0", "integer"),
    ],
    # Category 2: Data Processing
    "Filter Items": [
        ("filtered_items", "[]", "json"),
        ("count", "0", "integer"),
        ("conditions_applied", "[]", "json"),
    ],
    "Aggregate Data": [
        ("aggregated_results", "[]", "json"),
        ("group_field", "", "string"),
        ("total_groups", "0", "integer"),
    ],
    "Transform Data": [
        ("transformed_items", "[]", "json"),
        ("operation", "", "string"),
        ("count", "0", "integer"),
    ],
    # Category 3: Comparison & Analysis
    "Compare Items": [
        ("comparison_table", "{}", "json"),
        ("similarities", "[]", "json"),
        ("differences", "[]", "json"),
    ],
    "Extract Attributes": [
        ("extracted_data", "[]", "json"),
        ("extraction_type", "", "string"),
        ("count", "0", "integer"),
    ],
    "Assemble Product Data": [
        ("Assembled Data", "", "string"),  # JSON string for Analyze With LLM
        ("records_inserted", "0", "integer"),
        ("fields_discovered", "0", "integer"),
    ],
    "Analyze With LLM": [
        ("Analysis", "", "string"),
        ("Task", "", "string"),
        ("Context", "", "string"),
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
    "Lookup Standard": [
        ("standard_details", "{}", "json"),
        ("standard_type", "", "string"),
        ("identifier", "", "string"),
    ],
    # Category 5: Navigation & Discovery
    "Navigate Hierarchy": [
        ("hierarchy", "{}", "json"),
        ("direction", "", "string"),
        ("levels_traversed", "0", "integer"),
    ],
    "Discover Items": [
        ("discovered_items", "[]", "json"),
        ("pattern", "", "string"),
        ("match_type", "", "string"),
        ("count", "0", "integer"),
    ],
    "Get Metadata": [
        ("metadata", "{}", "json"),
        ("metadata_type", "", "string"),
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
