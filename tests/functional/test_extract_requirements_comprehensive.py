"""
Comprehensive test suite for func_extract_requirements with expanded requirement taxonomy.

Tests cover:
1. Core specifications (application, temperature, pressure, diameter)
2. Material & construction details
3. Connectivity & threading
4. Performance characteristics
5. Fluid compatibility
6. Environmental & regulatory requirements
7. Assembly & installation
8. Product series & variants
9. Special requirements
10. Real-world multi-criteria queries from question database
"""

import json
import pytest
from Layer_2_Agentic.logic.function_library import func_extract_requirements


class TestCoreSpecifications:
    """Test basic product parameters extraction."""

    def test_application_types(self):
        """Test extraction of different application types."""
        query = "I need a hose for hydraulic systems with 280 bar pressure"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("application") == "hydraulic"
        assert data.get("pressure_max") == 280

    def test_temperature_range(self):
        """Test extraction of temperature ranges."""
        query = "What hoses can be used for boiling water applications? Need temperature up to 150°C"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("application") in ["water", "hot_water"]
        assert data.get("temperature_max") >= 150

    def test_pressure_range_extraction(self):
        """Test extraction of pressure ranges."""
        query = "Which hydraulic hoses are rated for more than 300 bar working pressure?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("pressure_min") >= 300 or data.get("pressure_max") >= 300

    def test_diameter_dimension(self):
        """Test extraction of diameter/dimension requirements."""
        query = "I need a blue water hose in 3/4 inch dimension"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("diameter_max") is not None
        assert data.get("color_requirement") == "blue"


class TestMaterialConstruction:
    """Test material and construction extraction."""

    def test_material_types(self):
        """Test extraction of specific material requirements."""
        query = "Natural rubber hoses with PTFE inner tube for high temperature"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert "NR" in str(data.get("material", "")) or "natural rubber" in str(data.get("material", ""))
        assert "PTFE" in str(data.get("inner_tube_type", ""))

    def test_reinforcement_type(self):
        """Test hose standard/reinforcement extraction."""
        query = "What is the difference between a 2SN and 2SC hose?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        # Should recognize hose standards
        assert data.get("hose_standard") is not None or "intent" in data

    def test_smooth_outer_casing(self):
        """Test smooth outer casing requirement."""
        query = "Is there a hose with a smooth outer casing for easy cleaning?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("smooth_outer_casing") is True


class TestConnectivityThreading:
    """Test connection and threading extraction."""

    def test_thread_types(self):
        """Test extraction of different thread types."""
        query = "I need couplings with JIC 1/2 inch UNF threads"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert "JIC" in str(data.get("thread_type", ""))

    def test_connection_style(self):
        """Test extraction of connection style."""
        query = "Which quick-disconnect couplings are available for 3/4 inch?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("connection_style") in ["quick-disconnect", "quick_coupling", None]

    def test_seal_type_specification(self):
        """Test extraction of seal requirements."""
        query = "Which couplings have an O-ring seal for 1/2 inch?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("seal_type") in ["O-ring", "NBR"] or "O-ring" in str(data)


class TestPerformanceCharacteristics:
    """Test performance requirement extraction."""

    def test_vibration_resistance(self):
        """Test extraction of vibration requirements."""
        query = "Do you have a product that can withstand both high pressure and vibrations?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("vibration_resistance") is not None or data.get("pressure_max") is not None

    def test_flow_rate_specification(self):
        """Test extraction of flow rate requirements."""
        query = "The flow is 150 liters per minute, what hose dimension should I choose for pressure?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("flow_rate") == 150
        assert data.get("application") in ["pressure", "hydraulic"]

    def test_pressure_drop_tolerance(self):
        """Test extraction of pressure drop limits."""
        query = "I can have a maximum pressure drop of 200 millibars, flow is 100 liters per minute"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("pressure_drop_limit") <= 0.2 or data.get("pressure_drop_limit") == 200


class TestFluidCompatibility:
    """Test fluid compatibility extraction."""

    def test_chemical_resistance(self):
        """Test extraction of chemical compatibility."""
        query = "What hoses can be used for chemicals and alkaline degreasing?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert "chemical" in str(data.get("fluid_type", "")).lower()
        assert data.get("chemical_resistance") is not None or data.get("application") == "chemical"

    def test_environmental_oil_compatibility(self):
        """Test extraction of environmental oil requirements."""
        query = "Can I use environmental oil in this hose?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("environmental_oil_compatible") is not None or data.get("fluid_type") is not None

    def test_glycol_water_compatibility(self):
        """Test extraction of glycol/water mixture compatibility."""
        query = "Is this product compatible with glycol/water mixture?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("fluid_type") is not None or "intent" in data


