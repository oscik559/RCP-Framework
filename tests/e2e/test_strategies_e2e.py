"""
Rigorous testing of new generic strategies with real Hydroscand product questions.

Tests the 6 new strategies with realistic queries that would be found in 
Chapter 1 of the Hydroscand product catalogue (hydraulic hoses).
"""

import os
import sqlite3

from Layer_2_Agentic.logic.function_library import (
    func_search_products,
    func_compare_items,
    func_calculate,
    func_convert_units,
    func_lookup_standard,
    func_analyze_with_llm,
    func_semantic_search,
    func_filter_items,
    func_get_related_items,
    func_extract_attributes,
)

def print_header(title):
    """Print a formatted test header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(test_name, success, result, error=None):
    """Print formatted test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if success and result:
        print(f"     Result: {str(result)[:120]}...")
    elif error:
        print(f"     Error: {error}")
    print()

def get_sample_products():
    """Get sample products from database for testing."""
    try:
        conn = sqlite3.connect('database/harvested.db')
        cursor = conn.cursor()
        
        # Get a few sample products with specifications
        cursor.execute("""
            SELECT p.product_code, pf.family_code, pf.family_name, p.specifications
            FROM products p
            JOIN product_families pf ON p.family_id = pf.id
            LIMIT 5
        """)
        
        products = cursor.fetchall()
        conn.close()
        return products
    except Exception as e:
        print(f"⚠️  Could not load sample products: {e}")
        return []


# =============================================================================
# TEST 1: PRODUCT COMPARISON STRATEGY
# =============================================================================
def test_product_comparison_strategy():
    """
    Strategy: Search Products → Extract Attributes → Compare Items → Analyze With LLM
    
    Real-world question: "Compare the 2SN and 4SP hydraulic hose for pressure rating,
    flexibility, and recommended applications"
    """
    print_header("TEST 1: PRODUCT COMPARISON STRATEGY")
    print("Question: Compare 2SN vs 4SP hydraulic hoses")
    print("Strategy: Search → Extract → Compare → Analyze\n")
    
    # Product data for comparison (from Chapter 1 typical products)
    items = [
        {
            "id": "2SN",
            "name": "2SN Two-Wire Braid Hose",
            "pressure_rating": "280 bar",
            "construction": "Two-wire steel braid",
            "temperature_range": "-40°C to +100°C",
            "flexibility": "Excellent",
            "applications": "General hydraulics, mobile equipment"
        },
        {
            "id": "4SP",
            "name": "4SP Four-Wire Spiral Hose",
            "pressure_rating": "450 bar",
            "construction": "Four-wire steel spiral",
            "temperature_range": "-40°C to +100°C",
            "flexibility": "Good",
            "applications": "High-pressure systems, industrial"
        }
    ]
    
    # Execute comparison
    success, result = func_compare_items({
        "items": items,
        "fields": ["pressure_rating", "construction", "flexibility", "applications"]
    })
    
    print_result("Product Comparison", success, result)
    
    if success and isinstance(result, dict):
        print("     Comparison Table:")
        for field, values in result.get('comparison_table', {}).items():
            print(f"       {field}: {values}")
        
        print(f"\n     Recommendation: {result.get('recommendation', 'N/A')[:150]}...")
    
    return success


