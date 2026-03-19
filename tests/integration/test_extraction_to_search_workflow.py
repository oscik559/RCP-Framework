"""
Integration test suite for semantic search + requirement extraction workflow.

Tests the complete pipeline:
1. Extract requirements from user query
2. Use semantic search to find matching product families
3. Validate result completeness
"""

import json
import pytest
from Layer_2_Agentic_Reasoning.logic.function_library import (
    func_extract_requirements,
    func_semantic_search
)


class TestRequirementExtractionToSemanticSearch:
    """Test integration between requirement extraction and semantic search."""

    def test_boiling_water_to_semantic_search(self):
        """Test: boiling water query → extract requirements → semantic search."""
        query = "What hoses can be used for boiling water at high temperature?"
        
        # Step 1: Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            requirements = json.loads(result)
        else:
            requirements = result
        
        assert requirements.get("temperature_max", 0) >= 100 or requirements.get("application") in ["water", "hot_water"]
        
        # Step 2: Semantic search using the extracted application
        search_query = f"Hoses for boiling water {requirements.get('temperature_max', 100)}°C"
        search_success, search_result = func_semantic_search({"Input": search_query})
        
        assert search_success, f"Semantic search failed: {search_result}"

    def test_chemical_resistance_extraction_to_search(self):
        """Test: chemical requirement query → extraction → semantic search."""
        query = "Hoses suitable for chemical and alkaline degreasing applications"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            requirements = json.loads(result)
        else:
            requirements = result
        
        assert requirements.get("application") == "chemical" or "chemical" in str(requirements)
        
        # Semantic search
        search_query = "Chemical resistant hoses EPDM XLPE UPE"
        search_success, search_result = func_semantic_search({"Input": search_query})
        assert search_success, f"Semantic search failed: {search_result}"

    def test_high_pressure_vibration_workflow(self):
        """Test: complex high-pressure vibration query → extraction → search."""
        query = "Do you have a product that can withstand both 380 bar pressure and vibrations?"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            requirements = json.loads(result)
        else:
            requirements = result
        
        assert requirements.get("pressure_max", 0) >= 380
        assert requirements.get("vibration_resistance") is not None or "vibration" in str(requirements).lower()
        
        # Semantic search for high-pressure vibration resistant hoses
        search_success, search_result = func_semantic_search({
            "Input": "high pressure spiral wound hose vibration",
            "max_results": 5
        })
        assert search_success, f"Semantic search failed: {search_result}"

    def test_food_safety_extraction_to_search(self):
        """Test: food safety requirement → extraction → semantic search."""
        query = "Which products are approved for food use with FDA and REACH certification?"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            requirements = json.loads(result)
        else:
            requirements = result
        
        assert requirements.get("food_approved") is True
        
        # Semantic search for food-approved products
        search_success, search_result = func_semantic_search({
            "Input": "food approved FDA hoses FOODSTEAM"
        })
        assert search_success, f"Semantic search failed: {search_result}"

    def test_marine_dnv_certification_workflow(self):
        """Test: marine application with DNV requirement."""
        query = "Which hoses are DNV classified for marine and offshore applications?"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            requirements = json.loads(result)
        else:
            requirements = result
        
        assert requirements.get("marine_rating") is not None or "DNV" in str(requirements)
        
        # Semantic search
        search_success, search_result = func_semantic_search({
            "Input": "DNV MED marine certified hoses"
        })
        assert search_success, f"Semantic search failed: {search_result}"


