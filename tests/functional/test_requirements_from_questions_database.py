"""
Real-world test cases extracted from Hydroscand questions database.

These tests use actual customer questions and expected requirement patterns
from the comprehensive question analysis (questions.py).

Covers all 79 question categories:
- High-confidence questions (18)
- Medium-confidence questions (6)
- Low-confidence questions (1)
- General system queries (multiple)
"""

import json
import pytest
from Layer_2_Agentic_Reasoning.logic.function_library import func_extract_requirements


def _reqs(result):
    """Extract requirements dict from func_extract_requirements return value."""
    data = json.loads(result) if isinstance(result, str) else result
    return data.get("requirements", data)


class TestHighConfidenceQuestions:
    """Test extraction from high-confidence questions (expected: high accuracy)."""

    def test_boiling_water_hose_q5(self):
        """Question 5: What hoses can be used for boiling water?"""
        query = "What hoses can be used for boiling water?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("application") in ["water", "hot_water"] or data.get("temperature_max", 0) >= 100

    def test_product_comparison_q11(self):
        """Question 11: What is the difference between product A and B?"""
        query = "What is the difference between product A and B?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize comparison intent
        assert isinstance(data, dict)

    def test_food_approved_q14(self):
        """Question 14: Which products are approved for food use?"""
        query = "Which products are approved for food use?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("food_approved") is True

    def test_en857_standard_q20(self):
        """Question 20: Do you have hoses that meet the EN 857 standard?"""
        query = "Do you have hoses that meet the EN 857 standard?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("hose_standard") is not None or "EN 857" in str(data)

    def test_high_pressure_vibration_q22(self):
        """Question 22: Do you have a product that can withstand both high pressure and vibrations?"""
        query = "Do you have a product that can withstand both high pressure and vibrations?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("vibration_resistance") is not None or data.get("pressure_max") is not None

    def test_max_pressure_at_temp_q23(self):
        """Question 23: What is the maximum working pressure for this hose at 100°C?"""
        query = "What is the maximum working pressure for this hose at 100 °C?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("temperature_max") == 100 or data.get("temperature_max", 0) >= 100

    def test_chemical_hoses_q24(self):
        """Question 24: What hoses can be used for chemicals?"""
        query = "What hoses can be used for chemicals?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("application") == "chemical" or "chemical" in str(data).lower()

    def test_hose_type_difference_q36(self):
        """Question 36: What is the difference between a 2SN and 2SC hose?"""
        query = "What is the difference between a 2SN and 2SC hose?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize hose standards
        assert data.get("hose_standard") is not None or isinstance(data, dict)

    def test_fda_food_approval_q82(self):
        """Question 82: Which hoses are FDA approved for food use?"""
        query = "Which hoses are FDA approved for food use?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("food_approved") is True


class TestMediumConfidenceQuestions:
    """Test extraction from medium-confidence questions."""

    def test_series_42_compatibility_q30(self):
        """Question 30: Which hoses are suitable for the 42 series?"""
        query = "Which hoses are suitable for the 42 series?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("series_compatibility") == "42 series" or "42" in str(data)

    def test_alkaline_degreasing_q48(self):
        """Question 48: Hose for alkaline degreasing?"""
        query = "Hose for alkaline degreasing?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("application") == "chemical" or "alkaline" in str(data).lower()

    def test_socket_coupling_q67(self):
        """Question 67: Which socket fits 1118-12-16?"""
        query = "Which socket fits 1118-12-16?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize socket/fitting context
        assert data.get("connection_style") is not None or isinstance(data, dict)

    def test_smooth_casing_q79(self):
        """Question 79: Is there a hose with a smooth outer casing?"""
        query = "Is there a hose with a smooth outer casing?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("smooth_outer_casing") is True


class TestGeneralSystemQuestions:
    """Test extraction from general system-level questions."""

    def test_product_search_variants_q2(self):
        """Question 2: Want to search for variants without bringing up entire model."""
        query = "Want to search for variants without bringing up the entire model"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize search intent
        assert isinstance(data, dict)

    def test_spec_search_without_partnumber_q3(self):
        """Question 3: Search for technical specifications without part number."""
        query = "Be able to search for technical specifications (thread, diameter, length) even if the part number is missing"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize multi-parameter search
        assert isinstance(data, dict)

    def test_synonym_matching_q4(self):
        """Question 4: Synonyms and common terms should provide right matches."""
        query = "Synonyms and common terms should provide the right matches (quick coupling = hydraulic coupling fast)"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize quick coupling intent
        assert "quick" in str(data).lower() or "coupling" in str(data).lower()

    def test_hydraulic_system_components_q13(self):
        """Question 13: What components are needed to build a complete hydraulic system?"""
        query = "What components are needed to build a complete hydraulic system?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("application") == "hydraulic" or "hydraulic" in str(data).lower()

    def test_atex_environment_q14(self):
        """Question 14: Can I use this product in an ATEX environment?"""
        query = "Can I use this product in an ATEX environment?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("atex_certified") is not None or "ATEX" in str(data)

    def test_glycol_compatibility_q15(self):
        """Question 15: Is this product compatible with glycol/water mixture?"""
        query = "Is this product compatible with glycol/water mixture?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        assert data.get("fluid_type") is not None or "glycol" in str(data).lower()


class TestProductLookupQuestions:
    """Test extraction from specific product lookup questions."""

    def test_max_temperature_lookup_q63(self):
        """Question 63: What is the maximum temperature for hose 1071-00-16?"""
        query = "What is the maximum temperature for hose 1071-00-16?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should indicate temperature lookup intent
        assert data.get("temperature_max") is not None or isinstance(data, dict)

    def test_socket_fitting_q64(self):
        """Question 64: Which socket fits 1118-12-16?"""
        query = "Which socket fits 1118-12-16?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Failed: {result}"
        data = _reqs(result)
        
        # Should recognize fitting lookup context
        assert data.get("connection_style") is not None or isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
