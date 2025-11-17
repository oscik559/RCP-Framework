# Agentic Reasoning Strategy Framework - Proposal

## Executive Summary

Your system needs **query-specific strategies** that leverage existing generic functions to answer different types of product questions. Current scaffolding includes powerful, reusable functions; the task is organizing them into coherent strategy patterns.

---

## Database Inventory

### 1. **harvested.db** (Product Catalog)
- **Categories**: Product types (HÖGTRYCKSSLANG, OLJESLANG, etc.)
- **Product Families**: Groups (KAPPAFLEX 1, HYDROSCAND T8081, etc.)
- **Products**: Individual SKUs with specifications (product_code, specifications JSON)
- **Product Knowledge**: Documentation, standards, assembly instructions
- **FTS5 Indexes**: Full-text search on families and knowledge

**Key Data Type**: `specifications` is JSON
```json
{
  "Artikelnr.": "4200-11-03",
  "Används med": "EN1SN, 2SC",
  "Slang ID": "3/16\"",
  // ... other fields
}
```

### 2. **agentic.db** (Workflow Tracking)
- **GoalInSession**: User queries
- **StrategyInSession**: Selected reasoning approaches
- **FunctionInSession**: Individual function executions
- **FunctionParametersInSession**: Inputs
- **FunctionOutputInSession**: Outputs
- **Libraries**: Template definitions for reuse

### 3. **temp.db** (Session Isolation)
- Temporary staging for multi-step reasoning
- Isolated per-query assembly of product data
- Prevents main database mutations
- Used by `func_assemble_table` and `func_analyze_with_llm`

---

## Existing Function Inventory (Generic & Reusable)

### **Extraction Functions**
- `func_extract_product_number()` - Extract product codes from user query
- `func_normalize_product_number()` - Standardize product code format
- `func_suggest_keywords()` - Generate search keywords from user intent

### **Search & Query Functions**
- `func_search_products()` - Multi-criteria product search (category, keywords, specs)
- `func_query_database()` - SQL Agent for custom queries (joins, filters, aggregations)
- `func_semantic_search()` - Natural language semantic search

### **Data Processing Functions**
- `func_table_search()` - Search tables by keywords
- `func_filter_table()` - Remove irrelevant rows
- `func_filter_items()` - Generic list filtering with conditions
- `func_assemble_table()` - Merge and structure data

### **Analysis Functions**
- `func_analyze_data()` - LLM-powered data synthesis
- `func_compare_items()` - Compare products side-by-side
- `func_calculate()` - Technical calculations (flow, pressure, etc.)

### **Visual Functions**
- `func_generate_visual_layout()` - Locate and display product images
- `func_display_images()` - Show images in editor

---

## Test Query Classification & Strategy Mapping

### **Category A: Direct Specification Lookup** (Single-attribute product queries)
**Examples**:
- "What is the Slang ID for product 4221-24-08?"
- "What is the maximum temperature for hose 1071-00-16?"
- "Which socket fits 1118-12-16?"

**Characteristics**:
- Query targets ONE specific product code → ONE specific attribute
- Answer is in `specifications` JSON or product metadata
- No multi-step reasoning needed

**Proposed Strategy: `DIRECT_SPEC_LOOKUP`**
```
Plan: 
  1. Extract Product Number (from query)
  2. Query Database (direct SELECT on product code)
  3. Extract Attributes (parse specifications JSON)
  4. Analyze with LLM (synthesize answer)
```

**Function Sequence**:
```
func_extract_product_number
  → Keyword Output: "4221-24-08"
  
func_query_database (custom SQL)
  SELECT * FROM products WHERE product_code = '4221-24-08'
  → results: [{product_code, specifications, ...}]
  
func_analyze_data / Extract Attributes
  → Parse JSON, extract "Slang ID" field
  → "3/16\""
```

**Expected Questions This Handles**: 5, 63, 64, 20 (partial)

---

### **Category B: Family-Based Comparison & Recommendations** (Multi-product, specification-driven)
**Examples**:
- "What hoses can be used for boiling water?" (needs filtering by temp spec)
- "Which hydraulic hoses are rated for more than 300 bar?" (pressure filter)
- "Do you have a product that can withstand both high pressure and vibrations?"

**Characteristics**:
- Query specifies ONE or MORE filtering criteria (temperature, pressure, etc.)
- Need to search across product families for matches
- Answer is a curated LIST of products (not a single attribute)

**Proposed Strategy: `SPEC_BASED_SEARCH`**
```
Plan:
  1. Suggest Keywords (extract filtering criteria from query)
  2. Search Products (find matching family/products by criteria)
  3. Filter Items (further narrow by specifications)
  4. Compare Items (optional: show comparison)
  5. Analyze with LLM (synthesize recommendations)
```

