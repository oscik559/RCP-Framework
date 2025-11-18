# CONTEXTUAL PRODUCT SEARCH - Strategy Development

## Strategy Overview

**CONTEXTUAL PRODUCT SEARCH** is designed for application-based queries where users describe their use case, requirements, or environment rather than asking for a specific product code.

**Key Characteristic:** Requires semantic understanding + multi-criteria filtering + LLM ranking

---

## Questions Suitable for CONTEXTUAL PRODUCT SEARCH Strategy

These questions require understanding the *context* and *requirements* behind the query, not just direct product lookups.

### ✅ IDEAL QUESTIONS (Primary - Well-suited for strategy)

**Q8: "What hoses can be used for boiling water?"**
- Type: Temperature + application context
- Reasoning: Requires semantic understanding of "boiling water" → search for temp specs ≥ 100°C + hot water applications
- Current Quality: ✅ Good - clear intent
- Data Match: applications + construction_details.temperature_range
- Confidence: High

**Q10: "Which hydraulic hose and sleeve should I get for a particular excavator?"**
- Type: Application context + equipment type
- Reasoning: Requires matching equipment type (excavator) to product applications + sleeve recommendations
- Current Quality: ⚠️ Ambiguous - "particular excavator" is vague; should specify model/pressure/conditions
- Suggested Refinement: "Which hydraulic hose and sleeve are recommended for a 25-ton excavator operating at 280 bar?"
- Data Match: applications (excavator-specific) + construction_details.sleeve_info
- Confidence: High

**Q14: "Which products are approved for food use?"**
- Type: Regulatory/compliance context
- Reasoning: Search for food safety approvals (FDA) + applications.food_use
- Current Quality: ✅ Good - clear and specific
- Data Match: construction_details.standards (FDA) + applications.food
- Confidence: High

**Q22: "Do you have hoses that can withstand both high pressure and vibrations?"**
- Type: Multi-criteria environment context
- Reasoning: Requires combining pressure specifications + vibration resistance application
- Current Quality: ✅ Good - clear dual-criteria request
- Data Match: specifications.working_pressure + applications.vibration_resistant
- Confidence: High

**Q24: "What hoses can be used for chemicals?"**
- Type: Application context + environment
- Reasoning: Search for chemical-compatible materials + applications
- Current Quality: ⚠️ Vague - which type of chemicals? aggressive, mild, specific?
- Suggested Refinement: "What hoses are suitable for transporting industrial chemicals (aggressive oils, solvents)?"
- Data Match: applications.chemical + construction_details.materials
- Confidence: High

