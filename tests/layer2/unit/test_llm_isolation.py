#!/usr/bin/env python3
"""Test LLM context persistence issue."""

import logging
from agentic_reasoning.logic.function_library import func_extract_product_number

logging.basicConfig(level=logging.DEBUG)

def test_llm_isolation():
    """Test if LLM maintains context between different calls."""
    
    print("=== LLM CONTEXT ISOLATION TEST ===")
    
    # Test 1: Extract from query with C0001686-61701
    params1 = {"Input": "what is the shell size of the product C0001686-61701?"}
    success1, result1 = func_extract_product_number(params1)
    print(f"Test 1 Input: {params1['Input']}")
    print(f"Test 1 Output: {result1}")
    print()
    
    # Test 2: Extract from completely different query  
    params2 = {"Input": "Which LOCATOR and CRIMPTOOL number is used for RPT 235 4309/350?"}
    success2, result2 = func_extract_product_number(params2)
    print(f"Test 2 Input: {params2['Input']}")
    print(f"Test 2 Output: {result2}")
    print()
    
    # Test 3: Extract from another different query
    params3 = {"Input": "What keying is used for part number C0000658-11040?"}
    success3, result3 = func_extract_product_number(params3)
    print(f"Test 3 Input: {params3['Input']}")
    print(f"Test 3 Output: {result3}")
    print()
    
    # Check for contamination
    if "C0001686-61701" in result2.get("Keyword Output", ""):
        print("🚨 CONTAMINATION DETECTED: Test 2 contains C0001686-61701 but it's not in the query!")
    else:
        print("✅ Test 2 clean - no contamination")
        
    if "C0001686-61701" in result3.get("Keyword Output", ""):
        print("🚨 CONTAMINATION DETECTED: Test 3 contains C0001686-61701 but it's not in the query!")
    else:
        print("✅ Test 3 clean - no contamination")

if __name__ == "__main__":
    test_llm_isolation()


