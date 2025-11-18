# CONTEXTUAL PRODUCT SEARCH - Final Design Decisions ✅

**Status: APPROVED FOR IMPLEMENTATION**  
**Date: 2025-11-18**  
**Architecture: Extract Requirements → Semantic Search → Filter Items → Analyze With LLM**

---

## Decision Summary

### ✅ DECISION POINT 1: Embedding Generation

**Selected: Batch Pre-Population via `logic/embeddings.py`**

```python
# Usage:
python Layer_2_Agentic/logic/embeddings.py --action populate --model multilingual-e5-base

# Process:
# 1. Load all 168 product families from harvested.db
# 2. Generate embeddings using sentence-transformers (multilingual-e5-base)
# 3. Load to Chroma DB (relocated to database/chroma.sqlite3)
# 4. Verify all 168 embeddings loaded and indexed
# 5. Cache ready for semantic search (< 100ms per query)
```

**Model Selection:**
- **Primary: `multilingual-e5-base`** (Ollama: `nomic-embed-text` or `qwen3-embedding`)
- Supports English + Swedish natively
- Higher accuracy than MiniLM (better for product matching)
- ~5-10 minutes for 168 families (acceptable for setup)

**Database Location Change:**
- **Old:** `vector_index/chroma.sqlite3`
- **New:** `database/chroma.sqlite3`
- Update all config references in `config.yaml`
- Centralized database folder structure

---

### ✅ DECISION POINT 2: Language Handling

**Selected: Semantic + LLM (No Multi-Layer Fallback)**

**Architecture:**

```
User Query (English)
       ↓
[Extract Requirements] → LLM parses intent
       ↓
[Semantic Search] → Query embeddings against Chroma
       ↓
Do scores > 0.70?
    /             \
  YES              NO
   |                |
Return Top 15   Return Lower Scores
Results         (with Suggestions)
   |                |
   └────────┬───────┘
            ↓
    [User Guidance]
    - Show all matches with confidence scores
    - Suggest related searches if scores low
    - Allow user to select from options
    - Guide search refinement
```

**Key Behaviors:**

1. **High Confidence (> 0.70):**
   - Return top 15 families directly
   - Present to Filter Items

2. **Low Confidence (0.50-0.70):**
   - Show matches to USER with confidence scores
   - Suggest similar searches (LLM-enhanced)
   - Allow user to confirm/refine query

3. **No Matches (< 0.50):**
   - Return helpful suggestions for search refinement
   - Ask user to select from suggested directions

**Suggested Searches Feature (MVP):**
```json
{
    "query": "boiling water hoses",
    "semantic_matches": [
        {"name": "KAPPAFLEX 1", "score": 0.82, "applications": "High temperature, low/medium pressure"},
        {"name": "THERMOSTAT", "score": 0.76, "applications": "Extreme temperature ranges"}
    ],
    "suggestions_if_low": [
        "High temperature hoses (> 100°C)",
        "Pressure-resistant flexible hoses",
        "Industrial cooling systems"
    ],
    "guidance": "Select a family above or refine your search"
}
```

---

### ✅ DECISION POINT 3: Similarity Threshold

**Selected: Start with 0.70, Plan for 0.80 Upgrade**

```yaml
# config.yaml - SEMANTIC_SEARCH:
similarity_threshold_primary: 0.70      # Current (balanced precision/recall)
similarity_threshold_strict: 0.80       # Future (high precision mode)
similarity_threshold_permissive: 0.50   # Emergency (cast wide net)
```

**Threshold Behavior:**
- **>= 0.70:** Direct to Filter Items (high confidence)
- **0.50-0.70:** Show to user with suggestions (medium confidence)
- **< 0.50:** Suggest search refinement (low confidence)

**Future Optimization:**
- Monitor user feedback
- If many rejections at 0.70 → consider 0.75
- If too many "no results" → allow user to lower to 0.65

---

### ✅ DECISION POINT 4: Fallback When No Semantic Matches

**Selected: User-Selectable Options with Guidance**

**Flow:**