**Q34: "I need a blue water hose in 3/4\""?**
- Type: Specification + color + application context
- Reasoning: Dimension (3/4") + water application + color preference
- Current Quality: ⚠️ Color specification not in database (not searchable)
- Suggested Refinement: "I need a water hose in 3/4\" diameter for general purpose use"
- Data Match: specifications.dimensions + applications.water_use
- Confidence: Medium (color may not be available)

**Q47: "Need suggestions for hose for chemicals"**
- Type: Application context (informal)
- Reasoning: Semantic search for chemical applications
- Current Quality: ⚠️ Informal language - should be structured
- Suggested Refinement: "What hose recommendations do you have for chemical/solvent applications?"
- Data Match: applications.chemical
- Confidence: High

**Q48: "Hose for alkaline degreasing?"**
- Type: Application context (informal)
- Reasoning: Specific chemical application context
- Current Quality: ⚠️ Very informal - needs clarification
- Suggested Refinement: "Which hoses are suitable for alkaline degreasing solutions and cleaning applications?"
- Data Match: applications.degreasing + construction_details.chemical_resistance
- Confidence: Medium

**Q82: "Which hoses are FDA approved for food use?"**
- Type: Regulatory compliance context
- Reasoning: Search for FDA certification + food applications
- Current Quality: ✅ Good - specific and clear
- Data Match: construction_details.standards (FDA) + applications.food_use
- Confidence: High

### ⚠️ MARGINAL QUESTIONS (Secondary - Partially suitable, needs refinement)

**Q9: "Which sleeve should I get for hose X?"**
- Issue: Requires knowing which "hose X" is - incomplete question
- Refinement: "What sleeve is compatible with a 3/4\" high-pressure hose rated for 280 bar?"
- Strategy Fit: Low - better handled by DIRECT SPECIFICATION LOOKUP if product code given

**Q12: "Which coupling fits my existing hose with dimension Y?"**
- Issue: "dimension Y" is vague - what dimension?
- Refinement: "What couplings are compatible with a hose having a 19mm outer diameter?"
- Strategy Fit: Medium - dimensional filtering required

**Q30: "Which hoses are suitable for the 42 series?"**
- Issue: Unknown what "42 series" refers to (product line? pressure? series code?)
- Refinement: "Which hoses are compatible with the SAE 42 flange series?"
- Strategy Fit: Medium - needs clarification

**Q67: "Which socket fits 1118-12-16?"**
- Issue: Specific product code given - should use DIRECT SPECIFICATION LOOKUP instead
- Strategy Fit: Low - not contextual search

**Q75: "Can I use environmental oil in 1105-63?"**
- Issue: Specific product code given - better for DIRECT SPECIFICATION LOOKUP
- Refinement: Could work here if framed as: "What oils are compatible with rubber-based hoses?"
- Strategy Fit: Low-Medium

**Q79: "Is there a hose with a smooth outer casing?"**
- Issue: Design feature not well-indexed in database
- Refinement: "Do you have hoses with smooth outer covers for special applications?"
- Strategy Fit: Low - needs database enhancement

### ❌ NOT SUITABLE (Out of scope for CONTEXTUAL PRODUCT SEARCH)

**Q11, Q20, Q25, Q36, Q37, Q66, Q77, Q81:** These are better handled by:
- DIRECT SPECIFICATION LOOKUP (if product code given)
- STANDARD & COMPLIANCE LOOKUP (if standards-focused)
- TECHNICAL CALCULATION (if numerical comparisons needed)

---

## Refined Question Set for CONTEXTUAL PRODUCT SEARCH

Based on analysis above, here are the **refined questions** best suited for this strategy:

### Tier 1: Ready to Implement (8 questions)
1. **Q8:** "What hoses can be used for boiling water?" ✅
2. **Q14:** "Which products are approved for food use?" ✅
3. **Q22:** "Do you have hoses that can withstand both high pressure and vibrations?" ✅
4. **Q24 (refined):** "What hoses are suitable for transporting industrial chemicals (aggressive oils, solvents)?" 
5. **Q34 (refined):** "I need a water hose in 3/4\" diameter for general purpose use"
6. **Q47 (refined):** "What hose recommendations do you have for chemical/solvent applications?"
7. **Q48 (refined):** "Which hoses are suitable for alkaline degreasing solutions and cleaning applications?"
8. **Q82:** "Which hoses are FDA approved for food use?" ✅

### Tier 2: Needs Clarification (3 questions)
9. **Q10 (refined):** "Which hydraulic hose and sleeve are recommended for a 25-ton excavator operating at 280 bar?"
10. **Q12 (refined):** "What couplings are compatible with a hose having a 19mm outer diameter?"
11. **Q30 (refined):** "Which hoses are compatible with the SAE 42 flange series?"

---

## Function Block Architecture for CONTEXTUAL PRODUCT SEARCH

Strategy Function Chain:
```
Extract Requirements 
  ↓
Semantic Search (vector embeddings to find related families)
  ↓
Filter Items (multi-criteria filtering based on requirements)
  ↓
Extract Attributes (get detailed specs for filtered products)
  ↓
Analyze With LLM (synthesize results with natural language explanation)
```

### Function 1: Extract Requirements

**Purpose:** Parse user query to extract structured requirements

**Input:**
```python
{
    "Input": "What hoses can be used for boiling water?"
}
```

**Output:**
```python
{
    "requirements": {
        "temperature_min": 100,
        "temperature_unit": "°C",
        "applications": ["hot water", "boiling", "high temperature"],
        "environment": "industrial",
        "priority_fields": ["temperature_range", "applications"],
        "confidence": 0.95
    },
    "query_tokens": ["hoses", "boiling", "water"],
    "context": "temperature_and_application"
}
```

**Implementation Notes:**
- Use LLM to extract structured requirements from natural language
- Identify key parameters (temperature, pressure, environment, material, etc.)
- Extract keywords for semantic search
- Provide confidence score

---

### Function 2: Semantic Search

**Purpose:** Find related product families using embeddings + keyword matching

**Input:**
```python
{
    "query": "What hoses can be used for boiling water?",
    "keywords": ["hot water", "boiling", "high temperature"],
    "top_k": 15,
    "filters": {"temperature_min": 100}
}
```

**Output:**
```python
{
    "results": [
        {
            "family_id": 12,
            "family_name": "KAPPAFLEX HT-2000",
            "similarity_score": 0.92,
            "match_reason": "High-temperature rated hose, hot water applications",
            "construction_summary": "Natural rubber, temperature range -40°C to +100°C"
        },
        {
            "family_id": 45,
            "family_name": "THERMOMAX 300",
            "similarity_score": 0.88,
            "match_reason": "Designed for boiling water and steam applications",
            "construction_summary": "Synthetic rubber, up to 120°C continuous"
        }
    ],
    "count": 2,
    "search_method": "semantic_vector + keyword_filter"
}
```

**Implementation Notes:**
- Use Chroma vector DB with sentence-transformers embeddings
- Filter by temperature range if specified in requirements
- Return similarity scores and match reasoning
- Limit to top 15 results for efficiency

---

### Function 3: Filter Items

**Purpose:** Apply multi-criteria filtering to narrow results

**Input:**
```python
{
    "items": [
        {"family_id": 12, "specifications": {"temp_min": -40, "temp_max": 100, ...}},
        {"family_id": 45, "specifications": {"temp_min": -40, "temp_max": 120, ...}}
    ],
    "conditions": [
        {"field": "temperature_max", "operator": ">=", "value": 100},
        {"field": "applications", "operator": "contains", "value": "hot water"}
    ],
    "mode": "AND"
}
```

**Output:**
```python
{
    "filtered_items": [
        {"family_id": 12, "match_score": 0.95},
        {"family_id": 45, "match_score": 0.98}
    ],
    "count": 2,
    "conditions_applied": [
        "temperature_max >= 100",
        "applications contains 'hot water'"
    ],
    "filtered_out_count": 0
}
```

**Implementation Notes:**
- Support multiple conditions (AND/OR logic)
- Return match scores based on how well items meet criteria
- Track which conditions filtered items out
- Handle null/missing values gracefully

---

### Function 4: Extract Attributes

**Purpose:** Get detailed specifications for filtered products

**Input:**
```python
{
    "items": [12, 45],
    "extraction_type": "contextual",
    "config": {
        "focus_fields": ["temperature_range", "applications", "materials", "standards"],
        "include_products": True
    }
}
```

**Output:**
```python
{
    "extracted_data": [
        {
            "family_id": 12,
            "family_name": "KAPPAFLEX HT-2000",
            "temperature_range": "-40°C to +100°C",
            "materials": "Natural rubber with heat-resistant layers",
            "applications": "Hot water transport, industrial heating",
            "standards": ["EN 856", "ISO 1402"],
            "products_count": 15,
            "product_examples": [
                {"product_code": "1071-00-06", "size": "6mm", "working_pressure": "25 MPa"},
                {"product_code": "1071-00-12", "size": "12mm", "working_pressure": "25 MPa"}
            ]
        },
        {
            "family_id": 45,
            "family_name": "THERMOMAX 300",
            "temperature_range": "-40°C to +120°C",
            "materials": "Synthetic rubber, advanced polymer blend",
            "applications": "Boiling water, steam, high-temperature industrial",
            "standards": ["EN 857 2SC", "FDA"],
            "products_count": 8,
            "product_examples": [...]
        }
    ],
    "count": 2
}
```

**Implementation Notes:**
- Extract contextually relevant fields based on query
- Include product examples for each family
- Return hierarchical data (family → products)
- Format for LLM consumption

---

### Function 5: Analyze With LLM

**Purpose:** Synthesize results into natural language answer

**Input:**
```python
{
    "task": "recommendation",
    "extracted_data": [...],
    "question": "What hoses can be used for boiling water?"
}
```

**Output:**
```python
{
    "Analysis": "Based on our product database, we recommend two main options for boiling water applications:\n\n1. **KAPPAFLEX HT-2000** - Rated up to 100°C continuous, ideal for general hot water transport. Natural rubber construction with proven reliability.\n\n2. **THERMOMAX 300** - Premium option rated up to 120°C, specifically designed for boiling water and steam applications. Meets FDA standards for enhanced chemical resistance.\n\nFor your specific application, THERMOMAX 300 is the better choice due to its higher temperature rating and specialized design.",
    "Task": "recommendation",
    "Context": "2 product families evaluated, both suitable for boiling water applications"
}
```

---

## Summary: Question Quality Assessment

### ✅ Well-Written Questions (Ready to implement: 5)
1. Q8 - Clear and specific
2. Q14 - Compliance-focused, unambiguous
3. Q22 - Multi-criteria, well-defined
4. Q82 - Clear regulatory context

### ⚠️ Needs Minor Refinement (Improve clarity: 8)
1. Q10 - Too vague ("particular excavator")
2. Q24 - Vague chemical type
3. Q34 - Color specification not in database
4. Q47 - Informal, needs structure
5. Q48 - Too informal, needs context
6. Q12 - Vague ("dimension Y")
7. Q30 - Unknown reference ("42 series")
8. Q79 - Design feature poorly indexed

### ❌ Not Suitable for This Strategy (Route elsewhere: 3)
1. Q9 - Needs specific product code first
2. Q67 - Has specific product code → use DIRECT LOOKUP
3. Q75 - Has specific product code → use DIRECT LOOKUP

---

## Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Implement Extract Requirements function
- [ ] Test with 5 well-written questions
- [ ] Implement Semantic Search function
- [ ] Test vector retrieval with families

### Phase 2: Filtering & Extraction (Week 2)
- [ ] Implement Filter Items function
- [ ] Implement Extract Attributes (contextual mode)
- [ ] Integration test all 4 functions

### Phase 3: LLM Synthesis & Testing (Week 2)
- [ ] Integrate Analyze With LLM
- [ ] End-to-end testing with all 11 refined questions
- [ ] Performance optimization

