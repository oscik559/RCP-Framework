# CONTEXTUAL PRODUCT SEARCH - Pre-Implementation Brainstorm & Design Decisions

## Overview

Before we write a single line of code, we need to **lock in critical design decisions**. This document captures the key questions, explores tradeoffs, and proposes recommendations.

---

## DECISION POINT 1: Embedding Generation Timing

### The Question
**When should we generate and load embeddings into Chroma?**

### Option A: Batch Pre-Population (Recommended ✅)
```python
# ONCE at startup or via separate script:
python scripts/populate_embeddings.py
# Generates 168 embeddings in ~2 minutes
# All semantic searches are then instant (< 100ms)
```

**Pros:**
- ⚡ Fast semantic search (no delay on queries)
- 💾 Embeddings cached in Chroma for reuse
- 🔧 Easier to debug (separate process)
- 📊 Can batch-monitor embedding quality

**Cons:**
- ⏱️ 2-minute startup delay
- 📁 Takes disk space (~10MB for 168 embeddings)

### Option B: Lazy Generation (On-Demand)
```python
# First query triggers embedding generation:
def semantic_search(query):
    if not embeddings_loaded():
        generate_embeddings()  # 2-min delay first call only
    return search_embeddings(query)
```

**Pros:**
- ⚡ No startup delay
- 💰 Only generate if used
- 🚀 Deploy faster

**Cons:**
- 😫 First query slow (2 minutes to user)
- 🔄 Risk of timeout in web UI
- 🐞 Harder to debug production issues

### Option C: Hybrid (Smart Pre-Population)
```python
# At startup:
if not embeddings_loaded():
    start_background_embedding_job()
    # Meanwhile, fall back to FTS immediately
    return fts_search(query)
```

**Pros:**
- ⚡ UI responsive immediately
- ⏱️ Embeddings ready soon after
- 🔄 Graceful degradation

**Cons:**
- 🔧 More complex (async tasks)
- 🐞 Race conditions possible

### **RECOMMENDATION: Option A - Batch Pre-Population**

**Reasoning:**
- CONTEXTUAL SEARCH is new; users can wait 2 minutes for first startup
- Simpler, less error-prone
- Predictable performance after initial setup
- Can be documented in deployment guide

**Implementation Plan:**
1. Create `scripts/populate_embeddings.py` (50 lines)
2. Run once before deploying CONTEXTUAL SEARCH
3. Verify all 168 embeddings loaded (`SELECT COUNT(*) FROM embeddings`)
4. Document in deployment guide

---

## DECISION POINT 2: Language Handling Strategy

### The Question
**How should we handle Swedish product names vs English queries?**

### Example Scenario
```
User Query (English): "I need a hose for boiling water"
Database Content (Swedish): "Slang för låga och medelhöga tryck..."
Expected: KAPPAFLEX family should be found
Problem: Direct keyword match fails
```

### Option A: Vector Embeddings Only (Simple but Limited)
```python
# Rely entirely on semantic similarity
query_embedding = model.encode("boiling water hose")
family_embeddings = chroma.search(query_embedding, top_k=15)
# Returns families by semantic closeness, ignoring language
```

**Pros:**
- 🎯 Semantic similarity bridges language gap
- 🚀 Simplest implementation
- 📊 Multilingual model handles it

**Cons:**
- ⚠️ Fails if embeddings incomplete
- 🐛 No fallback for low-quality embeddings
- 🎮 Can't leverage existing FTS infrastructure

### Option B: Layer 1 Vector + Layer 2 FTS + Layer 3 LLM (Recommended ✅)
```python
def semantic_search_robust(query: str):
    # Layer 1: Vector search (fastest)
    results = chroma.search(encode(query), top_k=15)
    if results and best_score > 0.7:
        return results  # Good confidence
    
    # Layer 2: FTS search (Swedish keyword fallback)
    fts_results = fts_search(query)  # Searches Swedish text
    if fts_results:
        return fts_results
    
    # Layer 3: LLM-assisted (last resort)
    swedish_keywords = llm_expand_to_swedish(query)
    for kw in swedish_keywords:
        fts_results = fts_search(kw)
        if fts_results:
            return fts_results
    
    return []
```

**Pros:**
- 🔒 Multiple fallback layers (robust)
- ⚡ Fast path for good semantic matches
- 📚 Leverages FTS for keyword searches
- 🧠 LLM bridges language/intent gap

**Cons:**
- 🔧 More complex (4 functions)
- 🐢 Slower worst-case (LLM call)
- 🧪 More test cases needed

