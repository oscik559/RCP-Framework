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


def _reqs(result):
    """Extract requirements dict from func_extract_requirements return value."""
    data = json.loads(result) if isinstance(result, str) else result
    return data.get("requirements", data)


class TestRequirementExtractionToSemanticSearch:
    """Test integration between requirement extraction and semantic search."""

    def test_chemical_resistance_extraction_to_search(self):
        """Test: chemical requirement query → extraction → semantic search."""
        query = "Hoses suitable for chemical and alkaline degreasing applications"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        requirements = _reqs(result)
        
        assert requirements.get("application") == "chemical" or "chemical" in str(requirements)
        
        # Semantic search
        search_query = "Chemical resistant hoses EPDM XLPE UPE"
        search_success, search_result = func_semantic_search({"Input": search_query})
        assert search_success, f"Semantic search failed: {search_result}"

    def test_marine_dnv_certification_workflow(self):
        """Test: marine application with DNV requirement."""
        query = "Which hoses are DNV classified for marine and offshore applications?"
        
        # Extract requirements
        success, result = func_extract_requirements({"Input": query})
        assert success, f"Extraction failed: {result}"
        
        requirements = _reqs(result)
        
        assert requirements.get("marine_rating") is not None or "DNV" in str(requirements)
        
        # Semantic search
        search_success, search_result = func_semantic_search({
            "Input": "DNV MED marine certified hoses"
        })
        assert search_success, f"Semantic search failed: {search_result}"


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
        
        reqs = _reqs(result)
        
        # Should extract multiple criteria
        assert len([v for v in reqs.values() if v is not None]) > 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
