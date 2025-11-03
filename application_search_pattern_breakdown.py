"""
APPLICATION_SEARCH_PATTERN - Modular Function Block Breakdown

Breaking down: Semantic Search → Extract Attributes → Search Products → Filter Items → Aggregate Data → Analyze With LLM

Key Differences between Assemble and Aggregate:
- ASSEMBLE: Creates structured temp database with schema discovery (like func_assemble_table)
- AGGREGATE: Performs statistical operations (grouping, counting, averaging) on temp database data

Strategy: Create highly modular function blocks that maintain the agentic interface (params dict) → (success, dict)
and can be reused across multiple strategic patterns.

MODULAR FUNCTION BLOCKS FOR APPLICATION_SEARCH_PATTERN:
"""

# ========================================
# 1. SEMANTIC SEARCH BLOCK
# ========================================

def func_semantic_search(params: dict) -> tuple[bool, dict | str]:
    """
    Semantic search using vector embeddings and natural language understanding.
    
    Enhanced semantic search that finds relevant products/data based on meaning,
    not just keyword matching. Handles use cases, environments, industries, compatibility.
    
    Parameters:
        Input (str): Natural language query (e.g., "hoses for boiling water")
        search_scope (str, optional): Scope limitation ("products", "applications", "both")
        similarity_threshold (float, optional): Minimum similarity score (0.0-1.0, default: 0.7)
        max_results (int, optional): Maximum number of results (default: 20)
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Semantic Results (list): Relevant items with similarity scores
            - Search Query (str): Processed search query
            - Total Matches (int): Number of matches found
            
    Examples:
        "hoses for boiling water" → finds temperature-rated products
        "automotive hydraulic systems" → finds automotive-compatible items
        "food grade applications" → finds food-safe materials
    """
    query = params.get("Input", "").strip()
    search_scope = params.get("search_scope", "both")  # products, applications, both
    similarity_threshold = float(params.get("similarity_threshold", 0.7))
    max_results = int(params.get("max_results", 20))
    
    if not query:
        return (False, "Input query parameter missing")
    
    # Implementation would use vector embeddings for semantic search
    # This is a template showing the expected interface and behavior
    
    semantic_results = [
        {
            "product_family": "High Temperature Hoses",
            "product_code": "HTR-Series",
            "similarity_score": 0.95,
            "match_reason": "temperature resistance for boiling water applications"
        },
        {
            "product_family": "Food Grade Hoses", 
            "product_code": "FGH-Series",
            "similarity_score": 0.82,
            "match_reason": "suitable for hot liquid applications"
        }
    ]
    
    return (True, {
        "Semantic Results": semantic_results,
        "Search Query": query,
        "Total Matches": len(semantic_results)
    })


# ========================================
# 2. EXTRACT ATTRIBUTES BLOCK  
# ========================================

def func_extract_attributes(params: dict) -> tuple[bool, dict | str]:
    """
    Extract structured attributes from semantic search results or product data.
    
    Converts unstructured data into structured attributes for filtering and analysis.
    Uses LLM to identify technical specifications, applications, constraints.
    
    Parameters:
        Semantic Results (list): Results from semantic search
        Input (str): Original user query for context
        attribute_focus (str, optional): Focus areas ("technical", "application", "compatibility")
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Extracted Attributes (list): Structured attribute dicts
            - Attribute Categories (list): Categories found
            - Processing Summary (str): What was extracted
            
    Example Output:
        {
            "temperature_range": "100-150°C",
            "application_type": "hot liquid transfer",
            "material_compatibility": ["water", "steam", "hot oils"],
            "pressure_rating": "up to 10 bar"
        }
    """
    semantic_results = params.get("Semantic Results", [])
    query = params.get("Input", "")
    focus = params.get("attribute_focus", "technical")
    
    if not semantic_results:
        return (False, "Semantic Results parameter missing")
    
    # LLM-powered attribute extraction
    extracted_attributes = []
    
    for result in semantic_results:
        # Extract structured attributes from each result
        attributes = {
            "product_code": result.get("product_code", ""),
            "product_family": result.get("product_family", ""),
            "temperature_capability": "high_temp" if "temperature" in result.get("match_reason", "") else "standard",
            "application_suitability": result.get("match_reason", ""),
            "similarity_score": result.get("similarity_score", 0.0)
        }
        extracted_attributes.append(attributes)
    
    return (True, {
        "Extracted Attributes": extracted_attributes,
        "Attribute Categories": ["temperature_capability", "application_suitability", "product_identification"],
        "Processing Summary": f"Extracted {len(extracted_attributes)} product attribute sets focusing on {focus} aspects"
    })


# ========================================
# 3. SEARCH PRODUCTS BLOCK
# ========================================

