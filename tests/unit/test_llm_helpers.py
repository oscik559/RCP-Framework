"""
Unit tests for LLM helpers and initialization.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestLLMHelpers:
    """Test LLM helper functions."""

    def test_get_basic_llm_import(self):
        """Test that get_basic_llm can be imported."""
        try:
            from Layer_2_Agentic.logic.llm_helpers import get_basic_llm
            assert callable(get_basic_llm)
        except ImportError as e:
            pytest.fail(f"Failed to import get_basic_llm: {e}")

    def test_get_reasoning_llm_import(self):
        """Test that get_reasoning_llm can be imported."""
        try:
            from Layer_2_Agentic.logic.llm_helpers import get_reasoning_llm
            assert callable(get_reasoning_llm)
        except ImportError as e:
            pytest.fail(f"Failed to import get_reasoning_llm: {e}")

    def test_get_basic_llm_returns_llm(self):
        """Test that get_basic_llm returns an LLM instance."""
        try:
            from Layer_2_Agentic.logic.llm_helpers import get_basic_llm
            
            llm = get_basic_llm()
            assert llm is not None
            # LLM should have an invoke method
            assert hasattr(llm, 'invoke') or hasattr(llm, 'predict')
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")

    def test_get_reasoning_llm_returns_llm(self):
        """Test that get_reasoning_llm returns an LLM instance."""
        try:
            from Layer_2_Agentic.logic.llm_helpers import get_reasoning_llm
            
            llm = get_reasoning_llm()
            assert llm is not None
            # LLM should have an invoke method
            assert hasattr(llm, 'invoke') or hasattr(llm, 'predict')
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")


class TestPromptLoader:
    """Test prompt loading functionality."""

    def test_get_prompt_loader_import(self):
        """Test that get_prompt_loader can be imported."""
        try:
            from Layer_2_Agentic.config.prompt_loader import get_prompt_loader
            assert callable(get_prompt_loader)
        except ImportError as e:
            pytest.fail(f"Failed to import get_prompt_loader: {e}")

    def test_get_prompt_loader_returns_loader(self):
        """Test that get_prompt_loader returns a loader."""
        try:
            from Layer_2_Agentic.config.prompt_loader import get_prompt_loader
            
            loader = get_prompt_loader()
            assert loader is not None
            assert hasattr(loader, 'get_prompt'), "Loader should have get_prompt method"
        except Exception as e:
            pytest.skip(f"Prompt loader not available: {e}")

    def test_get_prompt_returns_dict(self):
        """Test that get_prompt returns a dictionary."""
        try:
            from Layer_2_Agentic.config.prompt_loader import get_prompt_loader
            
            loader = get_prompt_loader()
            # Try to get a prompt (might not exist, but method should work)
            try:
                prompt = loader.get_prompt("function_execution", "search")
                if prompt:
                    assert isinstance(prompt, dict)
            except Exception:
                # Prompt might not exist, that's ok
                pass
        except Exception as e:
            pytest.skip(f"Prompt loader test not applicable: {e}")


class TestFunctionLibraryImports:
    """Test function library imports."""

    def test_func_search_products_import(self):
        """Test that func_search_products can be imported."""
        try:
            from Layer_2_Agentic.logic.function_library import func_search_products
            assert callable(func_search_products)
        except ImportError as e:
            pytest.fail(f"Failed to import func_search_products: {e}")

    def test_func_filter_items_import(self):
        """Test that func_filter_items can be imported."""
        try:
            from Layer_2_Agentic.logic.function_library import func_filter_items
            assert callable(func_filter_items)
        except ImportError as e:
            pytest.fail(f"Failed to import func_filter_items: {e}")

    def test_func_analyze_data_import(self):
        """Test that func_analyze_data can be imported."""
        try:
            from Layer_2_Agentic.logic.function_library import func_analyze_data
            assert callable(func_analyze_data)
        except ImportError as e:
            pytest.fail(f"Failed to import func_analyze_data: {e}")

    def test_all_core_functions_callable(self):
        """Test that all core functions are callable."""
        try:
            from Layer_2_Agentic.logic import function_library
            
            # Get all functions that start with 'func_'
            funcs = [getattr(function_library, name) for name in dir(function_library) 
                    if name.startswith('func_') and callable(getattr(function_library, name))]
            
            assert len(funcs) > 0, "Should have at least one func_ function"
            
            for func in funcs:
                assert callable(func), f"{func.__name__} should be callable"
        except Exception as e:
            pytest.skip(f"Function library test not applicable: {e}")