### Option C: Always Use LLM Translation (Simple but Slow)
```python
# Every query: English → Swedish → Search
swedish_keywords = llm_expand_to_swedish(query)
results = fts_search(swedish_keywords)
```

**Pros:**
- 🎯 Accurate intent translation
- 🔒 Works reliably

**Cons:**
- 🐢 Every query includes LLM call (~2-3 sec latency)
- 💰 Higher inference cost
- 🚀 Not scalable for many queries

### **RECOMMENDATION: Option B - Layered Approach**

**Reasoning:**
- Most English queries will match semantically (Layer 1 handles ~90%)
- Swedish FTS catches keyword-based queries (Layer 2 handles ~8%)
- LLM fallback for complex intent (Layer 3 handles ~2%)
- Speed: 90% of queries are sub-100ms

---

## DECISION POINT 3: Similarity Threshold for Semantic Search

### The Question
**At what vector similarity score should we accept a semantic match as valid?**

### Similarity Scores Explained
```
1.0 = Perfect duplicate
0.8-1.0 = Very close (synonyms, related terms)
0.6-0.8 = Related (somewhat similar)
0.4-0.6 = Tangentially related
0.0-0.4 = Unrelated
```

### Option A: Permissive (0.5+) - Get More Results
```python
results = chroma.search(query, where={"score": {"$gte": 0.5}})
# Returns ~20-40 families per query
```

**Pros:**
- 🎣 Casts wide net
- 📊 More options for user
- 🔄 Fewer "no results" scenarios

**Cons:**
- 🐮 Low-quality matches included
- 😕 Less relevant results
- 🧠 LLM gets noise to analyze

### Option B: Moderate (0.65-0.75) - Balanced (Recommended ✅)
```python
results = chroma.search(query, where={"score": {"$gte": 0.70}})
# Returns ~10-20 families per query
```

**Pros:**
- ⚖️ Balanced precision/recall
- 🎯 Mostly relevant results
- 📊 Fits LLM context window nicely

**Cons:**
- ❌ Some valid matches filtered out
- 🔄 More "no results" edge cases

### Option C: Strict (0.8+) - Only High-Confidence Matches
```python
results = chroma.search(query, where={"score": {"$gte": 0.80}})
# Returns ~3-10 families per query
```

**Pros:**
- 🎯 Only highly relevant results
- ✅ Very precise
- 🚀 Fastest LLM analysis

**Cons:**
- ❌ Miss valid matches
- 😞 Frequent "no results" for fuzzy queries

### **RECOMMENDATION: Option B - Threshold 0.70**

**Reasoning:**
- Semantic models typically reliable above 0.70
- Provides 10-20 results (good for LLM analysis)
- Fallback to FTS if < 0.70
- Can be tuned in `config.yaml` for testing

---

## DECISION POINT 4: Fallback Strategy When No Semantic Matches Found

### The Question
**What happens when semantic search returns 0 results or all scores < 0.70?**

### Option A: Strict Fallback - FTS Only
```python
def semantic_search(query):
    results = chroma.search(query, top_k=15)
    if best_score < 0.70:
        return []  # No match - fail gracefully
    return results
```

**Pros:**
- 🔒 High precision
- 🎯 No false positives

**Cons:**
- 😞 Frequent "no results" messages
- 😤 User frustration ("I know it exists")

### Option B: Automatic FTS Fallback (Recommended ✅)
```python
def semantic_search(query):
    results = chroma.search(query, top_k=15)
    if best_score < 0.70:
        # Fall back to full-text search
        return fts_search(query)  # Searches Swedish text
    return results
```

**Pros:**
- 🎣 More results for users
- 🔄 Graceful degradation
- 📚 Uses existing FTS infrastructure

**Cons:**
- ⚠️ Mixed precision (some low-relevance results)
- 🐢 Potentially slower (FTS full-table scan)

### Option C: Hierarchical Fallback with LLM Bridge (Best, but Complex)
```python
def semantic_search(query):
    # Layer 1: Vector similarity
    results = chroma.search(query, top_k=15)
    if results and best_score >= 0.70:
        return results
    
    # Layer 2: FTS keyword search
    fts_results = fts_search(query)
    if fts_results:
        return fts_results
    
    # Layer 3: LLM-powered intent expansion
    llm_keywords = llm_expand_search_terms(query)
    for keyword in llm_keywords:
        fts_results = fts_search(keyword)
        if fts_results:
            return fts_results
    
    return []  # Finally, no results
```

**Pros:**
- 🏅 Most robust (3-layer fallback)
- 📊 High success rate for diverse queries

**Cons:**
- 🔧 Complex implementation
- 🐢 Worst-case latency (LLM call)
- 🧪 Many edge cases to test

