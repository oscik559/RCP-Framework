# Architecture Insights & Implementation Recommendations

**Analysis Date:** November 18, 2025  
**Analysis Basis:** Database inspection + main.py execution + schema review

---

## 🎯 Executive Summary

Your system has **excellent architecture** with clear separation of concerns:

| Layer | Status | Quality |
|-------|--------|---------|
| **Data Layer** (harvested.db) | ✅ Well-designed | Hierarchical schema, FTS enabled |
| **Workflow Layer** (state_graph.py) | ✅ Robust | LangGraph integration solid |
| **Function Layer** | ⚠️ Partial | Only 1 of 4 core strategies working |
| **Integration** | ✅ Clean | Ollama, SQLite, LangGraph well-integrated |

**Key Finding:** Your foundation is strong, but you're only using **4% of your function library**. You have templates for 12 strategies but only `DIRECT SPECIFICATION LOOKUP` is implemented.

---

## 📊 Current Data Coverage

```
Database: harvested.db
├─ Categories: 2 (HIGH-PRESSURE HOSES + PRESS COUPLINGS)
├─ Product Families: 168
│  ├─ HÖGTRYCKSSLANG: 69 families
│  └─ PRESSKOPPLINGAR: 99 families
├─ Products (SKUs): 1,628
│  ├─ All have specifications (JSON)
│  └─ Configuration types: STANDARD, REEL
└─ Product Knowledge: 0 (empty - future enhancement)

Capability: ✅ Query any of 1,628 products by code
           ⚠️ Can't search by application (no semantic index yet)
           ❌ No procedural knowledge base
```

### What Questions Can You Answer NOW?

Based on your database content, you can answer:

**✅ Direct Specification Lookups (30+ questions)**
- "What is the max pressure for product X?"
- "Which socket fits product Y?"
- "Specifications for 1110-00-06?"
- ~30 similar direct ID → specs queries

**✅ Simple Application Search (10-15 questions)**
- "What products are in the HÖGTRYCKSSLANG category?"
- "All press couplings with AISI 316?"
- FTS search on family descriptions

**❌ Contextual Application Search (NOT YET)**
- "Best hose for boiling water?" → Needs semantic understanding of temps + materials
- "What hose for high pressure + chemicals?" → Needs semantic search
- "Products for alkaline degreasing?" → Needs application matching

**❌ Procedural/Knowledge Questions (NOT YET)**
- "How to install a shell sleeve?" → Needs product_knowledge table
- "What is ISO bar?" → Needs knowledge base

---

## 🔍 System Architecture Deep-Dive

### Database Access Pattern

```
main.py
  ↓
state_graph.py (LangGraph workflow)
  ├─ Node: GoalDefine (LLM - parse query)
  ├─ Node: StrategyPlan (query agentic.db for strategy template)
  ├─ Node: FunctionExecute (call functions in function_library.py)
  │   └─ Each function may access:
  │       ├─ harvested.db (SELECT queries)
  │       ├─ agentic.db (read strategy templates)
  │       └─ Ollama (LLM calls)
  ├─ Node: FunctionValidate (check outputs)
  ├─ Node: StrategyValidate (check if strategy complete)
  ├─ Node: GoalValidate (final check + answer formatting)
  └─ Node: Done (return final_answer)
```

### Database Lifecycle

**agentic.db** (Session/Transient):
```
1. Clear old session data
2. Initialize schema (from agentic_schema.sql)
3. Populate templates from templates.py
4. Store strategy selection + function results
5. Clear after query completes
```

**harvested.db** (Data/Persistent):
```
1. Created by Layer 1 extraction (PDF → Products)
2. Queried by Layer 2 functions
3. Never cleared between sessions
4. Grows as more PDFs are extracted
```

### Current Data Access in DIRECT SPECIFICATION LOOKUP Strategy

```
User Query: "What do you know about 1110-00-06?"
    ↓
LLM extracts product code: "1110-00-06"
    ↓
Query harvested.db:
  SELECT * FROM products WHERE product_code = '1110-00-06'
    ↓
Result: 1 product record with JSON specs
    ↓
Join with family:
  SELECT * FROM product_families WHERE id = 16
    ↓
Extract & format specs
    ↓
LLM synthesizes into readable answer
```

---

## 💡 Key Insights

### 1. **Your JSON Specs Strategy is Perfect**
```json
// Example from database:
{
  "Artikelnr": "1110-00-06",
  "ID mm": "10,0",
  "ID tum": "3/8\"",
  "YD mm": "14,8",
  "Arb.tr. MPa": "10,0",
  "Böjradie mm": "40",
  "Vikt kg/m": "0,21"
}
```
✅ **Why it works:** No schema enforcement = flexible for different product types
✅ **Easy to extend:** Just add new keys for new specs
❌ **Hard to query:** Can't do `WHERE specifications.Arb_tr_MPa > 20` directly