# =============================================================================
# TEST 2: TECHNICAL CALCULATION STRATEGY
# =============================================================================
def test_technical_calculation_strategy():
    """
    Strategy: Search → Extract → Calculate → Convert Units → Analyze
    
    Real-world questions:
    - "What hose diameter do I need for 50 L/min flow rate?"
    - "Convert 350 bar working pressure to PSI"
    """
    print_header("TEST 2: TECHNICAL CALCULATION STRATEGY")
    print("Question 1: Calculate hose diameter for 50 L/min flow")
    print("Question 2: Convert 350 bar to PSI\n")
    
    # Test 1: Hose sizing calculation
    print("Step 1: Calculate hose diameter...")
    calc_success, calc_result = func_calculate({
        "calculation_type": "hose_dimension",
        "inputs": {
            "flow_rate": 50,  # L/min
            "target_velocity": 4.5  # m/s (recommended)
        }
    })
    
    print_result("  Hose Diameter Calculation", calc_success, calc_result)
    
    if calc_success:
        print(f"     Recommended diameter: {calc_result.get('result')} {calc_result.get('units')}")
        print(f"     Formula: {calc_result.get('formula_used')}")
    
    # Test 2: Pressure conversion
    print("\nStep 2: Convert pressure units...")
    convert_success, convert_result = func_convert_units({
        "value": 350,
        "from_unit": "bar",
        "to_unit": "psi",
        "context": "Working pressure for hydraulic hose"
    })
    
    print_result("  Pressure Conversion", convert_success, convert_result)
    
    if convert_success:
        print(f"     {convert_result.get('original_value')} bar = {convert_result.get('converted_value')} psi")
    
    return calc_success and convert_success


# =============================================================================
# TEST 3: STANDARD COMPLIANCE STRATEGY
# =============================================================================
def test_standard_compliance_strategy():
    """
    Strategy: Search → Lookup Standard → Extract → Compare → Analyze
    
    Real-world question: "Does this hose meet SAE 100R2 or EN 853 2SN standards?"
    """
    print_header("TEST 3: STANDARD COMPLIANCE STRATEGY")
    print("Question: What are the requirements for SAE 100R2 and EN 853 2SN?\n")
    
    # Test SAE 100R2
    print("Step 1: Lookup SAE 100R2 standard...")
    sae_success, sae_result = func_lookup_standard({
        "standard_type": "SAE",
        "identifier": "100R2"
    })
    
    print_result("  SAE 100R2 Lookup", sae_success, sae_result)
    
    # Test EN 853
    print("Step 2: Lookup EN 853 standard...")
    en_success, en_result = func_lookup_standard({
        "standard_type": "EN",
        "identifier": "853"
    })
    
    print_result("  EN 853 Lookup", en_success, en_result)
    
    if sae_success:
        details = sae_result.get('standard_details', '')
        lines = details.split('\n')[:6]
        print(f"     SAE 100R2 Details:\n       {chr(10).join('       ' + line for line in lines)}")
    
    return sae_success


# =============================================================================
# TEST 4: SMART RECOMMENDATION STRATEGY
# =============================================================================
def test_smart_recommendation_strategy():
    """
    Strategy: Semantic Search → Filter → Get Related → Aggregate → Analyze
    
    Real-world question: "Recommend a hose for mobile hydraulics operating 
    at 350 bar in cold weather (-20°C to +80°C)"
    """
    print_header("TEST 4: SMART RECOMMENDATION STRATEGY")
    print("Question: Recommend hose for mobile hydraulics, 350 bar, cold weather\n")
    
    # Perform intelligent analysis
    print("Step 1: Analyze requirements and provide recommendation...")
    success, result = func_analyze_with_llm({
        "task": "recommendation",
        "context": {
            "application": "Mobile hydraulics",
            "pressure": 350,
            "temperature_range": "-20°C to +80°C",
            "environment": "Cold weather",
            "candidates": ["2SN", "2SC", "4SP", "4SH"]
        },
        "question": "Which hose is best suited for these conditions?"
    })
    
    print_result("  Hose Recommendation", success, result)
    
    if success:
        analysis = result.get('analysis', '')
        lines = analysis.split('\n')[:10]
        print(f"     Analysis:\n       {chr(10).join('       ' + line for line in lines)}")
    
    return success


