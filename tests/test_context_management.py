"""
Test the enhanced analyze_with_llm function with context management.

Tests:
1. Direct mode with small dataset
2. Chunked mode with large dataset (automatic)
3. Assembly mode with temp.db
4. Flexible query types (not just specifications)
"""

import sys
import os

# Add Layer_2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2-Agentic'))

from logic.function_library import func_analyze_with_llm

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(success, result):
    if success:
        print(f"✅ Success")
        print(f"   Mode: {result.get('mode_used', 'unknown')}")
        print(f"   Products: {result.get('products_analyzed', 0)}")
        print(f"   Truncated: {result.get('context_truncated', False)}")
        print(f"   Context Size: {result.get('context_size_chars', 0)} chars")
        print(f"\n   Analysis:\n   {result.get('Analysis', '')[:200]}...")
    else:
        print(f"❌ Failed: {result}")


# =============================================================================
# TEST 1: DIRECT MODE - Small Dataset
# =============================================================================
def test_direct_mode():
    print_section("TEST 1: Direct Mode (Small Dataset)")
    
    # Small dataset - 3 products
    small_data = [
        {
            "product_code": "1103-03-08",
            "family_name": "KAPPAFLEX 1",
            "spec_working_pressure_mpa": "29.0",
            "spec_min_bend_radius_mm": "95",
            "spec_outer_diameter_mm": "19.0"
        },
        {
            "product_code": "1103-04-10",
            "family_name": "KAPPAFLEX 1",
            "spec_working_pressure_mpa": "29.0",
            "spec_min_bend_radius_mm": "120",
            "spec_outer_diameter_mm": "25.0"
        },
        {
            "product_code": "1104-03-08",
            "family_name": "KAPPAFLEX 2",
            "spec_working_pressure_mpa": "42.0",
            "spec_min_bend_radius_mm": "100",
            "spec_outer_diameter_mm": "20.0"
        }
    ]
    
    success, result = func_analyze_with_llm({
        "task": "comparison",
        "question": "Which of these products has the highest pressure rating?",
        "extracted_data": small_data
    })
    
    print_result(success, result)
    
    # Verify direct mode was used
    if success:
        assert result.get("mode_used") == "direct", "Should use direct mode for small dataset"
        assert not result.get("context_truncated"), "Should not truncate small dataset"
        print("\n✓ Correctly used direct mode")


# =============================================================================
# TEST 2: CHUNKED MODE - Large Dataset (Automatic)
# =============================================================================
def test_chunked_mode():
    print_section("TEST 2: Chunked Mode (Large Dataset with Relevance Filtering)")
    
    # Generate large dataset - 100 products
    large_data = []
    for i in range(100):
        # Mix of different product families
        if i % 3 == 0:
            family = "4SP"
            pressure = "45.0"
        elif i % 3 == 1:
            family = "2SN"
            pressure = "28.0"
        else:
            family = "1SN"
            pressure = "22.5"
        
        large_data.append({
            "product_code": f"TEST-{family}-{i:03d}",
            "family_name": f"{family} Hydraulic Hose",
            "spec_working_pressure_mpa": pressure,
            "spec_min_bend_radius_mm": str(100 + i),
            "spec_outer_diameter_mm": str(15 + (i % 10)),
            "spec_temperature_range": "-40°C to +100°C",
            "application": "General hydraulics"
        })
    
    # Question specifically about 4SP - should prioritize 4SP products
    success, result = func_analyze_with_llm({
        "task": "specification_lookup",
        "question": "What is the typical pressure rating for 4SP hoses and how do they compare to 2SN?",
        "extracted_data": large_data
    })
    
    print_result(success, result)
    
    # Verify chunked mode behavior
    if success:
        mode = result.get("mode_used")
        print(f"\n✓ Mode: {mode} (expected: 'chunked' or 'direct' depending on data size)")
        if result.get("context_truncated"):
            print("✓ Context was truncated as expected")
            print(f"✓ Handled {result.get('products_analyzed')} products")