**Function Sequence**:
```
func_suggest_keywords (extract "boiling water", "high temp")
  → Keywords: "temperature", "heat resistant", "150C"
  
func_search_products (category="hoses", keywords=extracted)
  → families: [STAINLESS_STEEL_HOSE, ...]
  → products: [products matching family]
  
func_filter_items (specs.max_temp >= 150)
  → filtered_products: [...suitable hoses...]
  
func_analyze_data (synthesize with LLM)
  → "For boiling water, choose hoses with ... Recommend products: ..."
```

**Expected Questions This Handles**: 7, 11, 19, 21, 22, 34, 45, 47

---

### **Category C: Standards & Compliance** (Standards-driven queries)
**Examples**:
- "Do you have hoses that meet the EN 857 standard?"
- "What are the standards for hydraulic hose?"
- "Which products are approved for food use?"

**Characteristics**:
- Query targets compliance/certification attributes
- Answer is filtered list of products matching standards
- May require cross-referencing product_knowledge table

**Proposed Strategy: `STANDARD_COMPLIANCE`**
```
Plan:
  1. Suggest Keywords (extract standard name: "EN 857", "FDA", etc.)
  2. Query Database (search product_knowledge for standard info)
  3. Search Products (find products matching standard)
  4. Filter Items (by standard attribute in specifications)
  5. Analyze with LLM (explain compliance)
```

**Expected Questions This Handles**: 17, 11 (FDA), 46, 71

---

### **Category D: Technical Calculations** (Math/dimensioning queries)
**Examples**:
- "The flow is 150 liters per minute, what hose dimension should I choose?"
- "The flow is 20 liters per minute, what hose dimension for suction/return?"
- "Flow is 100 l/min with max 200 mbar drop, what hose dimension?"

**Characteristics**:
- Query provides technical parameters (flow, pressure, etc.)
- Answer requires hydraulic calculations
- May need to search products for matching dimensions

**Proposed Strategy: `TECHNICAL_CALCULATION`**
```
Plan:
  1. Extract Product Number (if specific product given)
  2. Suggest Keywords (extract numerical parameters: flow, pressure, etc.)
  3. Calculate (perform hydraulic calculations)
  4. Search Products (find hose sizes matching calculated dimension)
  5. Analyze with LLM (provide recommendation with reasoning)
```

**Expected Questions This Handles**: 47, 48, 49

---

### **Category E: Combination Queries** (Multi-step, context-dependent)
**Examples**:
- "Compare products 1059-0101 and 1059-0401" (needs comparison)
- "Which hydraulic hose and sleeve should I get for excavator?" (context + recommendation)

**Characteristics**:
- Query involves MULTIPLE products and MULTIPLE attributes
- Needs side-by-side comparison or synthesis
- May require product family lookups + product recommendations

**Proposed Strategy: `COMPARATIVE_ANALYSIS`**
```
Plan:
  1. Extract Product Number (all products mentioned: "1059-0101", "1059-0401")
  2. Query Database (load full specs for each product)
  3. Compare Items (side-by-side attribute comparison)
  4. Assemble Product Data (stage data in temp.db for large comparisons)
  5. Analyze with LLM (synthesize comparison, provide recommendation)
```

**Expected Questions This Handles**: 6, 9, 12, 16, 26, 27, 51, 65, 66, 67, 73

---

### **Category F: Knowledge-Based / Semantic Queries** (Free-form, context-rich)
**Examples**:
- "What is ISO bar?" (conceptual/definitional)
- "What hoses can be used for chemicals?" (knowledge + product matching)
- "Which products are approved for food use?" (knowledge + compliance)

**Characteristics**:
- Query may reference concepts, standards, or domain knowledge
- Answer combines product data + documentation
- Often requires semantic search on product_knowledge table

**Proposed Strategy: `SEMANTIC_KNOWLEDGE_SEARCH`**
```
Plan:
  1. Suggest Keywords (extract domain concepts)
  2. Semantic Search (on product_knowledge table + product specs)
  3. Search Products (find products matching semantic results)
  4. Filter Items (by relevance/category)
  5. Assemble Product Data (stage in temp.db if large result set)
  6. Analyze with LLM (synthesize with context)
```

**Expected Questions This Handles**: 21, 22, 37, 38, 39, 44, 45, 52, 53, 70, 71

---

## Proposed Strategy Library

### Strategy Definitions (to populate StrategyLibrary)

