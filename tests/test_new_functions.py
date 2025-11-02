"""
Test script for new generic Hydroscand functions.

Tests the 5 priority functions:
- func_search_products
- func_filter_items
- func_compare_items
- func_calculate
- func_convert_units
"""

import sys
import sys
from pathlib import Path

# Add Layer_2-Agentic to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Layer_2-Agentic"))

from logic.function_library import (
    func_search_products,
    func_filter_items,
    func_compare_items,
    func_calculate,
    func_convert_units,
)


def test_search_products():
    """Test Q7: What hoses can be used for boiling water?"""
    print("\n" + "="*80)
    print("TEST 1: Search Products - High Temperature Hoses (Q7)")
    print("="*80)
    
    params = {
        "database_path": "../../data/database/harvested.db",
        "keywords": "hydraulic hose",
        "specs": {
            "min_temp": 100  # Boiling water temperature
        },
        "limit": 10
    }
    
    success, result = func_search_products(params)
    print(f"\n✓ Success: {success}")
    
    if success:
        print(f"✓ Found {result['Count']} products")
        if result['Count'] > 0:
            print(f"\nFirst product:")
            product = result['Products'][0]
            print(f"  - Code: {product.get('product_code')}")
            print(f"  - Name: {product.get('product_name')}")
            print(f"  - Family: {product.get('family_name')}")
            print(f"  - Description: {product.get('description', '')[:100]}...")
    else:
        print(f"✗ Error: {result}")


def test_filter_items():
    """Test filtering products by pressure rating"""
    print("\n" + "="*80)
    print("TEST 2: Filter Items - High Pressure Products")
    print("="*80)
    
    # Create sample items
    items = [
        {"product_code": "H1", "name": "Hose A", "pressure": 250, "diameter": 12},
        {"product_code": "H2", "name": "Hose B", "pressure": 350, "diameter": 16},
        {"product_code": "H3", "name": "Hose C", "pressure": 150, "diameter": 10},
        {"product_code": "H4", "name": "Hose D", "pressure": 400, "diameter": 19},
    ]
    
    params = {
        "items": items,
        "filters": {
            "pressure": {">": 200}  # Only high pressure hoses
        },
        "filter_mode": "AND"
    }
    
    success, result = func_filter_items(params)
    print(f"\n✓ Success: {success}")
    
    if success:
        print(f"✓ Filtered to {result['Count']} items (from {len(items)})")
        for item in result['FilteredItems']:
            print(f"  - {item['name']}: {item['pressure']} bar, {item['diameter']} mm")
    else:
        print(f"✗ Error: {result}")


def test_compare_items():
    """Test Q: What is difference between 2SN and 2SC hose?"""
    print("\n" + "="*80)
    print("TEST 3: Compare Items - 2SN vs 2SC Hoses (Q from test)")
    print("="*80)
    
    items = [
        {
            "product_code": "2SN",
            "name": "2SN Hydraulic Hose",
            "construction": "Two wire braid",
            "pressure_rating": 280,
            "temperature_range": "-40 to +100°C",
            "application": "Medium pressure hydraulics"
        },
        {
            "product_code": "2SC",
            "name": "2SC Hydraulic Hose", 
            "construction": "Two wire braid compact",
            "pressure_rating": 350,
            "temperature_range": "-40 to +100°C",
            "application": "High pressure compact systems"
        }
    ]
    
    params = {
        "items": items,
        "fields": ["construction", "pressure_rating", "temperature_range", "application"],
        "item_labels": ["2SN Hose", "2SC Hose"]
    }
    
    success, result = func_compare_items(params)
    print(f"\n✓ Success: {success}")
    
    if success:
        print(f"\n✓ Comparison Summary:")
        print(f"  - Total fields: {result['Summary']['TotalFields']}")
        print(f"  - Similar: {result['Summary']['SimilarFields']}")
        print(f"  - Different: {result['Summary']['DifferentFields']}")
        print(f"\n✓ Different fields: {', '.join(result['Summary']['DifferentFieldsList'])}")
        
        print(f"\n✓ Field-by-field comparison:")
        for field, values in result['Comparison'].items():
            print(f"\n  {field}:")
            for label, value in values.items():
                print(f"    {label}: {value}")
    else:
        print(f"✗ Error: {result}")


def test_calculate():
    """Test Q49: 150 l/min flow, what hose dimension?"""
    print("\n" + "="*80)
    print("TEST 4: Calculate - Hose Dimension for 150 L/min (Q49)")
    print("="*80)
    
    params = {
        "calc_type": "hose_dimension",
        "params": {
            "flow_rate": 150,  # L/min
            "velocity": 4.5    # m/s (standard for pressure lines)
        }
    }
    
    success, result = func_calculate(params)
    print(f"\n✓ Success: {success}")
    
    if success:
        print(f"✓ Calculated diameter: {result['CalculatedDiameter_mm']} mm")
        print(f"✓ Recommended standard size: {result['RecommendedSize_mm']} mm")
        print(f"✓ For flow rate: {result['FlowRate_Lmin']} L/min")
        print(f"✓ At velocity: {result['TargetVelocity_ms']} m/s")
    else:
        print(f"✗ Error: {result}")


def test_convert_units():
    """Test Q39: How many millimeters is 1/8"?"""
    print("\n" + "="*80)
    print("TEST 5: Convert Units - 1/8 inch to mm (Q39)")
    print("="*80)
    
    params = {
        "value": 1/8,
        "from_unit": "inch",
        "to_unit": "mm"
    }
    
    success, result = func_convert_units(params)
    print(f"\n✓ Success: {success}")
    
    if success:
        print(f"✓ {result['OriginalValue']} {result['FromUnit']} = {result['ConvertedValue']} {result['ToUnit']}")
    else:
        print(f"✗ Error: {result}")
    
    # Test pressure conversion
    print("\n" + "-"*80)
    print("BONUS: Convert pressure - 250 bar to psi")
    print("-"*80)
    
    params2 = {
        "value": 250,
        "from_unit": "bar",
        "to_unit": "psi"
    }
    
    success2, result2 = func_convert_units(params2)
    print(f"\n✓ Success: {success2}")
    
    if success2:
        print(f"✓ {result2['OriginalValue']} {result2['FromUnit']} = {result2['ConvertedValue']} {result2['ToUnit']}")
    else:
        print(f"✗ Error: {result2}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TESTING NEW GENERIC HYDROSCAND FUNCTIONS")
    print("="*80)
    print("Testing 5 priority functions with real Hydroscand test questions")
    
    try:
        test_search_products()
        test_filter_items()
        test_compare_items()
        test_calculate()
        test_convert_units()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\nNext steps:")
        print("1. Repopulate templates database: python logic/templates.py")
        print("2. Test with web app: python app/web_app.py")
        print("3. Create new strategies using these functions")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