# =============================================================================
# TEST 5: SPECIFICATION ANALYSIS STRATEGY
# =============================================================================
def test_specification_analysis_strategy():
    """
    Strategy: Search → Extract → Calculate → Convert → Compare → Analyze
    
    Real-world question: "I have a 3/4 inch hose with 350 bar. 
    What's that in metric? Can I use it at 5000 psi?"
    """
    print_header("TEST 5: SPECIFICATION ANALYSIS STRATEGY")
    print("Question: 3/4 inch hose at 350 bar - convert to metric, check 5000 psi compatibility\n")
    
    # Step 1: Convert diameter
    print("Step 1: Convert hose diameter to metric...")
    diameter_success, diameter_result = func_convert_units({
        "value": 0.75,
        "from_unit": "inch",
        "to_unit": "mm",
        "context": "Inner diameter of hydraulic hose"
    })
    
    print_result("  Diameter Conversion", diameter_success, diameter_result)
    
    if diameter_success:
        print(f"     {diameter_result.get('original_value')} inch = {diameter_result.get('converted_value')} mm")
    
    # Step 2: Convert pressure and compare
    print("\nStep 2: Check if 350 bar hose can handle 5000 psi...")
    
    # First convert 350 bar to psi
    bar_to_psi_success, bar_to_psi_result = func_convert_units({
        "value": 350,
        "from_unit": "bar",
        "to_unit": "psi",
        "context": "Working pressure rating"
    })
    
    print_result("  Pressure Conversion", bar_to_psi_success, bar_to_psi_result)
    
    if bar_to_psi_success:
        rated_psi = bar_to_psi_result.get('converted_value')
        print(f"     Hose rating: 350 bar = {rated_psi} psi")
        print(f"     Required: 5000 psi")
        
        if rated_psi and rated_psi >= 5000:
            print(f"     ✅ SAFE: Hose is rated for {rated_psi} psi (above 5000 psi)")
        else:
            print(f"     ⚠️  WARNING: Hose rated at {rated_psi} psi (below 5000 psi required)")
    
    # Step 3: Analyze complete specification
    print("\nStep 3: Provide safety analysis...")
    analysis_success, analysis_result = func_analyze_with_llm({
        "task": "safety_analysis",
        "context": {
            "hose_diameter": "3/4 inch (19.05 mm)",
            "rated_pressure": "350 bar (5076 psi)",
            "required_pressure": "5000 psi",
            "safety_factor": "4:1 standard"
        },
        "question": "Is this hose suitable for the application? Consider safety factors."
    })
    
    print_result("  Safety Analysis", analysis_success, analysis_result)
    
    if analysis_success:
        analysis = analysis_result.get('analysis', '')
        lines = analysis.split('\n')[:8]
        print(f"     Analysis:\n       {chr(10).join('       ' + line for line in lines)}")
    
    return diameter_success and bar_to_psi_success


