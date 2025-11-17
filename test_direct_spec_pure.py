#!/usr/bin/env python3
"""Test DIRECT_SPEC_LOOKUP without LLM - pure extraction and lookup"""

import sqlite3
import json
import re

print("=" * 70)
print("STRATEGY TEST: DIRECT_SPEC_LOOKUP (No LLM)")
print("=" * 70)
print()

# ========== STEP 1: Extract Product Number (pure regex) ==========
print("STEP 1: Extract Product Number (Pure Regex)")
print("-" * 70)
query = "What is the Slang ID for the product 4221-24-08?"
print(f"Query: {query}")
print()

# Simple regex to find product code pattern
product_code_pattern = r'\d{4}-\d{2}-\d{2}'
match = re.search(product_code_pattern, query)

if match:
    product_code = match.group(0)
    print(f"✓ Extracted Product Code: {product_code}")
else:
    print("❌ No product code found")
    exit(1)

print()

# ========== STEP 2: Query Database ==========
print("STEP 2: Query Database (Fetch Product Specifications)")
print("-" * 70)

db_path = "database/harvested.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query_sql = "SELECT product_code, specifications FROM products WHERE product_code = ?"
    cursor.execute(query_sql, (product_code,))
    result = cursor.fetchone()
    
    if result:
        product_code_db, specs_json = result
        specs = json.loads(specs_json)
        
        print(f"✓ Found product: {product_code_db}")
        print(f"✓ Specifications:")
        for key, value in specs.items():
            print(f"    {key}: {value}")
        print()
    else:
        print(f"❌ Product not found: {product_code}")
        exit(1)
        
    conn.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")
    exit(1)

# ========== STEP 3: Extract Target Attribute ==========
print("STEP 3: Extract Target Attribute from Query")
print("-" * 70)

query_lower = query.lower()

# Map attribute queries to actual spec keys
attribute_map = {
    "slang id": "Slang ID",
    "ganga": "Gänga",
    "ror": "Rör",
    "typ": "Typ",
    "artikelnr": "Artikelnr.",
}

target_attribute = None
for query_term, spec_key in attribute_map.items():
    if query_term in query_lower:
        target_attribute = spec_key
        break

if target_attribute:
    value = specs.get(target_attribute, "NOT FOUND")
    print(f"✓ Target Attribute: {target_attribute}")
    print(f"✓ Value: {value}")
    print()
    
    # ========== FINAL ANSWER ==========
    print("=" * 70)
    print("FINAL ANSWER:")
    print("=" * 70)
    print(f"The {target_attribute} for product {product_code} is: {value}")
    print()
    print("✅ STRATEGY COMPLETE!")
else:
    print("❌ Could not determine target attribute from query")

print()
print("=" * 70)
