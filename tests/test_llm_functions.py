#!/usr/bin/env python3
"""
Test script for LLM-powered generic functions.

Tests the 6 functions that use LLM:
1. func_analyze_with_llm
2. func_convert_units
3. func_calculate
4. func_lookup_standard
5. func_extract_attributes
6. func_compare_items
"""

import sys
import os

# Add Layer_2_Agentic to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2_Agentic'))

from agentic_reasoning.logic.function_library import (
    func_convert_units,
    func_calculate,
    func_lookup_standard,
    func_extract_attributes,
    func_compare_items,
    func_analyze_with_llm
)

def print_result(test_name, success, result):
    """Pretty print test results."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"\nResult:")
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 200:
                print(f"  {key}: {value[:200]}...")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  {result}")
    print(f"{'='*70}\n")


def test_convert_units():
    """Test LLM-powered unit conversion."""
    print("\n" + "🔄 TESTING UNIT CONVERSION".center(70, "="))
    
    # Test 1: Standard conversion
    params = {
        "value": 350,
        "from_unit": "bar",
        "to_unit": "psi",
        "context": "hydraulic hose pressure rating"
    }
    success, result = func_convert_units(params)
    print_result("Convert 350 bar to PSI", success, result)
    
    # Test 2: Fractional inch to mm
    params = {
        "value": 0.75,
        "from_unit": "inch",
        "to_unit": "mm",
        "context": "hose diameter"
    }
    success, result = func_convert_units(params)
    print_result("Convert 3/4 inch to mm", success, result)


def test_calculate():
    """Test LLM-powered calculations."""
    print("\n" + "🧮 TESTING CALCULATIONS".center(70, "="))
    
    # Test: Hose dimension calculation
    params = {
        "calculation_type": "hose_dimension",
        "inputs": {
            "flow_rate": 50,  # L/min
            "target_velocity": 4.5  # m/s
        }
    }
    success, result = func_calculate(params)
    print_result("Calculate hose diameter for 50 L/min flow", success, result)


def test_lookup_standard():
    """Test LLM-powered standard lookup."""
    print("\n" + "📖 TESTING STANDARD LOOKUP".center(70, "="))
    
    params = {
        "standard_type": "SAE",
        "identifier": "100R2"
    }
    success, result = func_lookup_standard(params)
    print_result("Look up SAE 100R2 standard", success, result)


def test_compare_items():
    """Test LLM-powered product comparison."""
    print("\n" + "⚖️  TESTING PRODUCT COMPARISON".center(70, "="))
    
    params = {
        "items": [
            {
                "name": "2SN Hose",
                "pressure": 280,
                "construction": "Two wire braid",
                "temperature": "-40 to +100°C",
                "flexibility": "Good"
            },
            {
                "name": "4SP Hose",
                "pressure": 450,
                "construction": "Four wire spiral",
                "temperature": "-40 to +100°C",
                "flexibility": "Moderate"
            }
        ],
        "fields": ["pressure", "construction", "flexibility"]
    }
    success, result = func_compare_items(params)
    print_result("Compare 2SN vs 4SP hose", success, result)


def test_analyze_with_llm():
    """Test general LLM analysis."""
    print("\n" + "🤖 TESTING LLM ANALYSIS".center(70, "="))
    
    params = {
        "task": "recommendation",
        "context": {
            "application": "Mobile hydraulics",
            "pressure": 350,
            "temperature": "-20 to +80°C",
            "options": ["2SN", "2SC", "4SP"]
        },
        "question": "Which hose type is best for this mobile hydraulics application?"
    }
    success, result = func_analyze_with_llm(params)
    print_result("Recommend hose for mobile hydraulics", success, result)


def main():
    """Run all tests."""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + "  TESTING LLM-POWERED GENERIC FUNCTIONS  ".center(68) + "║")
    print("╚" + "═"*68 + "╝")
    
    tests = [
        ("Unit Conversion", test_convert_units),
        ("Calculations", test_calculate),
        ("Standard Lookup", test_lookup_standard),
        ("Product Comparison", test_compare_items),
        ("LLM Analysis", test_analyze_with_llm),
    ]
    
    print(f"\nRunning {len(tests)} test suites...\n")
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {str(e)}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + "  TESTING COMPLETE  ".center(68) + "║")
    print("╚" + "═"*68 + "╝\n")


if __name__ == "__main__":
    main()
