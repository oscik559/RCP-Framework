# Optimized Strategy Framework
**Date:** November 18, 2025  
**Status:** Ready for Implementation  
**Coverage:** 79/79 questions (100%)

---

## Executive Summary

Consolidated from 12 strategies → **5 core strategies** with clear non-overlapping scope:

1. **DIRECT SPECIFICATION LOOKUP** - Fast product ID → specs queries
2. **CONTEXTUAL PRODUCT SEARCH** - Multi-criteria filtering + LLM reasoning
3. **TECHNICAL CALCULATION** - Hydraulic/flow calculations + sizing
4. **STANDARD & COMPLIANCE LOOKUP** - Certification + standard matching
5. **KNOWLEDGE BASE & RAG** - Procedural/general knowledge retrieval (future implementation)

---

## Strategy Details & Function Blocks

### 1️⃣ DIRECT SPECIFICATION LOOKUP
**Priority:** ⭐⭐⭐⭐⭐ (30+ questions)

#### Use Cases
- "What is the maximum working pressure for hose 1071-00-16?"
- "Which socket fits 1118-12-16?"
- "Can I use environmental oil in 1105-63?"
- "What is the maximum temperature for hose 1071-00-16?"

#### Function Block
```
Input:
  - product_id: str (article number, e.g., "1071-00-16")
  - spec_query: str (optional, e.g., "temperature", "pressure", "coupling")
  - database_path: str = "database/harvested.db"

Processing:
  1. Extract Product ID from input
  2. Query harvested.db → products table
     WHERE article_number = product_id
  3. Extract relevant specifications (JSON fields)
  4. If spec_query provided: filter to specific field
  5. Format response with context (hose name, family)

Output:
  - success: bool
  - data: {
      product_id: str,
      product_name: str,
      family: str,
      specifications: dict (all specs)
      requested_spec: any (if spec_query provided)
    }
  - source: str ("direct_db_lookup")

Error Handling:
  - Product not found → Suggest related products
  - Ambiguous spec → List available specs with clarification prompt
```

#### Implementation Pseudocode
```python
def direct_specification_lookup(product_id: str, spec_query: str = None, 
                                 database_path: str = "database/harvested.db"):
    """
    Fast direct lookup for product specifications by article number.
    No LLM needed - pure deterministic database extraction.
    """
    conn = sqlite3.connect(database_path)
    
    # Query product by ID
    product = conn.execute(
        "SELECT article_number, product_name, family, specifications FROM products "
        "WHERE article_number = ?",
        (product_id,)
    ).fetchone()
    
    if not product:
        return False, {"error": f"Product {product_id} not found"}
    
    specs = json.loads(product[3])
    
    # Extract specific spec if requested
    if spec_query:
        target = specs.get(spec_query.lower())
        if target is None:
            available = list(specs.keys())
            return False, {
                "error": f"Spec '{spec_query}' not found",
                "available_specs": available
            }
        return True, {
            "product_id": product_id,
            "product_name": product[1],
            "requested_spec": target
        }
    
    return True, {
        "product_id": product_id,
        "product_name": product[1],
        "family": product[2],
        "specifications": specs
    }
```

---

### 2️⃣ CONTEXTUAL PRODUCT SEARCH
**Priority:** ⭐⭐⭐⭐ (35+ questions)

#### Use Cases
- "What hoses can be used for boiling water?"
- "Which hydraulic hose and sleeve should I get for an excavator?"
- "What hoses can be used for chemicals?"
- "Do you have a product that can withstand both high pressure and vibrations?"
- "Hose for alkaline degreasing?"

