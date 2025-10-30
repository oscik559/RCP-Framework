#!/usr/bin/env python3
"""
Query database for hoses meeting EN 857 standard
"""

import sqlite3
import json
from pathlib import Path

def find_en857_hoses():
    """Find all hoses that meet EN 857 standard"""
    db_path = Path("data/products.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 SEARCHING FOR HOSES MEETING EN 857 STANDARD")
        print("=" * 60)
        
        # Search in construction details and specifications
        cursor.execute("""
            SELECT 
                p.product_code,
                pf.family_code,
                pf.name as family_name,
                pf.construction_details,
                p.specifications,
                c.name as category_name
            FROM products p
            JOIN product_families pf ON p.family_id = pf.id
            LEFT JOIN categories c ON pf.category_id = c.id
            WHERE 
                (pf.construction_details LIKE '%EN 857%' OR pf.construction_details LIKE '%EN857%')
                OR (p.specifications LIKE '%EN 857%' OR p.specifications LIKE '%EN857%')
                OR (pf.name LIKE '%EN 857%' OR pf.name LIKE '%EN857%')
                OR (pf.description LIKE '%EN 857%' OR pf.description LIKE '%EN857%')
            ORDER BY pf.family_code, p.product_code
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ No hoses found meeting EN 857 standard in the database")
            
            # Let's check what standards are available
            print("\n🔍 Let's see what standards are mentioned in the database...")
            cursor.execute("""
                SELECT DISTINCT
                    pf.construction_details,
                    pf.name,
                    pf.family_code
                FROM product_families pf
                WHERE pf.construction_details IS NOT NULL
                AND (pf.construction_details LIKE '%EN %' OR pf.construction_details LIKE '%ISO %')
                LIMIT 10
            """)
            
            standards_found = cursor.fetchall()
            if standards_found:
                print("\n📋 Standards found in database:")
                for construction, name, family_code in standards_found:
                    try:
                        construction_dict = json.loads(construction) if construction else {}
                        print(f"   Family {family_code} ({name}):")
                        for key, value in construction_dict.items():
                            if 'EN ' in str(value) or 'ISO ' in str(value):
                                print(f"     - {key}: {value}")
                    except:
                        if 'EN ' in str(construction) or 'ISO ' in str(construction):
                            print(f"   Family {family_code} ({name}): {construction}")
            else:
                print("   No EN or ISO standards found in construction details")
        else:
            print(f"✅ Found {len(results)} products meeting EN 857 standard:\n")
            
            current_family = None
            family_products = []
            
            for product_code, family_code, family_name, construction_details, specifications, category_name in results:
                
                if current_family != family_code:
                    # Print previous family if exists
                    if current_family:
                        print_family_info(current_family, family_products)
                    
                    # Start new family
                    current_family = family_code
                    family_products = []
                
                # Parse specifications
                try:
                    specs = json.loads(specifications) if specifications else {}
                except:
                    specs = {}
                
                # Parse construction details
                try:
                    construction = json.loads(construction_details) if construction_details else {}
                except:
                    construction = {}
                
                family_products.append({
                    'product_code': product_code,
                    'family_name': family_name,
                    'specifications': specs,
                    'construction': construction,
                    'category': category_name
                })
            
            # Print last family
            if current_family:
                print_family_info(current_family, family_products)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()

def print_family_info(family_code, products):
    """Print formatted family information"""
    if not products:
        return
    
    first_product = products[0]
    family_name = first_product['family_name']
    category = first_product['category']
    construction = first_product['construction']
    
    print(f"🔧 FAMILY: {family_code} - {family_name}")
    if category:
        print(f"   Category: {category}")
    
    # Show EN 857 related construction details
    if construction:
        print(f"   Construction details (EN 857 related):")
        for key, value in construction.items():
            if 'EN 857' in str(value) or 'EN857' in str(value):
                print(f"     - {key}: {value}")
    
    print(f"   Products ({len(products)} items):")
    for product in products:
        specs_summary = []
        specs = product['specifications']
        
        # Show key specifications
        for spec_key in ['ID mm', 'YD mm', 'Arb.tr. MPa', 'Böjradie mm']:
            if spec_key in specs:
                specs_summary.append(f"{spec_key}: {specs[spec_key]}")
        
        specs_text = " | ".join(specs_summary) if specs_summary else "No specs available"
        print(f"     • {product['product_code']}: {specs_text}")
    
    print()

def main():
    find_en857_hoses()

if __name__ == "__main__":
    main()