| Strategy Name | Target | Description | Plan Steps | Query Category |
|---|---|---|---|---|
| **DIRECT_SPEC_LOOKUP** | lookup | Direct product spec retrieval for single product, single attribute | Extract Product Number → Query Database → Extract Attributes → Analyze with LLM | A |
| **SPEC_BASED_SEARCH** | search | Filter products by technical specifications (temp, pressure, etc.) | Suggest Keywords → Search Products → Filter Items → Analyze with LLM | B |
| **STANDARD_COMPLIANCE** | compliance | Find products matching standards/certifications | Suggest Keywords → Query Database (knowledge) → Search Products → Filter Items → Analyze with LLM | C |
| **TECHNICAL_CALCULATION** | calculate | Perform hydraulic calculations and find matching products | Suggest Keywords → Calculate → Search Products → Analyze with LLM | D |
| **COMPARATIVE_ANALYSIS** | compare | Compare multiple products side-by-side | Extract Product Number → Query Database → Compare Items → Analyze with LLM | E |
| **SEMANTIC_KNOWLEDGE_SEARCH** | knowledge | Search domain knowledge + products using semantic matching | Suggest Keywords → Semantic Search → Search Products → Analyze with LLM | F |

---

## Function Mapping to Strategies

### Reusable Function Sequence Patterns

**Pattern 1: Single Product Direct Lookup**
```
func_extract_product_number
├─→ func_query_database (WHERE product_code = ?)
├─→ func_analyze_data (parse JSON specs)
└─→ func_analyze_data (LLM synthesis)
```
**Used by**: DIRECT_SPEC_LOOKUP

**Pattern 2: Multi-Product Search**
```
func_suggest_keywords
├─→ func_search_products (with keywords & filters)
├─→ func_filter_items (further filtering)
└─→ func_analyze_data (LLM synthesis)
```
**Used by**: SPEC_BASED_SEARCH, STANDARD_COMPLIANCE, SEMANTIC_KNOWLEDGE_SEARCH

**Pattern 3: Calculation-Based**
```
func_suggest_keywords (extract parameters)
├─→ func_calculate (perform calc)
├─→ func_search_products (find matching products)
└─→ func_analyze_data (recommend)
```
**Used by**: TECHNICAL_CALCULATION

**Pattern 4: Comparison-Based**
```
func_extract_product_number (all products)
├─→ func_query_database (load all)
├─→ func_compare_items (side-by-side)
└─→ func_analyze_data (synthesis)
```
**Used by**: COMPARATIVE_ANALYSIS

**Pattern 5: Knowledge-Enriched**
```
func_suggest_keywords
├─→ func_semantic_search (on product_knowledge)
├─→ func_search_products (find products)
├─→ func_assemble_product_data (stage in temp.db if large)
└─→ func_analyze_data (LLM synthesis with context)
```
**Used by**: SEMANTIC_KNOWLEDGE_SEARCH

---

## Implementation Roadmap

### Phase 1: Core Strategies (Quick Wins)
1. **DIRECT_SPEC_LOOKUP** - Simplest, handles Category A (5 questions immediately)
2. **SPEC_BASED_SEARCH** - Moderately complex, handles Category B (7+ questions)

### Phase 2: Advanced Strategies
3. **STANDARD_COMPLIANCE** - Reuses SPEC_BASED_SEARCH logic + knowledge queries
4. **COMPARATIVE_ANALYSIS** - Reuses core search + compare functions

### Phase 3: Intelligence Layer
5. **SEMANTIC_KNOWLEDGE_SEARCH** - Enriched with semantic search capability
6. **TECHNICAL_CALCULATION** - Domain-specific math + search

### Phase 4: Orchestration (Optional)
- **Hybrid strategies** that combine multiple approaches
- **Fallback strategies** when primary strategy fails
- **Context preservation** across multi-turn queries

---

## Key Design Principles

1. **Generic, Reusable Functions**: Functions don't know about strategies; strategies orchestrate them
2. **Composable Patterns**: Function sequences are combinable into new strategies
3. **Temp DB for Scale**: Use temp.db for large result sets (> 50 products)
4. **LLM as Synthesizer**: LLM only synthesizes at the END, not in every function
5. **Database-Centric**: Push as much work to SQL as possible (filtering, joining, aggregating)
6. **Stateless Functions**: Each function works independently; state lives in agentic.db

---

## Next Steps

1. ✅ Identify test questions by category (done - see test_questions_categorized.txt)
2. **→ Implement DIRECT_SPEC_LOOKUP** (handles 5 questions immediately)
3. **→ Implement SPEC_BASED_SEARCH** (covers most "what products..." questions)
4. **→ Test with test suite** (validate 10+ questions)
5. **→ Implement remaining strategies incrementally**

---

## Questions for You

1. **Query intent classification**: Should we auto-detect strategy from query, or provide a menu?
2. **Fallback behavior**: If primary strategy fails, should we retry with different strategy?
3. **Temp DB thresholds**: At what result set size should we use temp.db (50 products? 100?)?
4. **Caching**: Should we cache products/families in temp.db for session reuse?
5. **LLM role**: Should LLM only synthesize at end, or help with intermediate steps?

---
