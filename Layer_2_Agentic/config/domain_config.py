"""
Domain Configuration - Hydroscand Produktbok

Active domain configuration for the Hydroscand product catalog project.
Uses the product database from Layer_1 extraction.

Database: database/harvested.db (335 products, 69 families)
"""

# =============================================================================
# DOMAIN INFORMATION
# =============================================================================

DOMAIN_NAME = "Hydroscand Produktbok"
DOMAIN_DESCRIPTION = "Query system for Hydroscand hydraulic hose products, families, and specifications"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Path to Hydroscand product database (relative to project root)
DATABASE_PATH = "database/harvested.db"

# Hydroscand-specific database tables for product catalog
DOMAIN_TABLES = {
    # Main product catalog tables
    "categories": "categories",              # Product categories (top level)
    "product_families": "product_families",  # Product family groupings
    "products": "products",                  # Individual product items
    
    # Full-text search table
    "product_families_fts": "product_families_fts",  # FTS5 search index
}

# Helper function for accessing table names
def get_table_name(table_key: str) -> str:
    """Get table name by key with fallback."""
    return DOMAIN_TABLES.get(table_key, table_key)

# =============================================================================
# FUNCTION LIBRARY
# =============================================================================

# Hydroscand-specific functions to implement
DOMAIN_FUNCTIONS = [
    {
        "name": "find_product_by_code",
        "description": "Find product details by product code",
        "parameters": ["product_code"],
        "returns": "product_details"
    },
    {
        "name": "search_products_by_category",
        "description": "Find all products in a category",
        "parameters": ["category_name"],
        "returns": "product_list"
    },
    {
        "name": "get_product_family_details",
        "description": "Get family specifications and all products in family",
        "parameters": ["family_code"],
        "returns": "family_data"
    },
    {
        "name": "compare_products",
        "description": "Compare technical specifications of two products",
        "parameters": ["product_code1", "product_code2"],
        "returns": "comparison_table"
    },
    {
        "name": "search_products_by_specs",
        "description": "Full-text search across product specifications",
        "parameters": ["spec_query"],
        "returns": "matching_products"
    },
    {
        "name": "list_all_categories",
        "description": "Return all available product categories",
        "parameters": [],
        "returns": "category_list"
    },
    {
        "name": "get_products_in_family",
        "description": "Get all products belonging to a family",
        "parameters": ["family_id"],
        "returns": "product_list"
    },
    {
        "name": "search_similar_products",
        "description": "Find products with similar specifications",
        "parameters": ["product_code"],
        "returns": "similar_products"
    },
]

# =============================================================================
# STRATEGY TEMPLATES
# =============================================================================

# Common query patterns for Hydroscand product catalog
DOMAIN_STRATEGIES = [
    {
        "name": "ProductLookup",
        "description": "Direct product lookup by code or ID",
        "applicable_when": "User asks for specific product by code",
        "functions": ["find_product_by_code", "get_product_family_details"]
    },
    {
        "name": "CategoryBrowse",
        "description": "Explore products by category",
        "applicable_when": "User wants to browse products in a category",
        "functions": ["list_all_categories", "search_products_by_category", "get_products_in_family"]
    },
    {
        "name": "ProductComparison",
        "description": "Compare specifications of multiple products",
        "applicable_when": "User wants to compare two or more products",
        "functions": ["find_product_by_code", "compare_products"]
    },
    {
        "name": "SpecificationSearch",
        "description": "Search products by technical specifications",
        "applicable_when": "User searches by specs (pressure, temperature, size, etc.)",
        "functions": ["search_products_by_specs", "search_similar_products"]
    },
]

# =============================================================================
# QUERY EXAMPLES
# =============================================================================

# Example queries for Hydroscand system
EXAMPLE_QUERIES = [
    "Find product 1059-0101",
    "Show me all hydraulic hoses in the catalog",
    "Compare products 1059-0101 and 1059-0401",
    "What products have a pressure rating above 350 bar?",
    "List all products in family 1059-01",
    "Show me products similar to 1059-0101",
    "What categories are available?",
    "Find hoses suitable for high temperature applications",
]

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# LLM settings optimized for product catalog queries
LLM_CONFIG = {
    "provider": "ollama",  # Using local Ollama
    "model": "qwen3-vl:235b-cloud",  # Or gpt-oss:20b-cloud
    "temperature": 0.0,  # Deterministic for product accuracy
    "max_tokens": 2000,
}

# Hydroscand-specific prompts
DOMAIN_PROMPTS = {
    "system": """You are an AI assistant specialized in Hydroscand hydraulic hose products.
Your role is to help users find products, compare specifications, and navigate the
product catalog. Always provide accurate product codes, specifications, and technical
details based on the database.""",
    
    "goal_definition": """Analyze this query about Hydroscand products:
{query}

Define a clear goal that addresses the user's product information needs.""",
    
    "strategy_selection": """Based on this goal about Hydroscand products:
{goal}

Select the most appropriate strategy from available product catalog strategies.""",
}

# =============================================================================
# VECTOR SEARCH CONFIGURATION
# =============================================================================

# Vector search for product descriptions (optional)
VECTOR_CONFIG = {
    "enabled": False,  # Can enable for semantic product search
    "collection_name": "hydroscand_products",
    "embedding_model": "text-embedding-ada-002",
    "chunk_size": 500,
    "chunk_overlap": 50,
}

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Hydroscand-specific validation
VALIDATION_RULES = {
    "required_fields": ["product_code", "family_code"],
    "format_checks": {
        "product_code": r"^\d{4}-\d{4}$",  # Format: 1059-0101
        "family_code": r"^\d{4}-\d{2}$",   # Format: 1059-01
    },
    "business_rules": [
        "All products must belong to a valid family",
        "All families must belong to a valid category",
        "Specifications must include units where applicable",
    ],
}

# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

# Product catalog output format
OUTPUT_CONFIG = {
    "format": "json",
    "include_metadata": True,
    "include_confidence": False,
    "include_family_info": True,
    "include_category_info": True,
    "date_format": "%Y-%m-%d",
}

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================

PERFORMANCE_CONFIG = {
    "cache_results": True,
    "cache_ttl_seconds": 3600,  # 1 hour cache for product specs
    "max_parallel_functions": 3,
    "timeout_seconds": 30,
    "max_retries": 3,
}

# =============================================================================
# LOGGING AND MONITORING
# =============================================================================

LOGGING_CONFIG = {
    "log_level": "INFO",
    "log_file": "logs/hydroscand_queries.log",
    "log_queries": True,
    "log_results": True,
    "log_errors": True,
}

# =============================================================================
# SCHEMA REFERENCE
# =============================================================================

# Database schema for reference (from Layer_1/schema.sql)
SCHEMA_INFO = """
-- Categories (top level)
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

-- Product Families (grouped by category)
CREATE TABLE product_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_code TEXT NOT NULL,
    family_name TEXT,
    category_id INTEGER,
    specifications TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Products (individual items)
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    family_id INTEGER,
    description TEXT,
    technical_specs TEXT,
    FOREIGN KEY (family_id) REFERENCES product_families(id)
);

-- Full-text search
CREATE VIRTUAL TABLE product_families_fts USING fts5(
    family_code, family_name, specifications,
    content=product_families, content_rowid=id
);
"""