#### Function Block
```
Input:
  - context: str (full user query, e.g., "hose for hot water and high pressure")
  - filter_criteria: dict (optional, e.g., {"material": "rubber", "temp_min": 100})
  - limit: int = 10
  - database_path: str = "database/harvested.db"

Processing:
  1. Parse context using LLM → extract requirements
     Output: {materials, temperature_range, pressure_range, application, certifications}
  
  2. Semantic search in vector_index (Chroma)
     Query: "hoses for {extracted_application}"
     Top-k: 15 candidates
  
  3. Filter by criteria:
     - Temperature: min_temp >= user_min, max_temp >= user_need
     - Pressure: working_pressure >= user_need
     - Material: matches user preference
     - Certifications: if requested (FDA, DNV, etc.)
  
  4. Score & rank by relevance:
     - Semantic similarity score (0.7+)
     - Criteria match count
     - Product availability
  
  5. For top N results: compile specifications
  
  6. Generate LLM synthesis with recommendations

Output:
  - success: bool
  - products: [
      {
        product_id: str,
        product_name: str,
        family: str,
        specifications: dict,
        match_score: float,
        why_recommended: str (LLM synthesis)
      },
      ...
    ]
  - llm_analysis: str (comprehensive answer with reasoning)
  - source: str ("contextual_search")

Error Handling:
  - No results → Suggest related searches
  - Ambiguous requirements → Ask for clarification
```

#### Implementation Pseudocode
```python
def contextual_product_search(context: str, filter_criteria: dict = None, 
                               limit: int = 10, database_path: str = "database/harvested.db"):
    """
    Multi-criteria product search with semantic understanding.
    Combines FTS5, semantic search, and LLM reasoning.
    """
    # Step 1: LLM context extraction
    requirements = extract_requirements_llm(context)
    # Returns: {materials, temp_range, pressure_range, application, certifications}
    
    # Step 2: Semantic search
    chroma_client = get_chroma_client()
    semantic_results = chroma_client.query(
        query_texts=[requirements["application"]],
        n_results=15
    )
    product_ids = [meta["product_id"] for meta in semantic_results["metadatas"][0]]
    
    # Step 3: Filter by criteria
    conn = sqlite3.connect(database_path)
    candidates = []
    
    for pid in product_ids:
        product = conn.execute(
            "SELECT * FROM products WHERE article_number = ?", (pid,)
        ).fetchone()
        
        specs = json.loads(product["specifications"])
        
        # Apply filters
        if requirements["temp_range"]:
            if specs.get("max_temp") < requirements["temp_range"][0]:
                continue
        if requirements["pressure_range"]:
            if specs.get("working_pressure") < requirements["pressure_range"][0]:
                continue
        
        candidates.append({
            "product_id": pid,
            "product_name": product["product_name"],
            "specifications": specs,
            "semantic_score": semantic_results["distances"][0][product_ids.index(pid)]
        })
    
    # Step 4: Score & rank
    candidates = sorted(candidates, key=lambda x: x["semantic_score"], reverse=True)[:limit]
    
    # Step 5: LLM synthesis
    synthesis = synthesize_recommendation_llm(context, candidates)
    
    return True, {
        "products": candidates,
        "llm_analysis": synthesis,
        "requirements_interpreted": requirements
    }
```

---

### 3️⃣ TECHNICAL CALCULATION
**Priority:** ⭐⭐⭐ (5+ questions)

#### Use Cases
- "The flow is 150 liters per minute, what hose dimension should I choose for pressure?"
- "The flow is 20 liters per minute, what hose dimension for suction/return?"
- "The flow is 100 liters per minute and I can have max pressure drop of 200 millibars - what hose dimension?"