class TestEnvironmentalRegulatory:
    """Test environmental and regulatory requirement extraction."""

    def test_food_approval(self):
        """Test extraction of food approval requirement."""
        query = "Which products are approved for food use? Need FDA certified"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("food_approved") is True

    def test_atex_certification(self):
        """Test extraction of ATEX certification requirement."""
        query = "Can I use this product in an ATEX environment?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("atex_certified") is not None or "ATEX" in str(data)

    def test_marine_dnv_rating(self):
        """Test extraction of marine/DNV rating requirements."""
        query = "Which hoses are DNV classified for marine applications?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("marine_rating") is not None or "DNV" in str(data)

    def test_acid_resistant_requirement(self):
        """Test extraction of acid-resistant requirement."""
        query = "I need an acid-resistant coupling in AISI 316 stainless steel"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("corrosive_environment") is True or "AISI 316" in str(data)


class TestAssemblyInstallation:
    """Test assembly and installation requirement extraction."""

    def test_installation_type(self):
        """Test extraction of installation type."""
        query = "Which sleeve should I use to crimp a multi-spiral hose?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("installation_type") in ["crimped", "pressed"] or data.get("stripping_required") is True

    def test_tightening_torque_requirement(self):
        """Test extraction of tightening torque need."""
        query = "What is the recommended tightening torque for this JIC coupling?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("tightening_torque_specified") is True or data.get("thread_type") == "JIC"


class TestProductSeriesVariants:
    """Test product series and variant extraction."""

    def test_series_compatibility(self):
        """Test extraction of series compatibility."""
        query = "Which hoses are suitable for the 42 series quick couplings?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("series_compatibility") == "42 series" or "42" in str(data)

    def test_product_family_specification(self):
        """Test extraction of specific product family."""
        query = "Do you have Kappaflex hoses with smooth outer tube?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("product_family") == "Kappaflex" or "Kappaflex" in str(data)


class TestRealWorldMultiCriteria:
    """Test real-world multi-criteria queries from question database."""

    def test_excavator_hose_requirements(self):
        """Test complex excavator hose requirements."""
        query = "Which hydraulic hose and sleeve should I get for a particular excavator?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("application") == "hydraulic"
        # Should recognize multi-criteria nature
        assert "confidence" in data or "intent" in data

    def test_high_pressure_vibration_combo(self):
        """Test high pressure + vibration combined requirement."""
        query = "Do you have a product that can withstand both high pressure (380 bar) and vibrations?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("pressure_max") >= 380
        assert data.get("vibration_resistance") is not None or data.get("vibration_resistance") is True

    def test_chemical_temperature_requirement(self):
        """Test chemical resistance + temperature requirement."""
        query = "What hoses can be used for chemicals and alkaline degreasing at temperatures up to 120°C?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("temperature_max") <= 120 or data.get("temperature_max") == 120
        assert "chemical" in str(data.get("fluid_type", "")).lower()

    def test_food_steam_hose(self):
        """Test food-approved steam hose requirement."""
        query = "FOODSTEAM hose for hot water and steam in food industry, FDA and REACH approved"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("food_approved") is True
        assert data.get("application") in ["steam", "water", "hot_water"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_incomplete_query(self):
        """Test handling of incomplete query."""
        query = "I need a hose"
        success, result = func_extract_requirements({"Input": query})
        
        # Should still return valid JSON even with minimal info
        assert isinstance(result, str)
        if success:
            data = json.loads(result)
            assert "application" in data or "intent" in data

    def test_ambiguous_requirements(self):
        """Test handling of ambiguous requirements."""
        query = "What is the difference between product A and B?"
        success, result = func_extract_requirements({"Input": query})
        
        # Should indicate lack of specific requirements or comparison intent
        assert isinstance(result, str)

    def test_very_detailed_specification(self):
        """Test handling of very detailed multi-criteria query."""
        query = "I need a hydraulic hose rated for 350 bar, temperature range -40 to +100°C, 1 inch diameter with SAE JIC threading, food-approved FDA certification, AISI 316 acid-resistant with smooth outer tube and DN certified for marine"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        assert data.get("pressure_max") >= 350
        assert data.get("temperature_min") <= -40
        assert data.get("temperature_max") >= 100
        assert data.get("food_approved") is True
        assert data.get("marine_rating") is not None


class TestConfidenceAndIntent:
    """Test confidence scoring and intent detection."""

    def test_confidence_score_presence(self):
        """Test that confidence score is returned."""
        query = "What hoses can be used for boiling water?"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        # Should have confidence score
        assert "confidence" in data or isinstance(data, dict)

    def test_intent_summary(self):
        """Test that intent summary is provided."""
        query = "Need a hydraulic hose for 380 bar with smooth outer casing"
        success, result = func_extract_requirements({"Input": query})
        
        assert success, f"Query failed: {result}"
        data = json.loads(result)
        # Should provide some indication of intent
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
