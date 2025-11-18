# CONTEXTUAL PRODUCT SEARCH - Strategy Implementation Plan

## Current Status
✅ **Phase 1: Embedding Infrastructure Complete**
- 168 product family embeddings generated and stored
- Vector database: `database/vector_index/chroma.sqlite3`
- Embedding model: qwen3-embedding:8b (4096-dimensional)
- Semantic search verified and working
- Code linting: 100% clean

---

## Phase 2: Core Strategy Implementation

### Overview
Implement 5 core functions that form the CONTEXTUAL PRODUCT SEARCH strategy:

```
User Query
    ↓
[1. Extract Requirements] → Extract intent, constraints, preferences
    ↓
[2. Semantic Search] → Find similar product families by semantic similarity
    ↓
[3. Filter Items] → Apply attribute-based filters (temperature, pressure, material, etc.)
    ↓
[4. Extract Attributes] → Parse product specifications from results
    ↓
[5. Analyze with LLM] → Rank and explain results with LLM context
    ↓
Ranked Product Recommendations
```

---

## Implementation Details

### Function 1: `func_extract_requirements()`
**Purpose**: Parse user query to extract structured requirements

**Input**: User query string (Swedish)
**Output**: Dict with extracted requirements
```python
{
    "intent": "find high pressure hoses",
    "constraints": {
        "temperature_range": (20, 80),  # Celsius
        "pressure_min": 350,             # bar
        "material": "rubber",
        "thread_type": "G"
    },
    "preferences": {
        "compact": True,
        "lightweight": False
    },
    "confidence": 0.92
}
```

**Implementation Strategy**:
- Use LLM to parse query (not just string matching)
- Extract: temperature, pressure, materials, thread types, size preferences
- Preserve Swedish context (catalog is in Swedish)
- Return structured dict with confidence scores

**Dependencies**: LangChain LLM integration, prompt template

---

### Function 2: `func_semantic_search()`
**Purpose**: Find similar product families using vector similarity

**Input**: 
- Query text (or query embedding)
- Number of results (default: 5)

**Output**: List of (family_id, family_data, similarity_score)

**Implementation Strategy**:
- Use qwen3-embedding:8b to embed query (same model as data)
- Query Chroma collection with cosine distance
- Return top N results with scores
- Filter by minimum similarity threshold (0.6)

**Dependencies**: Ollama, Chroma DB

---

### Function 3: `func_filter_items()`
**Purpose**: Apply attribute-based filtering to candidates

**Input**:
- Candidate families (from semantic search)
- Requirements (from extract_requirements)

**Output**: Filtered families list

**Implementation Strategy**:
- Parse construction_details JSON for each family
- Match against constraints:
  - Temperature range
  - Pressure rating
  - Material type
  - Thread standard (G, JIC, ORFS, NPTF, BSP)
  - Coupling type
- Return families that meet all constraints
- Log filtering statistics

**Dependencies**: JSON parsing, construction_details schema knowledge

---

### Function 4: `func_extract_attributes()`
**Purpose**: Parse and standardize product attributes from results

**Input**: Filtered product families
**Output**: Standardized attributes dict for each family

**Implementation Strategy**:
- Extract from construction_details JSON
- Standardize formats (pressures in bar, temperatures in C)
- Parse applications text for use cases
- Extract coupling information
- Create human-readable specifications table

**Dependencies**: Schema mapping, JSON parsing

---

### Function 5: `func_analyze_with_llm()`
**Purpose**: Rank results and provide LLM-enhanced explanations

**Input**:
- Filtered + attribute-extracted families
- Original user query
- LLM context (model: gpt-4 or local LLM)

**Output**: Ranked recommendations with explanations

**Implementation Strategy**:
- Use LLM to re-rank by relevance to query
- Generate explanation for each recommendation
- Provide confidence scores
- Include alternative suggestions if relevant
- Format for presentation to user

**Dependencies**: LangChain LLM, prompt templates

---

## Technical Architecture

### Storage & Connectivity
- **Embeddings**: Chroma (database/vector_index/chroma.sqlite3)
- **Source Data**: harvested.db (168 product families)
- **Query Engine**: Ollama (local embedding model)
- **LLM Context**: LangChain integration

### Function Organization
- Location: `Layer_2_Agentic/logic/function_library.py`
- Pattern: Each function returns (success: bool, result: Dict)
- Error handling: Try/catch with logging
- Caching: Query results cached for performance

### Testing Strategy
- Unit tests for each function
- Integration tests for workflow
- Test data: 11 refined product questions
- Benchmark: Query response time < 5 seconds

---

## Phase 2A: Schema & Mapping

Before implementing functions, we need:

### 1. Construction Details Schema
**Goal**: Understand structure of construction_details JSON for all 168 families

**Task**: 
```python
# Sample construction_details structure from harvested.db
# Need to extract for schema mapping
```

### 2. Thread Type Standards
**Goal**: Map thread types across products

**Known Types**: G, JIC, ORFS, NPTF, BSP

### 3. Material Classifications
**Goal**: Group materials for filtering

**Known Categories**: 
- Rubber (SBR, NBR, EPDM, etc.)
- Thermoplastic
- Steel
- Composite

### 4. Temperature/Pressure Ranges
**Goal**: Extract min/max values for all families

---

## Implementation Roadmap

### Step 1: Schema Analysis (Day 1)
- [ ] Analyze construction_details JSON structure
- [ ] Create schema mapping document
- [ ] Identify field standardizations needed

### Step 2: Core Function Implementation (Days 2-3)
- [ ] Implement func_extract_requirements()
- [ ] Implement func_semantic_search()
- [ ] Implement func_filter_items()
- [ ] Implement func_extract_attributes()
- [ ] Implement func_analyze_with_llm()

### Step 3: Integration & Testing (Days 4-5)
- [ ] Create integration tests
- [ ] Test with 11 product questions
- [ ] Performance optimization
- [ ] Error handling & edge cases

### Step 4: Documentation (Day 6)
- [ ] API documentation
- [ ] Usage examples
- [ ] Troubleshooting guide

---

## Success Criteria

- ✅ All 5 functions implemented and tested
- ✅ 11 product questions answered correctly
- ✅ Query response time < 5 seconds per query
- ✅ Semantic search accuracy > 90%
- ✅ Zero linting errors
- ✅ Full code documentation

---

## Test Questions (11 refined product questions)

Will be provided in separate document with:
- Query text (Swedish)
- Expected family IDs
- Required attributes
- Expected accuracy threshold

---

## Next Steps

1. **Approve this strategy** - Confirm plan aligns with requirements
2. **Schema analysis** - Extract and document construction_details structure
3. **Function implementation** - Start with extract_requirements()
4. **Testing** - Validate each function with sample queries

