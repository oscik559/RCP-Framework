#!/usr/bin/env python3
"""
Critical review of DIRECT_SPEC_LOOKUP strategy functions
Analyzes inputs, outputs, and justification for each function
"""

print("=" * 90)
print("CRITICAL REVIEW: DIRECT_SPEC_LOOKUP STRATEGY FUNCTIONS")
print("=" * 90)
print()

# Define the strategy
strategy = {
    "name": "DIRECT SPECIFICATION LOOKUP",
    "functions": [
        {
            "name": "Extract Product Number",
            "inputs": [
                ("Input", "string", "User's natural language query")
            ],
            "outputs": [
                ("Keyword Output", "string", "Product code extracted from query"),
            ],
            "justification": [
                "NECESSARY: Converts natural language query to machine-readable product code",
                "Example: 'What is Slang ID for product 4221-24-08?' → '4221-24-08'",
                "Why: Database queries work better with exact product codes than natural language",
            ]
        },
        {
            "name": "Query Database",
            "inputs": [
                ("query_type", "string", "'select' for product lookup"),
                ("table", "string", "'products' table"),
                ("filters", "string", "Product code from Extract Product Number (smart mode)"),
                ("fields", "json", "[] for all fields"),
                ("joins", "json", "[] for no joins"),
                ("order_by", "string", "Empty string"),
                ("limit", "int", "100 products max"),
                ("custom_sql", "string", "Generated SQL for exact product code match"),
            ],
            "outputs": [
                ("results", "json", "Array of product records matching the code"),
                ("count", "int", "Number of products found"),
                ("items", "json", "Same as results for downstream compatibility"),
            ],
            "justification": [
                "NECESSARY: Fetches actual product data from harvested.db",
                "Uses the extracted product code to query the database",
                "Returns full product record including 'specifications' JSON field",
                "Example output: [{'product_code': '4221-24-08', 'specifications': '{...}', 'family_id': 164, ...}]",
                "Why: Only source of truth for product specifications in the system",
            ]
        },
        {
            "name": "Extract Attributes",
            "inputs": [
                ("items", "json", "Product records from Query Database"),
                ("extraction_type", "string", "'auto' for deterministic schema-aware extraction"),
                ("config", "json", "{} for default extraction config"),
            ],
            "outputs": [
                ("extracted_data", "json", "Array of extracted product data with parsed specs"),
                ("count", "int", "Number of products extracted"),
                ("fields_found", "json", "All specification fields discovered"),
            ],
            "justification": [
                "NECESSARY: Parses 'specifications' JSON field into structured data",
                "Handles encoding and JSON parsing of specifications",
                "Extracts metadata (family_id, page_number, etc)",
                "Example: Parses '{\"Slang ID\": \"1/2\"}' from raw JSON string",
                "Why: Converts raw database records into clean, parsed product data",
                "Why: Deterministic extraction (no LLM) ensures consistency",
            ]
        },
        {
            "name": "Analyze With LLM",
            "inputs": [
                ("task", "string", "'advice' for technical analysis"),
                ("extracted_data", "json", "Parsed product data from Extract Attributes"),
                ("Assembled Data", "json", "Optional - for large multi-product assembly"),
                ("question", "string", "Original user query"),
            ],
            "outputs": [
                ("Analysis", "string", "LLM-generated answer to the user's question"),
                ("Task", "string", "Task type executed"),
                ("Context", "string", "Context summary used by LLM"),
            ],
            "justification": [
                "NECESSARY: Synthesizes extracted data into natural language answer",
                "Uses LLM to find relevant specification from parsed product data",
                "Supports both direct mode (small data) and assembly mode (large data)",
                "Direct mode: Passes extracted_data directly to LLM",
                "Assembly mode: Queries temp.db for large assembled datasets",
                "Example: LLM reads {\"Slang ID\": \"1/2\"} and answers 'The Slang ID is 1/2\"'",
                "Why: LLM synthesis provides natural language explanation, not just data",
                "Why: Handles complexity - knows to ignore irrelevant fields, focus on target",
            ]
        },
    ]
}

# Print analysis
for i, func in enumerate(strategy["functions"], 1):
    print(f"\n{'='*90}")
    print(f"FUNCTION {i}: {func['name']}")
    print(f"{'='*90}")
    
    print(f"\n┌─ INPUTS ({len(func['inputs'])} parameters):")
    for param, ptype, desc in func['inputs']:
        print(f"│  • {param:<20} : {ptype:<15} = {desc}")
    print(f"└─")
    
    print(f"\n┌─ OUTPUTS ({len(func['outputs'])} fields):")
    for output, otype, desc in func['outputs']:
        print(f"│  • {output:<20} : {otype:<15} = {desc}")
    print(f"└─")
    
    print(f"\n┌─ WHY THIS FUNCTION IS NECESSARY:")
    for j, reason in enumerate(func['justification'], 1):
        print(f"│  {j}. {reason}")
    print(f"└─")