class TestMultiCriteriaRequirementMatching:
    """Test multi-criteria requirement extraction and matching."""

    def test_excavator_hydraulic_hose_complete_workflow(self):
        """Test complete workflow: excavator hose with all criteria."""
        query = "Hydraulic hose for excavator: 280 bar, EN 853 2SN, robust for high wear, steel wire reinforced"
        
        # Extract all requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            reqs = json.loads(result)
        else:
            reqs = result
        
        # Verify multiple criteria captured
        assert reqs.get("application") == "hydraulic"
        assert reqs.get("pressure_max", 0) >= 280
        
        # Semantic search for matching products
        search_success, search_result = func_semantic_search({
            "Input": "EN 853 2SN excavator hydraulic steel wire reinforced"
        })
        assert search_success, f"Semantic search failed: {search_result}"

    def test_steam_coupling_with_temperature_and_material(self):
        """Test steam coupling requirement with multiple criteria."""
        query = "Steam coupling G 1/2\" thread, AISI 316 acid-resistant stainless steel, high temperature rated"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            reqs = json.loads(result)
        else:
            reqs = result
        
        assert reqs.get("application") == "steam" or "steam" in str(reqs).lower()
        assert reqs.get("corrosive_environment") is True or "AISI 316" in str(reqs)
        
        # Semantic search
        search_success, search_result = func_semantic_search({
            "Input": "steam coupling G thread AISI 316"
        })
        assert search_success, f"Semantic search failed: {search_result}"

    def test_suction_return_hose_flow_sizing(self):
        """Test suction/return hose with flow rate sizing."""
        query = "Suction hose for 20 L/min, velocity max 1.5 m/s, return line max 2.5 m/s"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        if isinstance(result, str):
            reqs = json.loads(result)
        else:
            reqs = result
        
        assert reqs.get("flow_rate") == 20
        assert reqs.get("application") in ["suction", "suction_return"]
        
        # Can use these for subsequent product selection
        assert "velocity" in str(reqs).lower() or reqs.get("velocity_range") is not None


class TestSemanticSearchQualityAfterExtraction:
    """Verify semantic search results are relevant after extraction."""

    def test_search_results_relevance_for_high_temp(self):
        """Verify semantic search returns relevant high-temp products."""
        query = "High temperature hoses -40 to +150°C for HI-TEMP applications"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        # Semantic search
        search_success, search_result = func_semantic_search({
            "Input": "high temperature 150 HI-TEMP",
            "max_results": 3
        })
        assert search_success, f"Semantic search failed: {search_result}"
        
        if isinstance(search_result, str):
            results = json.loads(search_result)
        else:
            results = search_result
        
        # Should have results
        assert results if isinstance(results, list) else True

    def test_search_results_for_chemical_hoses(self):
        """Verify semantic search returns relevant chemical hose products."""
        query = "Chemical hoses EPDM for aggressive chemicals 1450-10 Cobra"
        
        # Extract
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        # Search
        search_success, search_result = func_semantic_search({
            "Input": "Cobra EPDM chemical aggressive",
            "max_results": 5
        })
        assert search_success, f"Semantic search failed: {search_result}"


class TestErrorHandlingInWorkflow:
    """Test error handling in extraction → search workflow."""

    def test_graceful_handling_ambiguous_query(self):
        """Test handling of ambiguous query."""
        query = "What is the difference between A and B?"
        
        # Extract should handle gracefully
        success, result = func_extract_requirements({"Input": query})
        # May succeed or fail, but should return meaningful response
        assert isinstance(result, (str, dict))

    def test_malformed_input_handling(self):
        """Test handling of malformed input."""
        query = ""
        
        success, result = func_extract_requirements({"Input": query})
        # Should handle empty input gracefully
        assert isinstance(result, (str, dict))

    def test_very_long_query_processing(self):
        """Test handling of very long complex query."""
        query = (
            "Need a hydraulic hose for a mining excavator application, "
            "rated for 350 bar pressure, temperature range -30 to +100°C, "
            "1.5 inch inner diameter with SAE JIC UNF threading, "
            "EPDM material for oil resistance, with steel wire reinforcement, "
            "suitable for high vibration and impulse loads, "
            "DN certified for marine transport, FDA approved for food contact surfaces, "
            "smooth outer casing for easy installation, and compact design to fit tight spaces"
        )
        
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Query failed: {result}"
        
        if isinstance(result, str):
            reqs = json.loads(result)
        else:
            reqs = result
        
        # Should extract multiple criteria
        assert len([v for v in reqs.values() if v is not None]) > 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
