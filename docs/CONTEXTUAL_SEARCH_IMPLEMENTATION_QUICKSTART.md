# CONTEXTUAL PRODUCT SEARCH - Implementation Quick Start

**Status: Ready to Build**  
**Start Date: 2025-11-18**  
**Phase: 1 - Infrastructure Setup**

---

## Overview

This guide walks through the implementation of CONTEXTUAL PRODUCT SEARCH strategy in 3 phases.

**Architecture:**
```
Extract Requirements (LLM)
    ↓
Semantic Search (Chroma embeddings)
    ↓
Filter Items (Multi-criteria ranking)
    ↓
Analyze With LLM (Product synthesis)
    ↓
Result with Guidance
```

---

## Phase 1: Infrastructure Setup (Today)

### Step 1.1: Create `embeddings.py` ✅

**Status:** Script created at `Layer_2_Agentic_Reasoning/logic/embeddings.py`

**What it does:**
- Loads all 168 product families from `harvested.db`
- Generates embeddings using multilingual-e5-base (or Ollama alternative)
- Loads embeddings to Chroma (now at `database/chroma.sqlite3`)
- Verifies all embeddings are queryable

### Step 1.2: Run Embedding Population

**Prerequisites:**
```powershell
# Start Ollama service (in separate terminal if not already running)
ollama serve

# Pull the qwen3-embedding model (in another terminal)
ollama pull qwen3-embedding:8b

# Verify model is available
ollama list

# Install Python dependencies
pip install chromadb
```

**Command:**
```powershell
# From project root:
cd c:\Users\oscik35\Desktop\PROJECTS\Hydroscand_Produktbok

# Run embedding population (uses qwen3-embedding:8b by default, takes ~2-5 minutes)
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action populate

# OR explicitly specify the model:
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action populate --model qwen3-embedding:8b

# With debug logging:
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action populate --debug
```

**Expected Output:**
```
[INFO] ======================================================================
[INFO] EMBEDDING POPULATION WORKFLOW
[INFO] ======================================================================
[INFO] Loading multilingual-e5-base from sentence-transformers...
[INFO] ✅ Model loaded: multilingual-e5-base
[INFO] Initializing Chroma at: .../database/chroma.sqlite3
[INFO] ✅ Chroma initialized with collection 'product_families'
[INFO] ✅ Loaded 168 families from harvested.db
[INFO] Generating embeddings for 168 families...
[INFO]   20/168 embeddings generated (2.5/sec)
[INFO]   40/168 embeddings generated (2.5/sec)
[INFO]   ...
[INFO] ✅ Generated 168 embeddings in 67.3s
[INFO] Loading 168 embeddings to Chroma...
[INFO]   Loaded batch 1/2
[INFO]   Loaded batch 2/2
[INFO] ✅ Successfully loaded 168 embeddings to Chroma
[INFO] Verifying embeddings in Chroma...
[INFO]   Embeddings in collection: 168
[INFO]   Testing semantic search...
[INFO] ✅ Semantic search working! Found 3 results
[INFO] ======================================================================
[INFO] ✅ EMBEDDING POPULATION COMPLETE
[INFO] ======================================================================
```

### Step 1.3: Verify Embeddings

**Command:**
```powershell
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action verify
```

**Expected:**
```
[INFO] Verifying embeddings in Chroma...
[INFO]   Embeddings in collection: 168
[INFO]   Testing semantic search...
[INFO] ✅ Semantic search working! Found 3 results
[INFO]   Top result: Family 5 (distance: 0.123)
```

### Step 1.4: Update Config

**File:** `Layer_2_Agentic_Reasoning/config/config.yaml`

**Add this section:**
```yaml
CONTEXTUAL_SEARCH:
  enabled: true
  
  # Semantic search settings
  embedding_model: "multilingual-e5-base"  # or: nomic-embed-text, qwen3-embedding
  chroma_path: "database/chroma.sqlite3"  # Moved from vector_index/
  
  # Similarity thresholds
  similarity_threshold_primary: 0.70      # High confidence
  similarity_threshold_secondary: 0.50    # Show to user
  similarity_top_k: 15                    # Return top 15 families
  
  # LLM settings
  analysis_temperature: 0.3
  analysis_model: "llama3.2"
  max_products_for_llm: 25                # Safety limit
  
  # Composite ranking
  ranking_weights:
    semantic_similarity: 0.70
    attribute_match: 0.30
  
  # Caching
  cache_enabled: true
  cache_ttl_hours: 24
  
  # Logging
  logging:
    debug_level: 2  # 0=SILENT, 1=ERRORS, 2=INFO, 3=DEBUG, 4=VERBOSE
    detailed_logs:
      extract_requirements: true
      semantic_search: true
      filter_items: true
      analyze_with_llm: true
      cache_hits: true
      rankings: true
    log_file: "Layer_2_Agentic_Reasoning/config/logs/contextual_search.log"
```