### **RECOMMENDATION: Option B - Automatic FTS Fallback**

**Reasoning:**
- Good balance of robustness and simplicity
- FTS is already configured and tested
- Can upgrade to Option C later if needed
- Avoids LLM latency for simple keyword queries

---

## DECISION POINT 5: Product Limiting Strategy for LLM Analysis

### The Question
**How many products should we send to LLM before hitting context limits?**

### The Math Reminder
```
LLM context: 8,192 tokens (~32,768 chars)
Safe overhead: 700 chars (system prompt + query)
Available for data: 32,068 chars

Per product spec size: ~500 chars average
Max safe products: 32,068 / 500 = 64 products
Recommended limit: 20-25 products (for margin)
```

### Option A: Conservative (15 products max)
```python
filtered = sort_by_relevance(candidates)[:15]
```

**Pros:**
- 🔒 Very safe (no risk of overflow)
- ⚡ Fast LLM response
- 🎯 Focused analysis

**Cons:**
- ❌ Might miss relevant products
- 😞 Limited options for user

### Option B: Moderate (20-25 products max) (Recommended ✅)
```python
max_products = min(len(candidates), 25)
filtered = sort_by_relevance(candidates)[:max_products]
```

**Pros:**
- ⚖️ Balanced (good options + safe)
- ✅ Room for safety margin
- 🎯 Diverse but focused results

**Cons:**
- ⚠️ Potential overflow with verbose specs

### Option C: Aggressive (50+ products)
```python
# Send all candidates to LLM
# Risk overflow for edge cases
```

**Pros:**
- 📊 Most product options

**Cons:**
- 🔴 Risk of context overflow
- 💥 LLM might truncate mid-response
- 😞 Unpredictable behavior

### **RECOMMENDATION: Option B - 20-25 Products Max**

**Reasoning:**
- Proven safe with llama3.2 (8K tokens)
- Good product variety without overwhelming user
- Room for safety margin
- Predictable performance

**Implementation:**
```python
# In Filter Items function:
SAFE_LLM_PRODUCT_COUNT = 25  # Config value

def filter_items_for_llm(candidates):
    sorted_candidates = sort_by_match_score(candidates)
    return sorted_candidates[:min(len(sorted_candidates), SAFE_LLM_PRODUCT_COUNT)]
```

---

## DECISION POINT 6: Result Ranking Strategy

### The Question
**How should we rank the 20-25 filtered products before sending to LLM?**

### Option A: Pure Similarity Score Ranking
```python
ranked = sorted(products, key=lambda p: p['semantic_similarity'], reverse=True)
# "Most similar to query" first
```

**Pros:**
- 🎯 Straightforward
- 📊 Objective metric

**Cons:**
- ⚠️ Doesn't consider attribute match quality
- 🎮 May miss best practical option

### Option B: Composite Score (Similarity + Attribute Match) (Recommended ✅)
```python
def composite_score(product, semantic_score, requirement_matches):
    """
    0.7 * semantic_similarity + 0.3 * attribute_match_ratio
    """
    return 0.7 * semantic_score + 0.3 * (requirement_matches / total_requirements)

ranked = sorted(products, key=composite_score, reverse=True)
```

**Pros:**
- ⚖️ Balances both similarity and practical fit
- 🎯 More relevant results
- 📊 Considers user requirements explicitly

**Cons:**
- 🔧 More complex (tuning weights)
- 🧪 More edge cases

### Option C: User-Requested Attribute Priority
```python
# If user asks specifically for "high temperature":
def prioritized_score(product):
    base = semantic_score(product)
    if product['max_temp'] > 100:  # High temp
        return base * 1.5  # 50% boost
    return base

ranked = sorted(products, key=prioritized_score, reverse=True)
```

**Pros:**
- 🎯 Directly addresses user needs

**Cons:**
- 🔧 Requires explicit requirement extraction
- 🧪 Complex logic per requirement

### **RECOMMENDATION: Option B - Composite Score**

**Reasoning:**
- Balances semantic relevance with practical fit
- Simple weighting (70/30) is interpretable
- Can be tuned if needed
- Provides better user results

---

## DECISION POINT 7: Error Handling - "No Results Found"

### The Question
**What should we tell users when no products match their query?**

### Option A: Simple "No Results"
```json
{
    "status": "no_results",
    "message": "No hoses found matching your query."
}
```

**Pros:**
- 🎯 Clear and simple

**Cons:**
- 😞 Not helpful
- 😤 User frustrated