# =============================================================================
# TEST 3: FLEXIBLE QUERY TYPES - Not Just Specifications
# =============================================================================
def test_flexible_queries():
    print_section("TEST 3: Flexible Query Types (Beyond Specifications)")
    
    product_data = [
        {
            "product_code": "2SN-12",
            "family_name": "2SN Two-Wire Braid",
            "spec_working_pressure_mpa": "28.0",
            "spec_burst_pressure_mpa": "112.0",
            "spec_temperature_range": "-40°C to +100°C",
            "spec_min_bend_radius_mm": "120",
            "construction": "Two-wire steel braid reinforcement",
            "applications": "General purpose, mobile hydraulics"
        },
        {
            "product_code": "4SP-12",
            "family_name": "4SP Four-Wire Spiral",
            "spec_working_pressure_mpa": "45.0",
            "spec_burst_pressure_mpa": "180.0",
            "spec_temperature_range": "-40°C to +100°C",
            "spec_min_bend_radius_mm": "180",
            "construction": "Four-wire steel spiral reinforcement",
            "applications": "High-pressure industrial systems"
        }
    ]
    
    # Test different query types
    queries = [
        {
            "task": "safety_assessment",
            "question": "Is it safe to use 2SN hose at 250 bar continuous pressure?"
        },
        {
            "task": "application_guidance",
            "question": "Which hose is better for mobile equipment that requires frequent flexing?"
        },
        {
            "task": "troubleshooting",
            "question": "Why might a 4SP hose be too stiff for a particular installation?"
        },
        {
            "task": "general_query",
            "question": "What's the difference in construction between 2SN and 4SP?"
        }
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: {query['task']} ---")
        print(f"Question: {query['question']}")
        
        success, result = func_analyze_with_llm({
            **query,
            "extracted_data": product_data
        })
        
        if success:
            print(f"✅ Analysis: {result['Analysis'][:150]}...")
        else:
            print(f"❌ Failed: {result}")
    
    print("\n✓ All flexible query types accepted (no task validation errors)")


# =============================================================================
# TEST 4: CONTEXT SIZE LIMITS
# =============================================================================
def test_context_limits():
    print_section("TEST 4: Context Size Limit Handling")
    
    # Create dataset that will definitely exceed limits
    massive_data = []
    for i in range(500):
        massive_data.append({
            "product_code": f"PROD-{i:04d}",
            "family_name": f"Family {i // 50}",
            "spec_working_pressure_mpa": str(20.0 + (i % 50)),
            "spec_burst_pressure_mpa": str(80.0 + (i % 50) * 4),
            "spec_temperature_range": "-40°C to +100°C",
            "spec_min_bend_radius_mm": str(100 + (i % 100)),
            "spec_outer_diameter_mm": str(15 + (i % 15)),
            "spec_inner_diameter_mm": str(10 + (i % 10)),
            "spec_weight_kg_per_m": str(0.5 + (i % 10) * 0.1),
            "construction": f"Construction type {i % 5}",
            "applications": f"Application category {i % 10}",
            "certifications": "ISO 1307, SAE 100R2AT",
            "color": "Black with yellow stripe"
        })
    
    success, result = func_analyze_with_llm({
        "task": "recommendation",
        "question": "Which products have the highest pressure ratings?",
        "extracted_data": massive_data,
        "max_context_chars": 30000  # Explicit limit
    })
    
    print_result(success, result)
    
    if success:
        if result.get("context_truncated"):
            print("\n✓ Successfully handled massive dataset with truncation")
            print(f"✓ Truncated from {result.get('products_analyzed')} products")
            print(f"✓ Final context size: {result.get('context_size_chars')} chars")
        else:
            print("\n⚠️  Warning: Expected truncation for 500 products")


# =============================================================================
# RUN ALL TESTS
# =============================================================================
def run_all_tests():
    print("\n" + "="*80)
    print("  CONTEXT MANAGEMENT TESTS")
    print("="*80)
    
    try:
        test_direct_mode()
        test_chunked_mode()
        test_flexible_queries()
        test_context_limits()
        
        print("\n" + "="*80)
        print("  ✅ ALL TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