**Verify update:**
```powershell
# Check config loads correctly
python -c "from Layer_2_Agentic_Reasoning.config.config_loader import load_config; cfg = load_config(); print(cfg.get('CONTEXTUAL_SEARCH'))"
```

---

## Phase 2: Core Function Implementation (Days 2-3)

### Architecture

**5 core functions to implement:**

```
1. extract_requirements(query: str) → requirements: Dict
   Purpose: Parse user query into structured requirements
   Output: {keywords, temp_range, pressure_range, application, confidence}
   Implementation: LLM-based, single call, temp=0.3

2. semantic_search(query: str, requirements: Dict) → results: List
   Purpose: Find matching families via embeddings
   Output: {families, scores, suggestions, guidance}
   Implementation: Chroma query + fallback suggestions

3. filter_items(families: List, requirements: Dict) → filtered: List
   Purpose: Multi-criteria filtering + ranking
   Output: Max 25 products, ranked by composite score
   Implementation: Criteria matching + composite scoring (0.7*sem + 0.3*attr)

4. extract_attributes(products: List) → attributes: Dict
   Purpose: Extract relevant specs from filtered products
   Output: Grouped by requirement (temp, pressure, material, etc.)
   Implementation: JSON parsing + requirement matching

5. analyze_with_llm(query: str, products: List) → analysis: str
   Purpose: LLM synthesis of top products
   Output: Recommendation + reasoning
   Implementation: Multi-product analysis + caching
```

### Step 2.1: Implement `extract_requirements()`

**Location:** `Layer_2_Agentic_Reasoning/logic/function_library.py`

**Skeleton:**
```python
def extract_requirements(params: Dict) -> Tuple[bool, Dict]:
    """
    Extract structured requirements from user query using LLM
    
    Args:
        params: {
            "query": "user query string",
            "llm_model": "llama3.2",
            "temperature": 0.3
        }
    
    Returns:
        (success: bool, result: {
            "query": str,
            "keywords": List[str],
            "temperature_range": (float, float),
            "pressure_range": (float, float),
            "material": Optional[str],
            "application": Optional[str],
            "confidence": float,
            "reasoning": str
        })
    """
    # TODO: Implement
    pass
```

**Implementation Tasks:**
1. Build LLM prompt that extracts: keywords, temp_range, pressure_range, material, application
2. Parse LLM response into structured Dict
3. Calculate confidence based on clarity of requirements
4. Handle edge cases (vague queries, conflicting requirements, etc.)

### Step 2.2: Implement `semantic_search()`

**Location:** `Layer_2_Agentic_Reasoning/logic/function_library.py`

**Skeleton:**
```python
def semantic_search(params: Dict) -> Tuple[bool, Dict]:
    """
    Search for product families using vector embeddings + guidance
    
    Args:
        params: {
            "query": str,
            "requirements": Dict from extract_requirements,
            "top_k": 15,
            "threshold": 0.70
        }
    
    Returns:
        (success: bool, result: {
            "families": List[Dict with id, name, score],
            "confidence_level": "HIGH" | "MEDIUM" | "LOW",
            "search_quality": float (0-1),
            "suggestions": List[str],
            "guidance": str,
            "fallback_used": bool
        })
    """
    # TODO: Implement
    pass
```

**Implementation Tasks:**
1. Query Chroma with query embeddings
2. Filter by similarity threshold (0.70)
3. If results >= 0.70: return directly (HIGH confidence)
4. If 0.50 <= results < 0.70: return with guidance (MEDIUM confidence)
5. If results < 0.50: suggest related searches (LOW confidence)
6. Use LLM to enhance suggestions if needed

### Step 2.3: Implement `filter_items()`

**Location:** `Layer_2_Agentic_Reasoning/logic/function_library.py`