#### Function Block
```
Input:
  - calculation_type: str (enum: "hose_sizing", "pressure_drop", "flow_velocity")
  - flow_rate: float (L/min)
  - pressure: float (bar, optional)
  - max_pressure_drop: float (bar, optional)
  - line_type: str (enum: "pressure", "suction", "return")
  - hose_length: float = 5.0 (meters, for pressure drop calc)
  - hydraulic_oil_viscosity: str = "ISO VG 46" (default)

Processing:
  1. Normalize inputs (handle unit conversions)
  
  2. Select calculation logic based on calculation_type:
  
     a) HOSE_SIZING:
        - Target flow velocity = 4-5 m/s (pressure), 1-2 m/s (suction), 2-3 m/s (return)
        - Calculate required ID: A = Q / v
          where A = cross-sectional area (mm²), Q = flow (mm³/s), v = velocity (mm/s)
        - Map to standard hose sizes from database
        - Return options with velocities achieved
     
     b) PRESSURE_DROP:
        - Use Darcy-Weisbach equation: ΔP = f * (L/D) * (ρ * v²) / 2
        - For laminar (Re < 2300): f = 64/Re
        - For turbulent (Re > 2300): use Colebrook-White
        - Calculate for candidate hose sizes
        - Return size that keeps ΔP <= max_pressure_drop
     
     c) FLOW_VELOCITY:
        - Simple: v = Q / A
        - Return achievable velocities for standard sizes
  
  3. Query database for available hose products matching calculated dimensions
  
  4. Filter for suitability (standard, in stock, suitable for application)
  
  5. Format recommendations with technical justification

Output:
  - success: bool
  - calculation_type: str
  - recommended_dimension: str (e.g., "1 1/4\"", "32mm")
  - alternative_dimensions: [str]
  - results: {
      required_area_mm2: float,
      target_velocity: float (m/s),
      achieved_velocity: float (m/s),
      pressure_drop: float (bar, if applicable),
      margin: float (%)
    }
  - recommended_products: [{product_id, product_name, specifications}]
  - engineering_notes: str (explanation)

Error Handling:
  - Invalid inputs → Validate and request clarification
  - No suitable products → Suggest next-best size with warning
```

#### Implementation Pseudocode
```python
def technical_calculation(calculation_type: str, flow_rate: float, 
                          line_type: str, pressure: float = None,
                          max_pressure_drop: float = None, hose_length: float = 5.0):
    """
    Perform hydraulic calculations for hose sizing and pressure drop.
    Pure math - no LLM needed, deterministic output.
    """
    # Define target velocities (m/s)
    velocity_targets = {
        "pressure": (4, 5),
        "suction": (1, 2),
        "return": (2, 3)
    }
    
    v_target = sum(velocity_targets[line_type]) / 2  # middle of range
    
    # Calculate required cross-sectional area
    # Q [L/min] → [mm³/s]: multiply by 16.667
    Q_mm3_s = flow_rate * 16.667
    v_mm_s = v_target * 1000
    A_mm2 = Q_mm3_s / v_mm_s
    
    # Map to standard hose sizes
    standard_sizes = get_standard_hose_sizes()  # from DB
    candidates = []
    
    for size_name, size_id_mm in standard_sizes:
        area = (size_id_mm / 2) ** 2 * 3.14159
        achieved_v = Q_mm3_s / area / 1000
        
        # Calculate pressure drop if requested
        pressure_drop = None
        if max_pressure_drop is not None:
            pressure_drop = calculate_pressure_drop(
                flow_rate, size_id_mm, hose_length, hydraulic_oil_viscosity
            )
            if pressure_drop > max_pressure_drop:
                continue  # Filter out
        
        candidates.append({
            "size": size_name,
            "id": size_id_mm,
            "area": area,
            "velocity": achieved_v,
            "pressure_drop": pressure_drop
        })
    
    # Recommend: size with velocity closest to target
    recommended = min(candidates, 
                      key=lambda c: abs(c["velocity"] - v_target))
    
    # Query products matching recommended size
    conn = sqlite3.connect("database/harvested.db")
    products = conn.execute(
        "SELECT * FROM products WHERE dimension_size = ? LIMIT 5",
        (recommended["size"],)
    ).fetchall()
    
    return True, {
        "recommended_dimension": recommended["size"],
        "achieved_velocity": recommended["velocity"],
        "pressure_drop": recommended.get("pressure_drop"),
        "recommended_products": products
    }
```

---

