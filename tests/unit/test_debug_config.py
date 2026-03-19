"""
Unit tests for debug configuration and logging.
"""

import pytest
from Layer_2_Agentic_Reasoning.config.debug_config import debug


class TestDebugConfig:
    """Test debug configuration."""

    def test_debug_object_exists(self):
        """Test that debug object is initialized."""
        assert debug is not None

    def test_debug_has_print_methods(self):
        """Test that debug has required print methods."""
        assert hasattr(debug, 'print_function'), "Missing print_function method"
        assert hasattr(debug, 'print_error'), "Missing print_error method"
        assert hasattr(debug, 'print_workflow'), "Missing print_workflow method"

    def test_debug_methods_callable(self):
        """Test that debug methods are callable."""
        assert callable(debug.print_function), "print_function should be callable"
        assert callable(debug.print_error), "print_error should be callable"
        assert callable(debug.print_workflow), "print_workflow should be callable"

    def test_debug_print_function_no_error(self):
        """Test that print_function executes without error."""
        try:
            debug.print_function("Test message")
        except Exception as e:
            pytest.fail(f"print_function raised exception: {e}")

    def test_debug_print_workflow_no_error(self):
        """Test that print_workflow executes without error."""
        try:
            debug.print_workflow("Test workflow message")
        except Exception as e:
            pytest.fail(f"print_workflow raised exception: {e}")

    def test_debug_print_error_no_error(self):
        """Test that print_error executes without error."""
        try:
            debug.print_error("Test error")
        except Exception as e:
            pytest.fail(f"print_error raised exception: {e}")

    def test_debug_all_print_methods(self):
        """Test that all print methods are available."""
        methods = [
            'print_workflow', 'print_goal', 'print_strategy', 'print_function',
            'print_params', 'print_outputs', 'print_merge', 'print_debug',
            'print_completion', 'print_validation', 'print_system', 'print_error'
        ]
        
        for method_name in methods:
            assert hasattr(debug, method_name), f"Missing method: {method_name}"
            assert callable(getattr(debug, method_name)), f"{method_name} should be callable"