# Data flow visualization
print(f"\n\n{'='*90}")
print("DATA FLOW VISUALIZATION")
print(f"{'='*90}\n")

flow = """
User Query: "What is the Slang ID for the product 4221-24-08?"
     ↓
┌────────────────────────────────────────────────────────────────┐
│ [1] Extract Product Number                                     │
│     Input:  "What is the Slang ID for the product 4221-24-08?" │
│     Output: "4221-24-08"                                       │
│     Action: LLM extracts product code from natural language    │
└─────────────────┬────────────────────────────────────────────┘
                  ↓
┌────────────────────────────────────────────────────────────────┐
│ [2] Query Database                                             │
│     Input:  Product Code = "4221-24-08"                        │
│     Action: SQL query on harvested.db                          │
│     Output: [{                                                 │
│       "product_code": "4221-24-08",                            │
│       "specifications": "{                                      │
│         "Artikelnr.": "4221-24-08",                            │
│         "Gänga": "M 24 x 1,5",                                │
│         "Rör": "16,75 mm",                                     │
│         "Typ": "UF",                                           │
│         "Slang ID": "1/2\\"",                                  │
│         "family_id": 164                                       │
│       }",                                                       │
│       "page_number": 188                                       │
│     }]                                                          │
│                                                                │
│     Why: Only source of product data in system                │
└─────────────────┬────────────────────────────────────────────┘
                  ↓
┌────────────────────────────────────────────────────────────────┐
│ [3] Extract Attributes                                         │
│     Input:  Raw product records                                │
│     Action: Parse JSON, extract fields deterministically       │
│     Output: {                                                  │
│       "product_id": 1797,                                      │
│       "product_code": "4221-24-08",                            │
│       "specifications": {                                      │
│         "Artikelnr.": "4221-24-08",                            │
│         "Gänga": "M 24 x 1,5",                                │
│         "Rör": "16,75 mm",                                     │
│         "Typ": "UF",                                           │
│         "Slang ID": "1/2\\""                                   │
│       }                                                         │
│     }                                                           │
│                                                                │
│     Why: Convert raw JSON string to structured data            │
└─────────────────┬────────────────────────────────────────────┘
                  ↓
┌────────────────────────────────────────────────────────────────┐
│ [4] Analyze With LLM                                           │
│     Input:  Extracted product data + Original question         │
│     Question: "What is the Slang ID for product 4221-24-08?"   │
│     Data: { "Slang ID": "1/2\\"", ... }                        │
│                                                                │
│     LLM Processing:                                            │
│     1. Read the question → identifies target = "Slang ID"      │
│     2. Scan extracted_data → finds "Slang ID": "1/2\\""        │
│     3. Synthesize answer with explanation                      │
│                                                                │
│     Output: "The Slang ID for product 4221-24-08 is 1/2".     │
│              This is found on Page 188 of the catalog."        │
│                                                                │
│     Why: Provides natural language answer, not raw JSON        │
└────────────────────────────────────────────────────────────────┘
          ↓
    Final Answer: "The Slang ID for the product 4221-24-08 is 1/2"
                  (with explanation and source attribution)
"""

print(flow)

# Analysis summary
print(f"\n{'='*90}")
print("CRITICAL ANALYSIS SUMMARY")
print(f"{'='*90}\n")

summary = """
✓ EACH FUNCTION IS NECESSARY:

1. Extract Product Number: ESSENTIAL
   - Converts human query to machine-readable identifier
   - Database doesn't understand "find product 4221-24-08" but understands WHERE code='4221-24-08'
   - LLM needed to extract from variable query formats

2. Query Database: CRITICAL PATH
   - Accesses the only authoritative source (harvested.db)
   - No cached specifications, must query database
   - Returns raw JSON specifications that need parsing

3. Extract Attributes: DETERMINISTIC PARSING
   - Parses nested JSON specifications string into structured format
   - Removes encoding issues and ensures valid JSON
   - Deterministic (no LLM randomness) for reproducibility
   - Required because specifications are stored as JSON strings, not native records

4. Analyze With LLM: SYNTHESIS & EXPLANATION
   - Finds target attribute from parsed data using semantic understanding
   - Generates human-readable explanation
   - Would be brittle to hardcode field extraction (what if user asks for different field?)
   - LLM handles: matching user intent to data fields, generating explanation

NO REDUNDANCIES DETECTED:
- Each function performs a distinct transformation
- No function output is directly available from another
- Data format changes appropriately at each stage
- Each step is a prerequisite for the next

POTENTIAL IMPROVEMENTS:
- Could combine Extract Attributes + Analyze With LLM if we always return raw JSON
  BUT: Would lose human readability and explanation
- Could skip Extract Attributes for small datasets
  BUT: Adds complexity to handle both parsed and raw JSON in different functions
  
CONCLUSION: The 4-function pipeline is well-designed for this product specification query type.
Each function serves a clear, necessary purpose in transforming raw data into final answer.
"""

print(summary)

print("\n" + "=" * 90)