### 4️⃣ STANDARD & COMPLIANCE LOOKUP
**Priority:** ⭐⭐⭐ (5+ questions)

#### Use Cases
- "Do you have hoses that meet the EN 857 standard?"
- "What standards are there for hydraulic hose?"
- "Which hoses are FDA approved for food use?"
- "Which hoses are DNV classified?"

#### Function Block
```
Input:
  - query_type: str (enum: "find_by_standard", "list_standards", "find_by_certification")
  - standard_or_cert: str (e.g., "EN 857", "FDA", "DNV", "REACH")
  - product_id: str (optional, to check specific product)
  - category: str (optional, filter by "food", "marine", "industrial")
  - database_path: str = "database/harvested.db"

Processing:
  1. Parse query type and determine search approach
  
  2. If query_type == "find_by_standard":
     - Query products table WHERE standards LIKE '%{standard}%'
     - Extract matching products
     - Group by standard level/class if applicable
     - Return with context
  
  3. If query_type == "list_standards":
     - Query knowledge database for standard definitions
     - Return comprehensive list with descriptions
     - Include ISO, EN, SAE standards with scope
  
  4. If query_type == "find_by_certification":
     - Query products WHERE certifications LIKE '%{cert}%'
     - Verify certification metadata
     - Return with compliance details
  
  5. Format with context (why this standard, applicable uses)

Output:
  - success: bool
  - query_type: str
  - results: [
      {
        product_id: str,
        product_name: str,
        standards_met: [str],
        certifications: [str],
        compliance_details: dict
      },
      ...
    ]
  - context: str (explanation of standard/certification)
  - related_standards: [str] (if applicable)

Error Handling:
  - Unknown standard → Suggest similar standards
  - No products found → Return standard description + guidance
```

#### Implementation Pseudocode
```python
def standard_and_compliance_lookup(query_type: str, standard_or_cert: str,
                                    product_id: str = None, category: str = None,
                                    database_path: str = "database/harvested.db"):
    """
    Lookup products by standards and certifications.
    Pure database query - no LLM needed.
    """
    conn = sqlite3.connect(database_path)
    
    if query_type == "find_by_standard":
        # Find all products meeting standard
        query = """
            SELECT article_number, product_name, standards, certifications 
            FROM products 
            WHERE standards LIKE ?
        """
        results = conn.execute(query, (f"%{standard_or_cert}%",)).fetchall()
        
        if not results:
            return False, {
                "error": f"No products found for standard {standard_or_cert}",
                "suggestion": "Try a related standard (e.g., EN 853 instead of EN 857)"
            }
        
        return True, {
            "products": [
                {
                    "product_id": r[0],
                    "product_name": r[1],
                    "standards": json.loads(r[2]),
                    "certifications": json.loads(r[3])
                }
                for r in results
            ],
            "query_type": query_type
        }
    
    elif query_type == "find_by_certification":
        # Find all products with certification
        query = """
            SELECT article_number, product_name, certifications, compliance_metadata
            FROM products
            WHERE certifications LIKE ?
        """
        results = conn.execute(query, (f"%{standard_or_cert}%",)).fetchall()
        
        return True, {
            "products": [
                {
                    "product_id": r[0],
                    "product_name": r[1],
                    "certifications": json.loads(r[2]),
                    "compliance": json.loads(r[3]) if r[3] else {}
                }
                for r in results
            ]
        }
    
    elif query_type == "list_standards":
        # Return all standards + descriptions from knowledge base
        standards = conn.execute(
            "SELECT standard_code, description, scope FROM standards"
        ).fetchall()
        
        return True, {
            "standards": [
                {
                    "code": s[0],
                    "description": s[1],
                    "scope": s[2]
                }
                for s in standards
            ]
        }
```

---

## Function Dependency Map

