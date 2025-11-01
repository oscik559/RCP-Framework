# Quick Start: Integrating the Agentic Reasoning System

This guide will help you quickly integrate the generic agentic reasoning system into your application.

## 5-Minute Integration

### Step 1: Configure Domain Settings

Edit `Layer_2/agentic_reasoning/config/domain_config.py` with your domain specifics:

```python
DOMAIN_NAME = "MyApplication"
DATABASE_PATH = "../path/to/your/database.db"
```

### Step 2: Define Your Functions

In `agentic_reasoning/logic/function_library.py`, add your functions:

```python
def find_my_entity(entity_id: str) -> dict:
    """Find entity in your database."""
    import sqlite3
    from ..config.domain_config import DATABASE_PATH
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"success": True, "entity": dict(result)}
    return {"success": False, "error": "Not found"}
```

### Step 3: Create Strategy Templates

In `agentic_reasoning/logic/templates.py`, add to strategy library:

```python
STRATEGY_LIBRARY.append({
    "strategyName": "FindEntity",
    "description": "Locate entity by identifier",
    "goal": "Find and return entity details",
    "functions": [
        {
            "name": "find_my_entity",
            "description": "Query database for entity",
            "parameters": {"entity_id": "string"}
        }
    ],
    "applicableWhen": "User asks for entity information",
    "expectedOutcome": "Entity details or not found message"
})
```

### Step 4: Test Your Integration

```python
from agentic_reasoning.config.session_config import get_default_session_state
from agentic_reasoning.logic.state_graph import get_graph
from agentic_reasoning.logic.templates import populate_template_libraries

# Initialize
query = "Find entity ABC123"
state = get_default_session_state(query=query)
populate_template_libraries()

# Execute
result = get_graph().invoke(state)

# Print answer
print(result['answer'])
```

## Complete Integration Example

### Example: Product Catalog Integration

Let's integrate with a product catalog:

#### 1. Domain Configuration (`domain_config.py`)

```python
DOMAIN_NAME = "Product Catalog"
DATABASE_PATH = "../../data/products.db"

DOMAIN_FUNCTIONS = [
    {
        "name": "find_product_by_code",
        "description": "Find product by product code",
        "parameters": ["product_code"],
        "returns": "product_details"
    },
    {
        "name": "search_products_by_category",
        "description": "Search products in a category",
        "parameters": ["category"],
        "returns": "product_list"
    },
    {
        "name": "compare_products",
        "description": "Compare specifications of two products",
        "parameters": ["product_code_1", "product_code_2"],
        "returns": "comparison_table"
    }
]

EXAMPLE_QUERIES = [
    "What are the specifications of product 1059-01-04?",
    "Find all products in HÖGTRYCKSSLANG category",
    "Compare product 1059-01-04 with 1059-01-06"
]
```

#### 2. Function Implementation

```python
# In function_library.py

import sqlite3
import json
from ..config.domain_config import DATABASE_PATH

def find_product_by_code(product_code: str) -> dict:
    """
    Find product by product code from database.
    
    Args:
        product_code: Product code (e.g., "1059-01-04")
    
    Returns:
        Dictionary with product details including family and specifications
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.product_code,
            p.variant_suffix,
            p.configuration_type,
            p.specifications,
            pf.family_code,
            pf.name as family_name,
            pf.construction_details,
            pf.applications,
            c.name as category
        FROM products p
        JOIN product_families pf ON p.family_id = pf.id
        JOIN categories c ON pf.category_id = c.id
        WHERE p.product_code = ?
    """
    
    cursor.execute(query, (product_code,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return {
            "success": False,
            "error": f"Product {product_code} not found"
        }
    
    # Parse JSON fields
    specifications = json.loads(result[3]) if result[3] else {}
    construction = json.loads(result[6]) if result[6] else {}
    
    return {
        "success": True,
        "product": {
            "product_code": result[0],
            "variant": result[1],
            "configuration_type": result[2],
            "specifications": specifications,
            "family_code": result[4],
            "family_name": result[5],
            "construction": construction,
            "applications": result[7],
            "category": result[8]
        }
    }


def search_products_by_category(category: str) -> dict:
    """
    Search all products in a category.
    
    Args:
        category: Category name (e.g., "HÖGTRYCKSSLANG")
    
    Returns:
        Dictionary with list of products
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.product_code,
            pf.name as family_name,
            p.configuration_type
        FROM products p
        JOIN product_families pf ON p.family_id = pf.id
        JOIN categories c ON pf.category_id = c.id
        WHERE c.name = ?
        ORDER BY pf.family_code, p.product_code
    """
    
    cursor.execute(query, (category,))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        return {
            "success": False,
            "error": f"No products found in category {category}"
        }
    
    products = [
        {
            "product_code": row[0],
            "family_name": row[1],
            "type": row[2]
        }
        for row in results
    ]
    
    return {
        "success": True,
        "category": category,
        "count": len(products),
        "products": products
    }


def compare_products(product_code_1: str, product_code_2: str) -> dict:
    """
    Compare specifications of two products.
    
    Args:
        product_code_1: First product code
        product_code_2: Second product code
    
    Returns:
        Comparison of specifications
    """
    # Get both products
    product1 = find_product_by_code(product_code_1)
    product2 = find_product_by_code(product_code_2)
    
    if not product1["success"] or not product2["success"]:
        return {
            "success": False,
            "error": "One or both products not found"
        }
    
    p1 = product1["product"]
    p2 = product2["product"]
    
    # Compare specifications
    spec1 = p1["specifications"]
    spec2 = p2["specifications"]
    
    comparison = {
        "product_1": {
            "code": p1["product_code"],
            "family": p1["family_name"],
            "specs": spec1
        },
        "product_2": {
            "code": p2["product_code"],
            "family": p2["family_name"],
            "specs": spec2
        },
        "differences": {}
    }
    
    # Find differences
    all_keys = set(spec1.keys()) | set(spec2.keys())
    for key in all_keys:
        val1 = spec1.get(key)
        val2 = spec2.get(key)
        if val1 != val2:
            comparison["differences"][key] = {
                "product_1": val1,
                "product_2": val2
            }
    
    return {
        "success": True,
        "comparison": comparison
    }
```