```
Semantic search returns 0-2 matches (score 0.50-0.70)
       ↓
Present to USER as:
{
    "confidence": "MEDIUM",
    "matches": [
        {id: 5, name: "KAPPAFLEX 1", score: 0.68, reason: "..."},
    ],
    "options": [
        "Continue with this match (medium confidence)",
        "Refine search: Try 'specific temperature range'",
        "Browse all families by category",
        "Contact support"
    ]
}
       ↓
User Selects Action
    /    |    \
   A     B     C
```

**No Hard Fallback** - User controls the next step:
- ✅ Can proceed with lower-confidence match
- ✅ Can refine query with guidance
- ✅ Can browse alternatives
- ✅ Preserves user intent

---

### ✅ DECISION POINT 5: Product Limiting for LLM

**Selected: 20-25 Products (Standard)**

```python
# In Filter Items function:
SAFE_LLM_PRODUCT_COUNT = 25  # Never exceed

def filter_items_for_llm(candidates):
    """Limit products to safe LLM context window"""
    sorted_candidates = sort_by_composite_score(candidates)
    # Composite: 0.7 * semantic_score + 0.3 * attribute_match
    
    limited = sorted_candidates[:SAFE_LLM_PRODUCT_COUNT]
    
    return {
        "products": limited,
        "total_candidates": len(candidates),
        "limited_to": SAFE_LLM_PRODUCT_COUNT,
        "ranking_reason": "Composite score (70% semantic + 30% attribute match)"
    }
```

**Safety Margin:** 25 products * 500 chars = 12,500 chars (leaving 19,500+ chars buffer)

---

### ✅ DECISION POINT 6: Result Ranking

**Selected: Composite Score (70% Semantic + 30% Attribute)**

```python
def composite_rank_score(product, semantic_similarity, requirements):
    """
    Balances semantic relevance with practical fit
    """
    # Count how many extracted requirements this product satisfies
    attribute_matches = count_matching_attributes(product, requirements)
    attribute_ratio = attribute_matches / len(requirements) if requirements else 0.5
    
    # Weighted composite
    composite = (0.7 * semantic_similarity) + (0.3 * attribute_ratio)
    
    return {
        "product_id": product['id'],
        "composite_score": composite,
        "semantic_score": semantic_similarity,
        "attribute_match_ratio": attribute_ratio,
        "ranking_reason": f"Matched {attribute_matches}/{len(requirements)} requirements"
    }
```

**Ranking Example:**
```
Query: "High temperature, high pressure hose"
Requirements: [temp > 100°C, pressure > 200 MPa]

Product A:
- Semantic similarity: 0.85 (very relevant)
- Attribute matches: 2/2 (100%)
- Composite: 0.7*0.85 + 0.3*1.0 = 0.845 → RANK 1

Product B:
- Semantic similarity: 0.82
- Attribute matches: 1/2 (50%)
- Composite: 0.7*0.82 + 0.3*0.5 = 0.724 → RANK 2
```

---

### ✅ DECISION POINT 7: Error Handling - No Results

**Selected: Option B - Suggest Similar Searches**

```json
{
    "status": "no_results",
    "query": "spacecraft pressure systems",
    "message": "No hoses found matching 'spacecraft pressure systems'. This application is not in our database.",
    
    "suggestions": [
        "Try searching for: 'high pressure industrial hoses' (we have up to 600 MPa)",
        "Try searching for: 'extreme temperature hoses' (we have up to 350°C)",
        "Browse: All families by temperature range",
        "Browse: All families by pressure range"
    ],
    
    "database_capabilities": {
        "pressure_range": "0.1 - 600 MPa",
        "temperature_range": "-40°C to +350°C",
        "total_families": 168,
        "total_products": 1628
    },
    
    "support": "Unable to find what you need? Contact support@hydroscand.se"
}
```

**LLM-Enhanced Suggestions:**
- Use LLM to suggest semantically related alternatives
- Show database capability boundaries
- Guide user to refine query appropriately

---

### ✅ DECISION POINT 8: Logging & Debugging

**Selected: Detailed Logging with Debug Level Control**

