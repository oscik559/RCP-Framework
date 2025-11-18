"""
Unit tests for configuration loader and settings.
"""

import pytest
from Layer_2_Agentic.config.config_loader import CONFIG


class TestConfigLoader:
    """Test configuration loading and access."""

    def test_config_exists(self):
        """Test that CONFIG is loaded."""
        assert CONFIG is not None

    def test_config_has_required_keys(self):
        """Test that CONFIG has required top-level keys."""
        required_keys = ["harvested_db", "agentic_db", "llms"]
        for key in required_keys:
            assert key in CONFIG, f"Missing required config key: {key}"

    def test_llm_config_structure(self):
        """Test that LLM configuration has proper structure."""
        assert "llms" in CONFIG
        assert isinstance(CONFIG["llms"], dict)
        
        # Check for basic and reasoning LLM configs
        llm_types = CONFIG["llms"]
        assert len(llm_types) > 0, "Should have LLM configurations"

    def test_database_paths_are_strings(self):
        """Test that database paths are strings."""
        assert isinstance(CONFIG["harvested_db"], str)
        assert isinstance(CONFIG["agentic_db"], str)

    def test_config_has_llms_section(self):
        """Test that CONFIG has LLM configuration."""
        assert "llms" in CONFIG
        
        # Check for expected LLM keys
        llms_config = CONFIG["llms"]
        expected_llm_keys = ["basic", "reasoning"]
        
        # At least one of these should exist
        has_expected = any(key in llms_config for key in expected_llm_keys)
        assert has_expected, "Should have at least basic or reasoning LLM config"