### Option B: Suggest Similar Searches (Recommended ✅)
```json
{
    "status": "no_results",
    "message": "No hoses found matching 'spacecraft pressure systems'.",
    "suggestions": [
        "Try: 'high pressure hoses'",
        "Try: 'industrial systems'",
        "Browse: All product families by temperature range"
    ],
    "tip": "Our database includes applications up to 350°C and 600 MPa pressure."
}
```

**Pros:**
- 🎯 Helpful guidance
- 🚀 User can refine search
- 😊 Better UX

**Cons:**
- 🔧 Requires predefined suggestions

### Option C: Suggest Closest Matches (Even if Below Threshold)
```json
{
    "status": "no_perfect_match",
    "message": "No exact matches found, but these are close:",
    "results": [
        {"name": "KAPPAFLEX 1", "match_score": 0.62, "note": "Lower confidence match"},
        {"name": "HYPROTEC", "match_score": 0.58, "note": "May work for your needs"}
    ]
}
```

**Pros:**
- 🎯 User gets options even for edge cases

**Cons:**
- ⚠️ Could mislead (low-quality matches)
- 😕 Confusing UX (when is 0.62 good enough?)

### **RECOMMENDATION: Option B - Suggest Similar Searches**

**Reasoning:**
- Helpful and user-friendly
- Guides refinement without false matches
- Educates about database capabilities
- Reduces user frustration

---

## DECISION POINT 8: Logging & Debugging Strategy

### The Question
**How much detail should we log for debugging semantic search failures?**

### Option A: Minimal Logging
```python
logger.info(f"Search: '{query}' returned {len(results)} results")
```

**Pros:**
- 🚀 Fast
- 📊 Less disk space

**Cons:**
- 🐞 Hard to debug failures

### Option B: Detailed Logging (Recommended ✅)
```python
logger.debug(f"Semantic search for '{query}'")
logger.debug(f"  → Top 3 vector matches: {[(r['name'], r['score']) for r in results[:3]]}")
logger.debug(f"  → FTS fallback? {fallback_used}")
logger.debug(f"  → Final count: {len(results)}")
```

**Pros:**
- 🔧 Easy debugging
- 📊 Can analyze patterns

**Cons:**
- 📁 More disk space
- 🔍 Privacy/data exposure risk

### **RECOMMENDATION: Option B - Detailed Logging**

**Reasoning:**
- CONTEXTUAL SEARCH is new and complex
- Will help identify edge cases
- Can be toggled via `debug_level` config
- Essential for production troubleshooting

---

## Summary: Recommended Approach

| Decision | Recommendation | Rationale |
|----------|---|---|
| **Embedding Timing** | Batch pre-population | Fast, predictable, simpler |
| **Language Handling** | Layered (Vector → FTS → LLM) | Robust, covers edge cases |
| **Similarity Threshold** | 0.70 | Good balance of precision/recall |
| **Fallback Strategy** | Auto-FTS for low scores | Graceful degradation |
| **LLM Product Limit** | 20-25 products | Safe for context window |
| **Result Ranking** | Composite score (70% sim + 30% attr) | Practical + relevant |
| **No Results UX** | Suggest similar searches | Helpful, reduces frustration |
| **Logging** | Detailed (debug mode) | Easier troubleshooting |

---

## Next Steps

### Phase 1: Setup (Day 1)
1. ✅ Create `scripts/populate_embeddings.py`
2. ✅ Run embedding generation (2 minutes)
3. ✅ Verify all 168 embeddings in Chroma

### Phase 2: Implementation (Days 2-3)
1. ✅ Implement Extract Requirements function
2. ✅ Implement Semantic Search function (with 3-layer fallback)
3. ✅ Implement Filter Items function (with 25-product limit)
4. ✅ Implement Extract Attributes function
5. ✅ Enhance Analyze With LLM for multi-product scenarios

### Phase 3: Testing (Day 4)
1. ✅ Test all 11 refined questions
2. ✅ Edge case testing (no results, language barriers, large datasets)
3. ✅ Performance benchmarking
4. ✅ LLM output quality assessment

---

## Open Questions for Discussion

Before we proceed, consider:

1. **Embedding Model Choice**: Use `multilingual-MiniLM-L6-v2` (light, fast) or `multilingual-e5-base` (more accurate)?
   - Recommend: MiniLM for speed, can upgrade later

2. **LLM Temperature Setting**: Should analysis be deterministic (temperature=0) or creative (temperature=0.7)?
   - Recommend: 0.3 (slightly creative, but consistent)

3. **Caching Strategy**: Cache semantic search results for repeated queries?
   - Recommend: Yes, for common queries (product family-level caching)

4. **User Feedback Loop**: Should we log user satisfaction to improve rankings?
   - Recommend: Yes, track which products users clicked on

---

**Status: Ready for coding once decisions are approved.**