**Skeleton:**
```python
def filter_items(params: Dict) -> Tuple[bool, Dict]:
    """
    Multi-criteria filtering with composite ranking
    
    Args:
        params: {
            "families": List[Dict],
            "requirements": Dict,
            "database_path": str,
            "max_items": 25
        }
    
    Returns:
        (success: bool, result: {
            "products": List[Dict],
            "total_candidates": int,
            "filtered_count": int,
            "rankings": List[Dict with product_id, composite_score, reasoning],
            "criteria_applied": List[str]
        })
    """
    # TODO: Implement
    pass
```

**Implementation Tasks:**
1. For each family, load products from database
2. Filter products by criteria (temp, pressure, material, etc.)
3. Calculate composite score: 0.7 * semantic + 0.3 * attribute_match
4. Sort by composite score (descending)
5. Limit to 25 products max
6. Return with ranking reasoning for each

### Step 2.4: Enhance `analyze_with_llm()`

**Location:** `Layer_2_Agentic_Reasoning/logic/function_library.py`

**Current Implementation:**
- Works for single products (DIRECT LOOKUP)
- Needs enhancement for multiple products (CONTEXTUAL SEARCH)

**Changes Needed:**
```python
def analyze_with_llm(params: Dict) -> Tuple[bool, Dict]:
    """
    Enhanced for multi-product analysis + caching
    
    Changes:
    1. Check Chroma cache for similar previous queries
    2. Handle 20-25 products in single LLM call
    3. Temperature: 0.3 (was 0.7)
    4. Return composite recommendation with alternatives
    5. Store result in Chroma cache for future use
    
    Cache key: hash(requirements) + product_ids
    Cache TTL: 24 hours
    """
```

### Step 2.5: Implement `extract_attributes()`

**Location:** `Layer_2_Agentic_Reasoning/logic/function_library.py` (or new file)

**Skeleton:**
```python
def extract_attributes(params: Dict) -> Tuple[bool, Dict]:
    """
    Extract attributes relevant to requirements
    
    Args:
        params: {
            "products": List[Dict],
            "requirements": Dict,
            "focus_fields": List[str]
        }
    
    Returns:
        (success: bool, result: {
            "products_with_attributes": List[Dict],
            "attribute_summary": Dict (grouped by requirement),
            "missing_specs": List[str]
        })
    """
    # TODO: Implement
    pass
```

**Implementation Tasks:**
1. For each product, extract specs JSON
2. Map specs to requirement fields (temp → max_temp, etc.)
3. Group results by requirement type
4. Identify missing information for user guidance

---

## Phase 3: Integration & Testing (Day 4)

### Step 3.1: Create Integration Test

**File:** `tests/functional/test_contextual_search.py`

**Skeleton:**
```python
"""
Integration tests for CONTEXTUAL PRODUCT SEARCH strategy
Tests all 5 functions end-to-end with 11 refined questions
"""

import pytest
from Layer_2_Agentic_Reasoning.logic.function_library import (
    extract_requirements,
    semantic_search,
    filter_items,
    extract_attributes,
    analyze_with_llm
)

# 11 refined test questions from previous analysis
TEST_QUESTIONS = [
    "What hoses can handle boiling water?",
    "I need high pressure, low temperature hoses",
    "Fire resistant hoses for industrial use",
    "FDA compliant food processing hoses",
    "Chemical resistant with high temperature rating",
    "Vibration resistant hydraulic hoses",
    "Extreme temperature range hoses (-40 to +200°C)",
    "High pressure (>300 MPa) with small diameter",
    "Flexible hoses for tight bending radius",
    "Long-life hoses for continuous duty",
    "Hoses for oxygen and acetylene systems"
]

@pytest.mark.parametrize("question", TEST_QUESTIONS)
def test_contextual_search_end_to_end(question):
    """
    Test full workflow: extract → search → filter → analyze
    """
    # Step 1: Extract requirements
    success, reqs = extract_requirements({
        "query": question,
        "llm_model": "llama3.2",
        "temperature": 0.3
    })
    assert success, f"Failed to extract requirements for: {question}"
    
    # Step 2: Semantic search
    success, search_results = semantic_search({
        "query": question,
        "requirements": reqs,
        "top_k": 15,
        "threshold": 0.70
    })
    assert success, f"Semantic search failed for: {question}"
    assert len(search_results['families']) > 0, f"No families found for: {question}"
    
    # Step 3: Filter items
    success, filtered = filter_items({
        "families": search_results['families'],
        "requirements": reqs,
        "database_path": "database/harvested.db",
        "max_items": 25
    })
    assert success, f"Filtering failed for: {question}"
    assert 0 < len(filtered['products']) <= 25
    
    # Step 4: Analyze with LLM
    success, analysis = analyze_with_llm({
        "query": question,
        "products": filtered['products'],
        "requirements": reqs,
        "llm_model": "llama3.2",
        "temperature": 0.3
    })
    assert success, f"LLM analysis failed for: {question}"
    assert len(analysis['recommendation']) > 0
    
    print(f"\n✅ {question}")
    print(f"   - Requirements: {reqs['keywords']}")
    print(f"   - Families found: {len(search_results['families'])}")
    print(f"   - Products recommended: {len(filtered['products'])}")
    print(f"   - Recommendation: {analysis['recommendation'][:100]}...")
```