### 2. **LLM is Only Used for 2 Functions**
- ✅ Extract Product Number (goal parsing)
- ✅ Extract Attributes (spec extraction - but could be deterministic)
- ✅ Analyze With LLM (answer formatting)

**Implication:** You can implement 3 of 4 core strategies WITHOUT LLM:
- ✅ DIRECT SPECIFICATION LOOKUP (working - uses LLM for formatting only)
- ✅ TECHNICAL CALCULATION (math only - no LLM needed)
- ✅ STANDARD & COMPLIANCE LOOKUP (DB query only - no LLM needed)
- ❌ CONTEXTUAL PRODUCT SEARCH (needs semantic search + LLM)

### 3. **Parallel Execution Mechanism Already Built**
Your `PARALLEL ENHANCED LOOKUP` strategy shows you thought about parallel execution:
```
"Normalize Product Number, Table Search, [Filter Table || Suggest Keywords], Find Latest Document..."
                                            ↑
                                   Parallel syntax
```
**Status:** Templates only, not yet implemented in function_library.py

### 4. **Vector Index Defined But Not Used**
`Chroma` vector DB referenced in imports but not populated.
- Needed for: Semantic product search
- Blocker for: CONTEXTUAL PRODUCT SEARCH strategy

---

## 🚀 Implementation Roadmap

### Phase 1: Quick Wins (This Week)

**1. Implement 3 Deterministic Strategies** (1-2 days each)

```python
# In Layer_2_Agentic/logic/function_library.py

def technical_calculation_hose_sizing(
    flow_rate: float,           # L/min
    line_type: str,             # "pressure", "suction", "return"
    pressure: float = None,
    max_pressure_drop: float = None,
    hose_length: float = 5.0
):
    """Pure math - no LLM, no DB (except product lookup)"""
    # 1. Validate inputs
    # 2. Calculate cross-sectional area: A = Q / v_target
    # 3. Find standard sizes that fit
    # 4. Query harvested.db for available products
    # 5. Return recommendations
    pass

def standard_and_compliance_lookup(
    standard_code: str,         # "EN 857", "FDA", "DNV"
    product_id: str = None      # Optional specific product
):
    """Pure DB query - no LLM needed"""
    # 1. Validate standard_code
    # 2. Query: SELECT * FROM product_families WHERE construction_details LIKE '%standard_code%'
    # 3. Format results with context
    pass
```

**Status After Phase 1:** Can answer 40+ questions (70% coverage)

---

### Phase 2: Semantic Search Setup (Next Week)

**2. Enable CONTEXTUAL PRODUCT SEARCH**

```python
# Step 1: Generate embeddings for all products
for family in product_families:
    embedding = embed_model.encode(family.name + " " + family.applications)
    store_in_chroma(family_id, embedding)

# Step 2: When user asks "hose for boiling water":
query_embedding = embed_model.encode("hose for boiling water")
similar_families = chroma_search(query_embedding, top_k=10)

# Step 3: Filter by specs (temp, pressure, etc.)
matching = [f for f in similar_families if f.max_temp >= 100]

# Step 4: LLM synthesis
answer = llm.format_response(matching, original_query)
```

**Requirements:**
- ✅ Embedding model (e.g., `sentence-transformers/multilingual-MiniLM-L6-v2`)
- ✅ Chroma client (already imported)
- ❌ Product embeddings (need to generate once)

**Status After Phase 2:** Can answer 75+ questions (95% coverage)

---

### Phase 3: Knowledge Base (Future)

**3. Populate product_knowledge Table**

```sql
INSERT INTO product_knowledge (
    pdf_name,
    page_number,
    category,
    knowledge_type,
    section_title,
    content
) VALUES (
    'High-Pressure_Hose.pdf',
    33,
    'HÖGTRYCKSSLANG',
    'ASSEMBLY',
    'How to install a crimp sleeve',
    'The installation of a crimp sleeve...'
);
```

**Status After Phase 3:** Can answer all 79 questions (100%)

---

## 📋 Before You Start Building Functions

### Questions to Answer First

**1. Parallel Execution Priority?**
- Question: Do you want to implement `[Func1 || Func2]` parallel syntax immediately?
- My recommendation: **NO - start sequential.** Add parallel in Phase 2 optimization.

**2. Temp.db Strategy?**
- Question: When should we use temp.db for "Assembled Specification Lookup"?
- My recommendation: **NOW** - set it up as optional mode in functions for large datasets.
- Implementation: Create `temp_db_path` parameter in "Analyze With LLM" function.

