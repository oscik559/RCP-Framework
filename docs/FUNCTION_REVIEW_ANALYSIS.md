# Function Library Review - Generic Building Blocks Analysis

## Summary of All Functions (30 total)

### ✅ ALREADY GENERIC - Database/Search Operations (8 functions)
1. **func_table_search** - Generic table search with keywords
2. **func_table_search_on_document** - Document-specific table search
3. **func_filter_table** - Generic table filtering by keywords
4. **func_filter_table_by_field** - Filter table by specific field
5. **func_assemble_table** - Assemble table from rows
6. **func_filter_items** - Generic item filtering engine
7. **func_semantic_search** - Generic semantic vector search
8. **func_aggregate_data** - Generic data aggregation

### ✅ ALREADY GENERIC - Data Processing (6 functions)
9. **func_transform_data** - Generic data transformation
10. **func_extract_attributes** - Extract attributes from items
11. **func_compare_items** - Generic item comparison
12. **func_calculate** - Generic mathematical calculations
13. **func_convert_units** - Unit conversion (temperature, pressure, etc.)
14. **func_analyze_with_llm** - Generic LLM analysis

### ✅ ALREADY GENERIC - Image Processing (3 functions)
15. **func_image_search** - Generic image search
16. **func_display_images** - Display images
17. **func_analyze_image** - Generic image analysis with LLM
18. **func_generate_visual_layout** - Visual layout generation

### ✅ ALREADY GENERIC - Product/Item Operations (5 functions)
19. **func_search_products** - Generic product search (fixed table names)
20. **func_get_related_items** - Get related items by relationship
21. **func_navigate_hierarchy** - Navigate category/product hierarchies
22. **func_discover_items** - Discover items in categories
23. **func_get_metadata** - Get metadata (families, stats, location)

### ⚠️ NEEDS REVIEW - Domain-Specific Functions (8 functions)
24. **func_extract_product_number** ⚠️ - Extract product codes (too specific?)
25. **func_normalize_product_number** ⚠️ - Normalize product codes (SAAB-specific?)
26. **func_suggest_keywords** ⚠️ - Keyword suggestions (too specific?)
27. **func_change_keyword** ⚠️ - Keyword modification (too specific?)
28. **func_find_latest_document** ⚠️ - Find latest document (too simplistic?)
29. **func_lookup_standard** ⚠️ - Lookup standards (domain-specific?)

---

## Detailed Analysis of Functions Needing Review

### 1. func_extract_product_number (Line 1852)
**Current**: Extracts product numbers with LLM
**Issue**: Name suggests "product number" but should be generic "entity extraction"
**Recommendation**: 
- Rename to `func_extract_entities` or keep as is (product numbers are generic concept)
- Already generic enough - product numbers = SKUs/part numbers/article numbers

### 2. func_normalize_product_number (Line 1940)
**Current**: Normalizes product codes using LLM
**Issue**: May have SAAB-specific logic for format variations
**Recommendation**: Review normalization rules - ensure they're generic product code patterns

### 3. func_suggest_keywords (Line 1973)
**Current**: Uses LLM to suggest alternative keywords
**Issue**: None - this is already generic
**Status**: ✅ Generic

### 4. func_change_keyword (Line 1534)
**Current**: Allows keyword modification
**Issue**: None - generic keyword manipulation
**Status**: ✅ Generic

### 5. func_find_latest_document (Line 793)
**Current**: Returns last document from list
**Issue**: Too simplistic - just returns last item from comma-separated list
**Recommendation**: Enhance or remove - not really useful as-is

### 6. func_lookup_standard (Line 3117)
**Current**: Looks up standards/certifications
**Issue**: Checks for specific standards (SAE, ISO, EN, DIN)
**Recommendation**: Make standards list configurable or database-driven

---

## Functions with Hardcoded Values to Review

### Priority 1: func_normalize_product_number
```python
# Line 1940 - Check for SAAB-specific patterns
```

### Priority 2: func_lookup_standard
```python
# Line 3117 - Hardcoded standard prefixes
COMMON_STANDARDS = ["SAE", "ISO", "EN", "DIN", "ASTM", "API"]
```

### Priority 3: func_extract_product_number
```python
# Line 1852 - Check LLM prompt for domain-specific language
```

---

## Action Items

### HIGH PRIORITY
1. ✅ Review `func_normalize_product_number` for SAAB-specific logic
2. ✅ Review `func_extract_product_number` LLM prompt for domain specificity
3. ✅ Make `func_lookup_standard` standards list database-driven

### MEDIUM PRIORITY
4. ✅ Review `func_find_latest_document` - enhance or remove
5. ✅ Review all LLM prompts for domain-specific language
6. ✅ Ensure all function docstrings describe generic use cases

### LOW PRIORITY
7. Add configuration options for domain-specific parameters
8. Create domain adaptation layer for specialized use cases

---

## Conclusion

**Status**: 22/30 functions (73%) are already generic
**Action Required**: Review 8 functions for domain specificity
**Risk Level**: LOW - Most issues are in prompts/configuration, not logic

The framework is largely generic with good separation of concerns. Main areas to address:
1. LLM prompts may contain domain-specific language
2. Some normalization logic may be SAAB-specific
3. Standards lookup uses hardcoded list (should be database-driven)