### Step 3.2: Run Integration Tests

```powershell
# Run all tests
pytest tests/functional/test_contextual_search.py -v

# Run specific test
pytest tests/functional/test_contextual_search.py::test_contextual_search_end_to_end -v

# With output
pytest tests/functional/test_contextual_search.py -v -s
```

### Step 3.3: Performance Benchmarking

**File:** `tests/performance/test_contextual_search_perf.py`

**Metrics to track:**
- Query-to-results latency (target: < 5 sec)
- Semantic search latency (target: < 500ms)
- LLM analysis latency (target: < 3 sec)
- Context window utilization
- Cache hit rate

---

## Configuration Summary

**Key Config Values:**
```yaml
# similarity_threshold_primary: 0.70
# - Returns families with score >= 0.70

# similarity_threshold_secondary: 0.50
# - Shows families 0.50-0.70 to user for guidance

# max_products_for_llm: 25
# - Hard limit before sending to LLM

# ranking_weights:
#   semantic_similarity: 0.70
#   attribute_match: 0.30
# - Composite score formula

# analysis_temperature: 0.3
# - Balanced between deterministic and creative

# cache_ttl_hours: 24
# - Cache results for 24 hours in Chroma
```

---

## Troubleshooting

### Problem: "No embedding model available"

**Solution:**
```powershell
# Install sentence-transformers
pip install sentence-transformers torch

# OR start Ollama and pull model
ollama serve  # Terminal 1
ollama pull nomic-embed-text  # Terminal 2
```

### Problem: "Chroma connection failed"

**Solution:**
```powershell
# Verify Chroma path
python -c "from pathlib import Path; print(Path('database/chroma.sqlite3').exists())"

# Reinitialize
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action clear
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action populate
```

### Problem: "LLM context overflow"

**Solution:**
- Check that `max_products_for_llm: 25` is set in config
- Verify composite score filtering is working
- Check logs for actual product count being sent

### Problem: "Slow semantic search"

**Solution:**
- Check embedding model: e5-base is accurate but slower
- Try `nomic-embed-text` (faster, good accuracy)
- Verify Chroma index is built (first query is slower)

---

## Next Steps After Phase 1

**✅ Phase 1 Done:** Infrastructure setup + embeddings populated

**👉 Phase 2:** Implement the 5 core functions

**👉 Phase 3:** Integration testing + performance tuning

**👉 Phase 4:** Deploy to web UI + enable CONTEXTUAL SEARCH strategy

---

## Files Created/Modified

| File | Action | Status |
|------|--------|--------|
| `Layer_2_Agentic_Reasoning/logic/embeddings.py` | CREATE | ✅ DONE |
| `Layer_2_Agentic_Reasoning/config/config.yaml` | UPDATE | ⏳ TODO |
| `Layer_2_Agentic_Reasoning/logic/function_library.py` | UPDATE | ⏳ TODO |
| `tests/functional/test_contextual_search.py` | CREATE | ⏳ TODO |
| `tests/performance/test_contextual_search_perf.py` | CREATE | ⏳ TODO |
| `docs/CONTEXTUAL_SEARCH_IMPLEMENTATION.md` | CREATE | ⏳ TODO |

---

## Success Criteria for Phase 1

✅ Embeddings generated for all 168 families  
✅ Chroma initialized at `database/chroma.sqlite3`  
✅ Semantic search verified working (< 100ms)  
✅ Config updated with CONTEXTUAL_SEARCH settings  
✅ Embedding generation script tested and documented  

---

**Status: Ready to begin Phase 1**

**Next Command:**
```powershell
python Layer_2_Agentic_Reasoning/logic/embeddings.py --action populate --model multilingual-e5-base
```