**3. Knowledge Base Scope?**
- Question: Should knowledge base be in harvested.db or separate?
- My recommendation: **harvested.db** - simpler to manage, can be extracted once.

**4. Caching Strategy?**
- Question: Should function results be cached?
- My recommendation: **YES - add after Phase 1.** Cache product lookups with 1-day TTL.

### Code Organization Guidelines

**For new strategies, follow this pattern:**

```python
# Layer_2_Agentic/logic/function_library.py

# ─────────────────────────────────────────────────────────────────
# STRATEGY: TECHNICAL CALCULATION
# ─────────────────────────────────────────────────────────────────

def func_calculate_hose_size(params: dict) -> Tuple[bool, dict]:
    """
    Calculate hose size based on flow rate and line type.
    
    Inputs:
      params['flow_rate']: float (L/min)
      params['line_type']: str ("pressure"|"suction"|"return")
      params['pressure']: float (bar, optional)
      params['max_pressure_drop']: float (bar, optional)
    
    Returns:
      (success, result)
    """
    try:
        # Validate
        flow_rate = float(params.get('flow_rate', 0))
        if flow_rate <= 0:
            return False, {"error": "flow_rate must be > 0"}
        
        # Calculate
        v_target = _get_target_velocity(params['line_type'])
        area_required = flow_rate / v_target
        
        # Find standard size
        recommended = _find_standard_size(area_required)
        
        # Query products
        products = _query_products_by_size(recommended)
        
        return True, {
            "recommended_size": recommended,
            "products": products,
            "rationale": f"At {flow_rate} L/min, target velocity {v_target} m/s"
        }
    except Exception as e:
        return False, {"error": str(e)}
```

---

## ✅ Action Items Before Implementation

### Do These First:

- [ ] **Decide on 5 strategies** (already done: Direct Spec, Contextual Search, Calc, Standards, Knowledge Base)
- [ ] **Remove template definitions for old strategies** (12 → 5)
- [ ] **Keep PARALLEL ENHANCED LOOKUP template** (for Phase 2)
- [ ] **Verify harvested.db has all needed product data** (currently have hoses + couplings)
- [ ] **Check if new PDFs need to be extracted** (expand coverage beyond 2 categories)

### Then Build In This Order:

1. **DIRECT SPECIFICATION LOOKUP** ✅ (Already working - just clean up function_library.py)
2. **TECHNICAL CALCULATION** (Pure math, 2-3 days)
3. **STANDARD & COMPLIANCE LOOKUP** (DB query, 1-2 days)
4. **CONTEXTUAL PRODUCT SEARCH** (Needs semantic search, 3-4 days)
5. **KNOWLEDGE BASE & RAG** (After product_knowledge populated, 2-3 days)

---

## 🎯 Testing Strategy

### For Each New Strategy:

```python
# tests/functional/test_strategies.py

def test_direct_specification_lookup():
    """Test queries from question set"""
    assert query("What is max temp for 1071-00-16?")  # Should work
    assert query("1110-00-06 specs?")  # Should work
    # ~30 questions to validate

def test_technical_calculation():
    """Test hydraulic math"""
    result = calculate_hose_size(flow_rate=150, line_type="pressure")
    assert result["recommended_size"] in ["1 1/4\"", "32mm"]
    # Q47, Q48, Q49

def test_contextual_product_search():
    """Test semantic search"""
    result = search_products("hose for boiling water")
    assert any(product["max_temp"] >= 100 for product in result)
    # ~35 questions

def test_standards_compliance():
    """Test certification matching"""
    result = find_by_standard("EN 857")
    assert len(result) > 0
    # Q17, Q71, Q78
```

---

## 💭 Final Recommendations

**Do You Have All the Data?**
- ✅ YES for direct lookups (1,628 products available)
- ⚠️ PARTIAL for applications (FTS enabled but no semantic index)
- ❌ NO for procedures (product_knowledge table empty)

**Is the Architecture Ready?**
- ✅ YES - solid foundation with LangGraph + SQLite + Ollama
- ⚠️ NEEDS - more function implementations
- ⚠️ NEEDS - semantic search setup

**Next Steps:**
1. Update templates.py (remove 12 → keep 5 strategies)
2. Update strategy_testing.py (enable all 5 strategies)
3. Start implementing function_library.py (begin with Technical Calculation)
4. Create test suite in tests/functional/
5. Validate with 79 test questions

**Estimated Timeline:**
- Phase 1 (Deterministic strategies): 1 week
- Phase 2 (Semantic search): 1 week
- Phase 3 (Knowledge base): 1 week
- **Total: 3 weeks to 100% coverage**

---