def func_search_products(params: dict) -> tuple[bool, dict | str]:
    """
    Search product database using extracted attributes as search criteria.
    
    Translates semantic attributes into database queries to find actual products.
    Supports multiple search strategies: exact match, fuzzy match, range queries.
    
    Parameters:
        Extracted Attributes (list): Structured attributes from extraction
        search_strategy (str, optional): "exact", "fuzzy", "range" (default: "fuzzy")
        include_related (bool, optional): Include related products (default: True)
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Product Results (list): Found products with full specifications  
            - Search Strategy Used (str): Strategy that was applied
            - Match Quality (str): Overall match quality assessment
    """
    attributes = params.get("Extracted Attributes", [])
    strategy = params.get("search_strategy", "fuzzy")
    include_related = params.get("include_related", True)
    
    if not attributes:
        return (False, "Extracted Attributes parameter missing")
    
    # Database search using attributes as criteria
    product_results = []
    
    for attr in attributes:
        product_code = attr.get("product_code", "")
        if product_code:
            # Simulate database lookup
            product = {
                "product_code": product_code,
                "product_name": f"{product_code} - High Temperature Hose",
                "temperature_max": "150°C",
                "pressure_max": "16 bar", 
                "material": "EPDM with textile reinforcement",
                "applications": ["hot water", "steam", "heating systems"],
                "match_quality": "high"
            }
            product_results.append(product)
    
    return (True, {
        "Product Results": product_results,
        "Search Strategy Used": strategy,
        "Match Quality": "high" if len(product_results) > 0 else "low"
    })


# ========================================
# 4. FILTER ITEMS BLOCK
# ========================================

def func_filter_items(params: dict) -> tuple[bool, dict | str]:
    """
    Filter products based on user requirements and constraints.
    
    Applies intelligent filtering using the original query context and extracted requirements.
    Supports multiple filter types: specification-based, application-based, compatibility-based.
    
    Parameters:
        Product Results (list): Products to filter
        Input (str): Original query for filtering context
        filter_criteria (dict, optional): Specific filter criteria
        filter_mode (str, optional): "strict", "permissive", "adaptive" (default: "adaptive")
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Filtered Products (list): Products meeting criteria
            - Filter Applied (dict): What filters were applied  
            - Rejection Reasons (dict): Why products were rejected
    """
    products = params.get("Product Results", [])
    query = params.get("Input", "")
    criteria = params.get("filter_criteria", {})
    mode = params.get("filter_mode", "adaptive")
    
    if not products:
        return (False, "Product Results parameter missing")
    
    # Intelligent filtering based on query context
    filtered_products = []
    filter_applied = {}
    rejection_reasons = {}
    
    # Extract filtering requirements from query
    if "boiling water" in query.lower():
        filter_applied["temperature_min"] = 100
        
    for product in products:
        # Apply temperature filter if needed
        temp_max = product.get("temperature_max", "0°C")
        temp_value = int(temp_max.replace("°C", ""))
        
        if filter_applied.get("temperature_min", 0) <= temp_value:
            filtered_products.append(product)
        else:
            rejection_reasons[product["product_code"]] = f"Temperature {temp_max} insufficient for boiling water"
    
    return (True, {
        "Filtered Products": filtered_products,
        "Filter Applied": filter_applied,
        "Rejection Reasons": rejection_reasons
    })


# ========================================
# 5. AGGREGATE DATA BLOCK
# ========================================

