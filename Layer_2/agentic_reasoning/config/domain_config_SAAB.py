"""
Domain Configuration - SAAB

This is the configuration for the SAAB technical documentation project.
Use this as a reference when creating configurations for other domains.

To use this configuration:
    cp domain_config_SAAB.py domain_config.py
"""

# =============================================================================
# DOMAIN INFORMATION
# =============================================================================

DOMAIN_NAME = "SAAB Technical Documentation"
DOMAIN_DESCRIPTION = "Query system for SAAB technical manuals, product specs, and diagrams"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Path to SAAB document database (harvested_db from config.yaml)
DATABASE_PATH = "../data/database/harvested.db"

# SAAB-specific database tables for extracted PDF content
DOMAIN_TABLES = {
    # Extracted content from SAAB PDF documents
    "extracted_tables": "extracted_tables",  # PDF table data storage (451+ tables)
    "stored_texts": "stored_texts",          # Extracted text content from PDFs
    "saved_images": "saved_images",          # Images, diagrams, and technical drawings
    "product_lookup": "product_lookup",      # SAAB product code mappings
    "summarized_doc": "summarized_doc",      # Document summaries and metadata
}

# Helper function for accessing table names
def get_table_name(table_key: str) -> str:
    """Get table name by key with fallback."""
    return DOMAIN_TABLES.get(table_key, table_key)

# =============================================================================
# FUNCTION LIBRARY
# =============================================================================

# SAAB-specific functions available in function_library.py
DOMAIN_FUNCTIONS = [
    {
        "name": "search_technical_specifications",
        "description": "Search SAAB technical specs by product code or keywords",
        "parameters": ["product_code", "keywords"],
        "returns": "technical_specifications"
    },
    {
        "name": "find_product_diagrams",
        "description": "Find diagrams and images for SAAB products",
        "parameters": ["product_code", "diagram_type"],
        "returns": "image_paths"
    },
    {
        "name": "search_product_tables",
        "description": "Search extracted tables from SAAB PDFs",
        "parameters": ["product_code", "table_keywords"],
        "returns": "table_data"
    },
    {
        "name": "get_document_summary",
        "description": "Get summary of SAAB technical document",
        "parameters": ["document_name"],
        "returns": "summary_text"
    },
]

# =============================================================================
# STRATEGY TEMPLATES
# =============================================================================

# Common query patterns for SAAB documentation
DOMAIN_STRATEGIES = [
    {
        "name": "ProductSpecificationLookup",
        "description": "Find detailed technical specifications for SAAB products",
        "applicable_when": "User asks for product specs, technical details, or parameters",
        "functions": ["search_technical_specifications", "search_product_tables"]
    },
    {
        "name": "DiagramAndImageRetrieval",
        "description": "Locate and retrieve technical diagrams and images",
        "applicable_when": "User needs visual documentation, diagrams, or schematics",
        "functions": ["find_product_diagrams", "search_saved_images"]
    },
    {
        "name": "DocumentExploration",
        "description": "Browse and summarize SAAB technical documentation",
        "applicable_when": "User wants to explore documents or needs summaries",
        "functions": ["get_document_summary", "search_stored_texts"]
    },
]

# =============================================================================
# QUERY EXAMPLES
# =============================================================================

# Example queries for SAAB system
EXAMPLE_QUERIES = [
    "Find technical specifications for product code SAAB-12345",
    "Show me diagrams for the hydraulic system in document XYZ",
    "What are the dimensions and weight specifications for component ABC?",
    "Compare specifications between product A and product B",
    "Find all tables mentioning pressure ratings in SAAB manuals",
]

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# LLM settings optimized for technical documentation
LLM_CONFIG = {
    "provider": "ollama",  # Using local Ollama for SAAB
    "model": "gpt-oss:20b-cloud",
    "temperature": 0.0,  # Deterministic for technical accuracy
    "max_tokens": 2000,
}

# SAAB-specific prompts
DOMAIN_PROMPTS = {
    "system": """You are an AI assistant specialized in SAAB technical documentation.
Your role is to help users query technical specifications, diagrams, and product information
from SAAB manuals and documentation. Always provide accurate, specific technical details
based on the extracted data.""",
    
    "goal_definition": """Analyze this technical query about SAAB products:
{query}

Define a clear goal that addresses the user's technical information needs.""",
    
    "strategy_selection": """Based on this technical goal:
{goal}

Select the most appropriate strategy from available SAAB documentation strategies.""",
}

# =============================================================================
# VECTOR SEARCH CONFIGURATION
# =============================================================================

# Vector search for SAAB documents
VECTOR_CONFIG = {
    "enabled": True,
    "collection_name": "saab_documents",
    "embedding_model": "text-embedding-ada-002",
    "chunk_size": 500,
    "chunk_overlap": 50,
}

# =============================================================================
# VALIDATION RULES
# =============================================================================

# SAAB-specific validation
VALIDATION_RULES = {
    "required_fields": ["product_code", "document_source"],
    "format_checks": {
        "product_code": r"^[A-Z]{4}-\d{5}$",  # SAAB product code format
    },
    "business_rules": [
        "All specifications must include units of measurement",
        "Image references must include document source",
    ],
}

# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

# Technical documentation output format
OUTPUT_CONFIG = {
    "format": "json",
    "include_metadata": True,
    "include_confidence": False,
    "include_source_docs": True,
    "date_format": "%Y-%m-%d",
}

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================

PERFORMANCE_CONFIG = {
    "cache_results": True,
    "cache_ttl_seconds": 7200,  # 2 hours cache for technical specs
    "max_parallel_functions": 5,
    "timeout_seconds": 60,  # Longer timeout for PDF processing
    "max_retries": 3,
}

# =============================================================================
# LOGGING AND MONITORING
# =============================================================================

LOGGING_CONFIG = {
    "log_level": "INFO",
    "log_file": "logs/saab_queries.log",
    "log_queries": True,
    "log_results": True,
    "log_errors": True,
}