**Config (config.yaml):**
```yaml
CONTEXTUAL_SEARCH_LOGGING:
  debug_level: 2  # 0=SILENT, 1=ERRORS, 2=INFO, 3=DEBUG, 4=VERBOSE
  
  log_components:
    extract_requirements: true
    semantic_search: true
    filter_items: true
    analyze_with_llm: true
    
  detailed_logs:
    query_processing: true          # Log query parsing steps
    semantic_scores: true           # Log top-5 match scores
    fallback_usage: true            # Log when fallbacks triggered
    llm_calls: true                 # Log LLM prompts & responses
    cache_hits: true                # Log Chroma cache effectiveness
    final_rankings: true            # Log composite score calculations
    
  log_file: "Layer_2_Agentic/config/logs/contextual_search.log"
```

**Log Output Example:**
```
[DEBUG] Query: "boiling water hoses"
[DEBUG]   → Extract Requirements: {temp: [80-120], pressure: [10-50], application: "thermal"}
[DEBUG]   → Semantic Search: Top 5 matches:
[DEBUG]     1. KAPPAFLEX 1 (0.89)
[DEBUG]     2. THERMOSTAT (0.84)
[DEBUG]     3. HYDRO-FLEX (0.78)
[DEBUG]     4. PRESSURE-PRO (0.72)
[DEBUG]     5. STANDARD (0.68)
[DEBUG]   → Matches > 0.70: 4 families
[DEBUG]   → Filter Items: Applying multi-criteria filter...
[DEBUG]   → Final 20 products ranked by composite score (0.7*semantic + 0.3*attr)
[DEBUG]   → LLM Analysis: Processing 20 products for recommendations
[DEBUG]   → Cache hit: Product family KAPPAFLEX_1 analyzed 3x this session
```

---

### ✅ Additional Decisions

#### Embedding Model Choice

**Selected: `multilingual-e5-base`**

| Model | Pros | Cons | Selection |
|-------|------|------|-----------|
| multilingual-e5-base | High accuracy, Swedish+English, optimized | Slower (10 min) | ✅ PRIMARY |
| nomic-embed-text | Fast, good accuracy | Lower precision | Alt via Ollama |
| qwen3-embedding | High accuracy, multilingual | Resource heavy | Alt via Ollama |
| multilingual-MiniLM-L6-v2 | Very fast | Lower accuracy | Fallback only |

**Implementation:**
```python
# Try in order:
1. Use sentence-transformers.multilingual-e5-base (if available)
2. Fall back to Ollama: nomic-embed-text
3. Fall back to Ollama: qwen3-embedding
4. Emergency: multilingual-MiniLM-L6-v2
```

---

#### LLM Temperature Setting

**Selected: 0.3 (Slightly Creative, Consistent)**

```yaml
# config.yaml - LLM_SETTINGS:
analysis_temperature: 0.3

Reasoning:
- 0.0 = Deterministic (too rigid, boring recommendations)
- 0.3 = Balanced (consistent + some variation)
- 0.7 = Creative (too random for product analysis)
```

**Usage:**
```python
# In analyze_with_llm():
response = llm.invoke(
    prompt=analysis_prompt,
    temperature=0.3,
    max_tokens=1024
)
```

---

#### Caching Strategy

**Selected: Product Family-Level Caching in Chroma**

```python
# Cache Structure in Chroma:
collection: "analysis_cache"

document: {
    "query_hash": md5(extracted_requirements),
    "cached_analysis": "LLM analysis result",
    "timestamp": epoch,
    "ttl": 86400  # 24 hours
}

metadata: {
    "query": original_query,
    "families_analyzed": [5, 12, 47],
    "accuracy": 0.92
}
```

**Benefits:**
- ⚡ If user asks similar query → instant cached result
- 📊 Track query patterns
- 🔒 Same Chroma DB handles both embeddings + cache
- 🧹 Auto-purge old cache (24h TTL)

