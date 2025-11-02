# Quick Reference: Context Management

## When to Use Which Mode?

| Your Situation | Use This | How |
|----------------|----------|-----|
| 🟢 **1-20 products** | Direct Mode | Just pass `extracted_data` |
| 🟡 **20-200 products** | Chunked Mode | Pass `extracted_data` (auto-chunks) |
| 🔵 **200+ products** | Assembly Mode | Pass `assembled_data` parameter |

---

## Mode Indicators

Check the return value to see which mode was used:

```python
success, result = func_analyze_with_llm({...})

print(result['mode_used'])  # "direct", "chunked", or "assembly"
```

### Direct Mode ✅
- **When**: Small datasets
- **Speed**: Fastest (2-3s)
- **Accuracy**: 100%
- **Indicator**: `mode_used == "direct"`

### Chunked Mode ⚠️
- **When**: Large datasets (auto-triggered)
- **Speed**: Medium (3-5s)
- **Accuracy**: 95%+ (depends on relevance filtering)
- **Indicator**: `mode_used == "chunked"` and `context_truncated == True`

### Assembly Mode 🔧
- **When**: Massive datasets
- **Speed**: Slower (4-8s)
- **Accuracy**: 100%
- **Indicator**: `mode_used == "assembly"`

---

## Quick Examples

### Example 1: Simple Query
```python
# Automatic mode selection
success, result = func_analyze_with_llm({
    "task": "specification",
    "question": "What's the pressure rating?",
    "extracted_data": products
})
```

### Example 2: Force Assembly Mode
```python
# For very large datasets
assembled = func_assemble_table({"tables": all_data})
success, result = func_analyze_with_llm({
    "task": "analysis",
    "question": "Which products are best?",
    "assembled_data": assembled["Assembled Data"]
})
```

### Example 3: Custom Limit
```python
# Allow more context
success, result = func_analyze_with_llm({
    "task": "comparison",
    "question": "Compare all features",
    "extracted_data": products,
    "max_context_chars": 50000  # Larger limit
})
```

---

## Diagnostic Checklist

### If Analysis Seems Incomplete

1. **Check if truncated**:
   ```python
   if result['context_truncated']:
       print("⚠️ Some products were excluded")
   ```

2. **Check products analyzed**:
   ```python
   print(f"Analyzed {result['products_analyzed']} products")
   ```

3. **Check context size**:
   ```python
   print(f"Context: {result['context_size_chars']} chars")
   ```

### Solution: Use Assembly Mode
```python
# Instead of direct extraction
assembled = func_assemble_table({"tables": large_data})
result = func_analyze_with_llm({
    "assembled_data": assembled["Assembled Data"]
})
```

---

## Common Patterns

### Pattern 1: Quick Lookup
```python
extract → analyze
```

### Pattern 2: Filtered Analysis
```python
filter → extract → analyze
```

### Pattern 3: Large Dataset
```python
extract → assemble → analyze (via temp.db)
```

### Pattern 4: Complex Query
```python
semantic_search → extract → analyze
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Context too large" error | Use assembly mode |
| Results seem incomplete | Check `context_truncated` flag |
| Wrong products analyzed | Use assembly mode with SQL filter |
| Slow performance | Reduce `max_context_chars` |

---

## Performance Tips

1. **Filter before extracting**: Use `func_filter_items` first
2. **Use assembly for 200+**: Don't try direct mode
3. **Adjust context limit**: Based on your LLM model
4. **Monitor diagnostics**: Check `mode_used` regularly

---

## Task Types (All Accepted)

No restrictions! Examples:
- `"compatibility"`
- `"recommendation"`
- `"safety_assessment"`
- `"troubleshooting"`
- `"general_query"`
- `"specification"`
- Any other task type you need!

---

## Key Parameters

```python
func_analyze_with_llm({
    "task": str,                    # Required: Any task type
    "question": str,                # Required: Your question
    "extracted_data": list/dict,    # Optional: Direct data
    "assembled_data": str,          # Optional: Assembly mode
    "max_context_chars": int        # Optional: Default 30000
})
```

---

## Return Values

```python
{
    "Analysis": str,              # The answer
    "Task": str,                  # Task type
    "mode_used": str,             # Which mode was used
    "products_analyzed": int,     # How many products
    "context_truncated": bool,    # Was data cut?
    "context_size_chars": int     # Final size
}
```

---

**Remember**: The system automatically selects the best mode for your data size!