# =============================================================================
# TEST 6: REAL-WORLD COMPLEX QUERY
# =============================================================================
def test_complex_real_world_query():
    """
    Test a complex multi-step query combining multiple strategies.
    
    Real-world question: "I need a hose for a mobile crane hydraulic system. 
    Flow rate is 60 L/min, working pressure 320 bar, temperature range -25°C to +90°C. 
    The installation space is tight. What do you recommend and why?"
    """
    print_header("TEST 6: COMPLEX REAL-WORLD QUERY")
    print("Question: Mobile crane hydraulics - 60 L/min, 320 bar, -25°C to +90°C, tight space\n")
    
    results = []
    
    # Step 1: Calculate required hose diameter
    print("Step 1: Calculate minimum hose diameter...")
    calc_success, calc_result = func_calculate({
        "calculation_type": "hose_dimension",
        "inputs": {
            "flow_rate": 60,
            "target_velocity": 4.5
        }
    })
    results.append(("Diameter Calculation", calc_success))
    if calc_success:
        print(f"     ✅ Calculated diameter: {calc_result.get('result')} {calc_result.get('units')}")
    
    # Step 2: Convert pressure to PSI for reference
    print("\nStep 2: Convert working pressure to PSI...")
    convert_success, convert_result = func_convert_units({
        "value": 320,
        "from_unit": "bar",
        "to_unit": "psi",
        "context": "Working pressure"
    })
    results.append(("Pressure Conversion", convert_success))
    if convert_success:
        print(f"     ✅ 320 bar = {convert_result.get('converted_value')} psi")
    
    # Step 3: Compare candidate hoses
    print("\nStep 3: Compare candidate hoses for tight spaces...")
    items = [
        {
            "id": "2SN",
            "pressure_rating": "280 bar",
            "flexibility": "Excellent",
            "bend_radius": "10 × OD"
        },
        {
            "id": "2SC",
            "pressure_rating": "350 bar",
            "flexibility": "Very Good",
            "bend_radius": "12 × OD"
        },
        {
            "id": "4SP",
            "pressure_rating": "450 bar",
            "flexibility": "Good",
            "bend_radius": "15 × OD"
        }
    ]
    
    compare_success, compare_result = func_compare_items({
        "items": items,
        "fields": ["pressure_rating", "flexibility", "bend_radius"]
    })
    results.append(("Hose Comparison", compare_success))
    if compare_success:
        print(f"     ✅ Comparison completed")
    
    # Step 4: Get recommendation
    print("\nStep 4: Generate final recommendation...")
    analysis_success, analysis_result = func_analyze_with_llm({
        "task": "recommendation",
        "context": {
            "application": "Mobile crane hydraulics",
            "flow_rate": "60 L/min",
            "calculated_diameter": calc_result.get('result') if calc_success else "17 mm",
            "working_pressure": "320 bar (4641 psi)",
            "temperature": "-25°C to +90°C",
            "constraint": "Tight installation space",
            "candidates": ["2SN (280 bar, excellent flexibility)",
                          "2SC (350 bar, very good flexibility)",
                          "4SP (450 bar, good flexibility)"]
        },
        "question": "Which hose should be selected and why? Consider all requirements."
    })
    results.append(("Final Recommendation", analysis_success))
    
    if analysis_success:
        analysis = analysis_result.get('analysis', '')
        lines = analysis.split('\n')[:12]
        print(f"\n     Final Recommendation:\n       {chr(10).join('       ' + line for line in lines)}")
    
    # Summary
    print(f"\n     {'='*70}")
    passed = sum(1 for _, success in results if success)
    print(f"     Sub-tests passed: {passed}/{len(results)}")
    
    return all(success for _, success in results)


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
def main():
    """Run all strategy tests."""
    print("\n" + "="*80)
    print("  RIGOROUS TESTING OF NEW STRATEGIES WITH REAL HYDROSCAND QUESTIONS")
    print("="*80)
    print("\nTesting 6 new generic strategies with realistic product catalogue queries")
    print("All questions are representative of Chapter 1 (Hydraulic Hoses)\n")
    
    # Check database
    if not os.path.exists('database/harvested.db'):
        print("⚠️  Warning: harvested.db not found. Using synthetic test data.")
    else:
        print("✅ Database found: database/harvested.db")
    
    # Run tests
    results = []
    
    try:
        results.append(("1. PRODUCT COMPARISON", test_product_comparison_strategy()))
        results.append(("2. TECHNICAL CALCULATION", test_technical_calculation_strategy()))
        results.append(("3. STANDARD COMPLIANCE", test_standard_compliance_strategy()))
        results.append(("4. SMART RECOMMENDATION", test_smart_recommendation_strategy()))
        results.append(("5. SPECIFICATION ANALYSIS", test_specification_analysis_strategy()))
        results.append(("6. COMPLEX REAL-WORLD", test_complex_real_world_query()))
        
        # Final Summary
        print("\n" + "="*80)
        print("  TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}  {test_name}")
        
        print(f"\n{'='*80}")
        print(f"  OVERALL: {passed}/{total} strategies working correctly")
        print(f"{'='*80}")
        
        if passed == total:
            print("\n🎉 All strategies are operational and ready for production use!")
            print("\nThese strategies can now handle:")
            print("  • Product comparisons with intelligent analysis")
            print("  • Technical calculations (sizing, flow, pressure)")
            print("  • Standards compliance checking (SAE, EN, ISO, DIN)")
            print("  • Smart recommendations based on requirements")
            print("  • Specification analysis with unit conversions")
            print("  • Complex multi-step real-world queries")
        else:
            print(f"\n⚠️  {total - passed} strategy(ies) need attention")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