**Implementation:**
```python
def analyze_with_cache(query, products):
    """Check Chroma for cached analysis of similar queries"""
    
    cache_key = hash_requirements(extract_requirements(query))
    
    # Look for cache hit
    cached = chroma.query(
        query_embeddings=[cache_key],
        collection="analysis_cache",
        where={"ttl": {">": time.time()}}
    )
    
    if cached:
        logger.debug(f"Cache hit for: {query}")
        return cached[0]
    
    # No cache: run full analysis
    analysis = analyze_with_llm(query, products)
    
    # Store for future use
    chroma.upsert(
        collection="analysis_cache",
        documents=[json.dumps(analysis)],
        metadatas=[{"query": query, "timestamp": time.time()}],
        ids=[cache_key]
    )
    
    return analysis
```

---

## Implementation Checklist

### Phase 1: Infrastructure (Day 1)

- [ ] Create `Layer_2_Agentic/logic/embeddings.py` (batch generation script)
- [ ] Move `vector_index/chroma.sqlite3` → `database/chroma.sqlite3`
- [ ] Update all config references to new Chroma path
- [ ] Update `config.yaml` with all CONTEXTUAL_SEARCH settings
- [ ] Run embedding population: `python Layer_2_Agentic/logic/embeddings.py --action populate`
- [ ] Verify 168 embeddings loaded in Chroma

### Phase 2: Core Functions (Day 2-3)

- [ ] Implement `extract_requirements()` - LLM-based intent parsing
- [ ] Implement `semantic_search()` - Chroma query + user guidance
- [ ] Implement `filter_items()` - Multi-criteria filter + composite ranking
- [ ] Enhance `analyze_with_llm()` - Multi-product analysis + caching
- [ ] Implement cache layer in Chroma

### Phase 3: Integration & Testing (Day 4)

- [ ] Integrate all 5 functions into strategy workflow
- [ ] Test with 11 refined questions
- [ ] Validate context window limits (no overflow)
- [ ] Test user guidance quality
- [ ] Performance benchmarking

### Phase 4: Documentation & Deployment

- [ ] Create `CONTEXTUAL_SEARCH_IMPLEMENTATION.md`
- [ ] Document embedding setup steps
- [ ] Create troubleshooting guide
- [ ] Add example queries with expected outputs
- [ ] Deploy with confidence

---

## Key Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `Layer_2_Agentic/logic/embeddings.py` | CREATE | Embedding generation & Chroma management |
| `database/chroma.sqlite3` | MOVE | Vector DB (from vector_index/) |
| `config.yaml` | UPDATE | Add CONTEXTUAL_SEARCH settings + logging |
| `Layer_2_Agentic/logic/function_library.py` | UPDATE | Implement 5 core functions |
| `Layer_2_Agentic/db/templates.py` | UPDATE | Verify 5 templates are correct |
| `tests/functional/test_contextual_search.py` | CREATE | Test all 11 questions |

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Embeddings not populated | 🔴 CRITICAL | Run verify script, manual check in Chroma |
| LLM context overflow | 🔴 CRITICAL | Strict 25-product limit + buffer testing |
| Language mismatch | 🟡 HIGH | Semantic search bridges languages |
| Poor user guidance | 🟡 HIGH | Clear suggestions + reasoning in output |
| Cached stale results | 🟠 MEDIUM | 24h TTL + manual cache clearing |
| Embedding accuracy | 🟠 MEDIUM | Use multilingual-e5-base for best results |

---

## Success Criteria

✅ **System is ready for implementation when:**

1. All 8 design decisions documented and approved
2. Embedding model selected and tested
3. Chroma database moved to database/ folder
4. Config.yaml updated with all settings
5. No architectural blockers identified
6. Team alignment on user guidance approach

✅ **Implementation is complete when:**

1. All 5 core functions implemented and tested individually
2. Integration test passes on 11 refined questions
3. No LLM context overflow detected
4. User guidance tested with real queries
5. Performance meets target (< 5 sec per query)
6. Documentation complete and deployment-ready

---

**Status: ✅ READY FOR IMPLEMENTATION**

**Next Action: Create `Layer_2_Agentic/logic/embeddings.py` and begin Phase 1 infrastructure setup.**