#### 3. Strategy Templates

```python
# In templates.py

PRODUCT_STRATEGIES = [
    {
        "strategyName": "ProductLookup",
        "description": "Find product by code and return details",
        "goal": "Retrieve complete product information",
        "functions": [
            {
                "name": "find_product_by_code",
                "description": "Query product from database",
                "parameters": {"product_code": "extracted from query"}
            }
        ],
        "applicableWhen": "User asks for specific product information",
        "expectedOutcome": "Complete product specifications and details"
    },
    {
        "strategyName": "CategoryBrowse",
        "description": "Browse products in a category",
        "goal": "List all products in specified category",
        "functions": [
            {
                "name": "search_products_by_category",
                "description": "Search by category name",
                "parameters": {"category": "extracted from query"}
            }
        ],
        "applicableWhen": "User wants to browse or list products in category",
        "expectedOutcome": "List of products with basic information"
    },
    {
        "strategyName": "ProductComparison",
        "description": "Compare two products side by side",
        "goal": "Provide comparative analysis of two products",
        "functions": [
            {
                "name": "find_product_by_code",
                "description": "Get first product",
                "parameters": {"product_code": "first product code"}
            },
            {
                "name": "find_product_by_code",
                "description": "Get second product",
                "parameters": {"product_code": "second product code"}
            },
            {
                "name": "compare_products",
                "description": "Generate comparison",
                "parameters": {
                    "product_code_1": "first product code",
                    "product_code_2": "second product code"
                }
            }
        ],
        "applicableWhen": "User wants to compare two specific products",
        "expectedOutcome": "Side-by-side comparison showing differences"
    }
]

# Add to library
def populate_template_libraries():
    """Populate strategy and function libraries."""
    STRATEGY_LIBRARY.extend(PRODUCT_STRATEGIES)
    # ... rest of your templates
```

#### 4. Run It

```python
# In main.py

user_query = "What are the specifications of product 1059-01-04?"

# Or
user_query = "Compare product 1059-01-04 with 1059-01-06"

# Or
user_query = "Find all products in HÖGTRYCKSSLANG category"
```

## Next Steps

1. **Add More Functions**: Expand your function library with domain-specific operations
2. **Create More Strategies**: Build strategies for complex multi-step operations
3. **Tune LLM Prompts**: Customize prompts for better domain understanding
4. **Add Vector Search**: Enable semantic search over your documents/data
5. **Implement Caching**: Add caching for frequently accessed data
6. **Add Monitoring**: Track query patterns and performance

## Common Patterns

### Pattern 1: Simple Lookup
```
Query → Goal → Strategy: "DatabaseLookup" → Function: find_by_id → Answer
```

### Pattern 2: Multi-Step Analysis
```
Query → Goal → Strategy: "DetailedAnalysis" → 
  Functions: [fetch_data, analyze, summarize] → Answer
```

### Pattern 3: Comparison
```
Query → Goal → Strategy: "Comparison" → 
  Functions: [get_item_1, get_item_2, compare, format_results] → Answer
```

### Pattern 4: Search and Filter
```
Query → Goal → Strategy: "SearchAndFilter" → 
  Functions: [search, filter_results, rank, format] → Answer
```

## Troubleshooting

**Q: Functions not being found**
- Ensure functions are properly imported in `function_library.py`
- Check function names match exactly in strategy templates

**Q: Database connection errors**
- Verify `DATABASE_PATH` in domain_config.py
- Check database file permissions
- Ensure database schema exists

**Q: LLM returning generic responses**
- Add more specific domain context to prompts
- Include example queries and expected formats
- Tune temperature and max_tokens settings

**Q: Strategies not being selected**
- Make "applicableWhen" descriptions more specific
- Add more example scenarios
- Check LLM can understand the query context

## Support

For more detailed documentation, see:
- `README.md` - Full system documentation
- `docs/graph.md` - Workflow architecture
- `agentic_reasoning/config/domain_config_template.py` - Configuration options