```
DIRECT SPECIFICATION LOOKUP
├── Extract Product ID (string parsing)
├── Query DB (simple SELECT)
└── Format Response

CONTEXTUAL PRODUCT SEARCH
├── LLM: Extract Requirements
├── Semantic Search (Chroma vector index)
├── DB Filter (FTS5 + criteria)
├── Score & Rank
├── LLM: Synthesis & Recommendations
└── Assemble Results

TECHNICAL CALCULATION
├── Input Validation & Normalization
├── Hydraulic Math (Darcy-Weisbach, etc.)
├── Standard Size Lookup
├── Pressure Drop Calculation
├── DB Query for Available Products
└── Format Engineering Output

STANDARD & COMPLIANCE LOOKUP
├── Parse Query Type
├── DB Query (standards/certifications table)
└── Format with Context
```

---

## Migration Path

### Phase 1: Build Core Functions (Recommended)
1. Implement `direct_specification_lookup()` → Deploy (simplest, highest ROI)
2. Implement `technical_calculation()` → Deploy (deterministic, no ML needed)
3. Implement `standard_and_compliance_lookup()` → Deploy

### Phase 2: Add Reasoning (Next)
4. Implement `contextual_product_search()` with LLM

### Phase 3: Optimize (Future)
- Add caching layer for repeated queries
- Add analytics for query patterns
- Refine LLM prompts based on feedback

---

---

### 5️⃣ KNOWLEDGE BASE & RAG
**Priority:** ⭐⭐ (4 questions - Future Implementation)

#### Use Cases
- "How do I install a shell sleeve?" (procedural instructions)
- "What is ISO bar?" (standard terminology)
- "Tell me about hydraulic systems" (general knowledge)
- System-level questions

#### Function Block
```
Input:
  - query: str (full user question)
  - query_type: str (enum: "procedural", "definition", "general_knowledge")
  - knowledge_base_path: str = "knowledge_base/hydroscand_knowledge.db"

Processing:
  1. Semantic search in knowledge base using embeddings
  2. Retrieve relevant documents/sections
  3. Rank by relevance
  4. Format with sources and references
  5. Optional: Augment with recent Q&A feedback

Output:
  - success: bool
  - answer: str (formatted response with sources)
  - confidence: float (0.0-1.0)
  - sources: [str] (document references)
  - related_topics: [str]

Note:
  - No agentic reasoning needed
  - Pure retrieval augmented generation
  - Can be implemented with vector embeddings + LLM formatting
  - Good candidate for caching (low volatility)
```

#### Implementation Notes
```python
# Simple skeleton - implement when needed
def knowledge_base_rag(query: str, query_type: str = "general_knowledge",
                       knowledge_base_path: str = "knowledge_base/hydroscand_knowledge.db"):
    """
    Retrieve knowledge from structured knowledge base.
    Uses semantic search + optional LLM synthesis.
    """
    # Step 1: Semantic search in knowledge base
    # Step 2: Rank results by relevance
    # Step 3: Format with context and sources
    # Step 4: Return with confidence score
    pass
```

---

## Coverage Matrix (100%)

```
Total Questions: 79
Covered: 79 ✅ (100%)

Strategy 1: DIRECT SPECIFICATION LOOKUP     [30 questions]
Strategy 2: CONTEXTUAL PRODUCT SEARCH       [35 questions]
Strategy 3: TECHNICAL CALCULATION           [5 questions]
Strategy 4: STANDARD & COMPLIANCE LOOKUP    [5 questions]
Strategy 5: KNOWLEDGE BASE & RAG            [4 questions] ⚠️ Future
```

---

## Next Steps

1. ✅ Review this framework
2. Update `templates.py` with 5 strategies (remove 12 old, keep PARALLEL ENHANCED LOOKUP)
3. Update `strategy_testing.py` to reflect new strategy set
4. Examine `harvested.db` to understand data coverage
5. Run `main.py` to analyze current system architecture
6. Create `function_library.py` implementations for strategies 1-4
7. Create test suite (`tests/functional/test_strategies.py`)
8. Validate with 79 test questions
9. Plan knowledge base structure for strategy 5