def func_aggregate_data_enhanced(params: dict) -> tuple[bool, dict | str]:
    """
    Enhanced aggregation function that stores data in temp.db for LLM analysis.
    
    This is different from func_assemble_table:
    - ASSEMBLE: Creates structured schema from raw table data  
    - AGGREGATE: Groups and analyzes structured product data statistically
    
    Performs grouping, statistical analysis, and stores results in temp database
    for efficient LLM context building.
    
    Parameters:
        Filtered Products (list): Products to aggregate
        aggregation_type (str, optional): "by_family", "by_application", "by_specification"
        statistics (list, optional): Stats to calculate ["count", "avg", "min", "max"]
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Aggregated Data (str): JSON summary for LLM (matches existing interface)
            - Aggregation Summary (dict): Statistical summary
            - Temp DB Status (str): Database storage status
    """
    from db.connection import get_temp_connection
    import json
    
    products = params.get("Filtered Products", [])
    agg_type = params.get("aggregation_type", "by_family")
    statistics = params.get("statistics", ["count", "avg"])
    
    if not products:
        return (False, "Filtered Products parameter missing")
    
    try:
        # Store in temp database for LLM analysis
        with get_temp_connection() as conn:
            # Clean previous aggregation data
            conn.execute("DROP TABLE IF EXISTS temp_product_aggregation")
            
            # Create aggregation table
            conn.execute("""
                CREATE TABLE temp_product_aggregation (
                    id INTEGER PRIMARY KEY,
                    product_code TEXT,
                    product_name TEXT,
                    product_family TEXT,
                    temperature_max REAL,
                    pressure_max REAL,
                    material TEXT,
                    applications TEXT,
                    aggregation_group TEXT
                )
            """)
            
            # Insert product data
            for product in products:
                # Determine aggregation group
                if agg_type == "by_family":
                    agg_group = product.get("product_code", "").split("-")[0] if "-" in product.get("product_code", "") else "General"
                elif agg_type == "by_application":
                    apps = product.get("applications", [])
                    agg_group = apps[0] if apps else "General"
                else:
                    agg_group = "All Products"
                
                # Parse temperature and pressure values
                temp_str = product.get("temperature_max", "0°C")
                temp_val = float(temp_str.replace("°C", "")) if "°C" in temp_str else 0.0
                
                press_str = product.get("pressure_max", "0 bar")  
                press_val = float(press_str.replace(" bar", "")) if "bar" in press_str else 0.0
                
                conn.execute("""
                    INSERT INTO temp_product_aggregation 
                    (product_code, product_name, product_family, temperature_max, pressure_max, material, applications, aggregation_group)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product.get("product_code", ""),
                    product.get("product_name", ""),
                    product.get("product_code", "").split("-")[0],
                    temp_val,
                    press_val,
                    product.get("material", ""),
                    json.dumps(product.get("applications", [])),
                    agg_group
                ))
            
            # Calculate aggregation statistics
            aggregation_stats = {}
            
            # Group counts
            group_counts = conn.execute("""
                SELECT aggregation_group, COUNT(*) as count
                FROM temp_product_aggregation  
                GROUP BY aggregation_group
            """).fetchall()
            
            for group, count in group_counts:
                if group not in aggregation_stats:
                    aggregation_stats[group] = {}
                aggregation_stats[group]["product_count"] = count
            
            # Temperature statistics if requested
            if "avg" in statistics:
                temp_stats = conn.execute("""
                    SELECT aggregation_group, AVG(temperature_max) as avg_temp, AVG(pressure_max) as avg_pressure
                    FROM temp_product_aggregation
                    GROUP BY aggregation_group
                """).fetchall()
                
                for group, avg_temp, avg_pressure in temp_stats:
                    aggregation_stats[group]["avg_temperature"] = f"{avg_temp:.1f}°C"
                    aggregation_stats[group]["avg_pressure"] = f"{avg_pressure:.1f} bar"
            
            conn.commit()
            
            # Create summary for LLM analysis (matches existing interface)
            llm_summary = {
                "aggregation_type": agg_type,
                "total_products": len(products),
                "groups_created": len(aggregation_stats),
                "statistics_calculated": statistics,
                "group_details": aggregation_stats,
                "database_table": "temp_product_aggregation"
            }
            
            return (True, {
                "Aggregated Data": json.dumps([{"aggregation_summary": llm_summary}]),  # Matches existing interface
                "Aggregation Summary": aggregation_stats,
                "Temp DB Status": f"Stored {len(products)} products in temp_product_aggregation table"
            })
            
    except Exception as e:
        return (False, f"Aggregation error: {str(e)}")


# ========================================
# 6. ANALYZE WITH LLM BLOCK
# ========================================

def func_analyze_with_llm_enhanced(params: dict) -> tuple[bool, dict | str]:
    """
    Enhanced LLM analysis using aggregated data from temp database.
    
    Uses the aggregated data stored in temp.db to provide comprehensive analysis
    with proper context building and statistical insights.
    
    Parameters:
        Input (str): Original user query
        Aggregated Data (str): JSON summary from aggregation step
        analysis_focus (str, optional): "comparison", "recommendation", "specification"
    
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Analysis Output (str): Comprehensive LLM-generated analysis
            - Analysis Type (str): Type of analysis performed
            - Context Used (str): Summary of data context used
    """
    from db.connection import get_temp_connection
    import json
    
    query = params.get("Input", "")
    aggregated_data_str = params.get("Aggregated Data", "")
    analysis_focus = params.get("analysis_focus", "recommendation")
    
    if not query:
        return (False, "Input parameter missing")
    
    if not aggregated_data_str:
        return (False, "Aggregated Data parameter missing")
    
    try:
        # Parse aggregated data
        aggregated_tables = json.loads(aggregated_data_str)
        if not aggregated_tables:
            return (False, "No aggregated data found")
        
        aggregation_info = aggregated_tables[0].get("aggregation_summary", {})
        
        # Query temp database for comprehensive context
        context_parts = []
        with get_temp_connection() as conn:
            # Get product details with grouping
            products = conn.execute("""
                SELECT aggregation_group, COUNT(*) as count,
                       AVG(temperature_max) as avg_temp, AVG(pressure_max) as avg_pressure,
                       GROUP_CONCAT(DISTINCT material) as materials
                FROM temp_product_aggregation
                GROUP BY aggregation_group
            """).fetchall()
            
            context_parts.append("=== PRODUCT ANALYSIS SUMMARY ===")
            context_parts.append(f"Query: {query}")
            context_parts.append(f"Analysis Focus: {analysis_focus}")
            context_parts.append("")
            
            for group, count, avg_temp, avg_pressure, materials in products:
                context_parts.append(f"Product Group: {group}")
                context_parts.append(f"  Products Found: {count}")
                context_parts.append(f"  Average Temperature Rating: {avg_temp:.1f}°C")
                context_parts.append(f"  Average Pressure Rating: {avg_pressure:.1f} bar")
                context_parts.append(f"  Materials: {materials}")
                context_parts.append("")
            
            # Get specific product examples
            examples = conn.execute("""
                SELECT product_code, product_name, temperature_max, pressure_max, material, applications
                FROM temp_product_aggregation
                ORDER BY temperature_max DESC
                LIMIT 5
            """).fetchall()
            
            context_parts.append("=== TOP PRODUCT EXAMPLES ===")
            for code, name, temp, pressure, material, apps_json in examples:
                apps = json.loads(apps_json) if apps_json else []
                context_parts.append(f"• {code}: {name}")
                context_parts.append(f"  Temperature: {temp}°C, Pressure: {pressure} bar")
                context_parts.append(f"  Material: {material}")
                context_parts.append(f"  Applications: {', '.join(apps)}")
                context_parts.append("")
        
        combined_context = "\n".join(context_parts)
        
        # LLM Analysis (simplified for template)
        analysis_output = f"""
Based on your query "{query}", I analyzed the available hydraulic hose products with {analysis_focus} focus:

FINDINGS:
- Found {aggregation_info.get('total_products', 0)} relevant products across {aggregation_info.get('groups_created', 0)} product families
- Products are grouped by {aggregation_info.get('aggregation_type', 'family')} for comprehensive comparison
- Temperature ratings range from standard to high-temperature applications (up to 150°C+)
- Pressure capabilities vary from low-pressure to high-pressure systems (up to 16+ bar)

RECOMMENDATIONS:
For boiling water applications, I recommend focusing on:
1. High-temperature rated hoses (100°C minimum capability)
2. EPDM or equivalent materials for hot water compatibility
3. Adequate pressure rating for your system requirements
4. Food-grade materials if applicable to your use case

The aggregated analysis shows clear product categories suitable for your application requirements.

Context: {len(context_parts)} data points analyzed from temp database aggregation.
"""
        
        return (True, {
            "Analysis Output": analysis_output,
            "Analysis Type": analysis_focus,
            "Context Used": f"Aggregated data from {aggregation_info.get('total_products', 0)} products"
        })
        
    except Exception as e:
        return (False, f"LLM analysis error: {str(e)}")


# ========================================
# INTEGRATION SUMMARY
# ========================================

APPLICATION_SEARCH_PATTERN_FUNCTIONS = {
    "Semantic Search": func_semantic_search,
    "Extract Attributes": func_extract_attributes, 
    "Search Products": func_search_products,
    "Filter Items": func_filter_items,
    "Aggregate Data": func_aggregate_data_enhanced,  # Enhanced version that uses temp.db
    "Analyze With LLM": func_analyze_with_llm_enhanced  # Enhanced version for aggregated data
}

# Strategy Template for templates.py integration
APPLICATION_SEARCH_STRATEGY = (
    "APPLICATION SEARCH PATTERN",
    "application_search", 
    "Semantic search for product applications: find products by use case, environment, industry, or compatibility requirements using intelligent semantic matching.",
    "Semantic Search, Extract Attributes, Search Products, Filter Items, Aggregate Data, Analyze With LLM"
)

print("APPLICATION_SEARCH_PATTERN breakdown complete!")
print(f"\nMODULAR FUNCTION BLOCKS:")
for name, func in APPLICATION_SEARCH_PATTERN_FUNCTIONS.items():
    doc = func.__doc__ or "No description"
    print(f"✓ {name}: {doc.split('.')[0].strip()}")

print(f"\n🔄 REUSABILITY: These {len(APPLICATION_SEARCH_PATTERN_FUNCTIONS)} function blocks can be reused across multiple strategic patterns")
print("📊 TEMP.DB INTEGRATION: Aggregate Data stores structured results for efficient LLM analysis")
print("🧠 AGENTIC INTERFACE: All functions maintain (params: dict) → (success, dict) interface")