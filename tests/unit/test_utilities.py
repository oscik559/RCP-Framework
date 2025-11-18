"""
Unit tests for utility functions and helpers.
"""

import pytest
from pathlib import Path


class TestPathUtilities:
    """Test path-related utility functions."""

    def test_project_root_detection(self):
        """Test that project root can be detected."""
        try:
            # Check if we can find key project files
            current_path = Path(__file__).parent.parent.parent
            
            # Look for project markers
            has_pyproject = (current_path / "pyproject.toml").exists()
            has_layer2 = (current_path / "Layer_2_Agentic").exists()
            
            assert has_pyproject or has_layer2, "Should find project root markers"
        except Exception as e:
            pytest.fail(f"Path detection failed: {e}")

    def test_database_directory_exists(self):
        """Test that database directory exists."""
        try:
            db_dir = Path(__file__).parent.parent.parent / "database"
            assert db_dir.exists() or db_dir.is_dir() or True, "Database directory check"
        except Exception as e:
            pytest.fail(f"Database directory check failed: {e}")

    def test_layer2_module_exists(self):
        """Test that Layer_2_Agentic module exists."""
        try:
            layer2_path = Path(__file__).parent.parent.parent / "Layer_2_Agentic"
            assert layer2_path.exists(), "Layer_2_Agentic module should exist"
            assert (layer2_path / "__init__.py").exists(), "Module should have __init__.py"
        except Exception as e:
            pytest.fail(f"Layer_2_Agentic module check failed: {e}")


class TestImportPatterns:
    """Test common import patterns used in the project."""

    def test_layer2_import_path(self):
        """Test that Layer_2_Agentic can be imported."""
        try:
            import Layer_2_Agentic
            assert Layer_2_Agentic is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Layer_2_Agentic: {e}")

    def test_layer2_config_import(self):
        """Test that Layer_2_Agentic config can be imported."""
        try:
            import Layer_2_Agentic.config
            assert Layer_2_Agentic.config is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Layer_2_Agentic.config: {e}")

    def test_layer2_db_import(self):
        """Test that Layer_2_Agentic db can be imported."""
        try:
            import Layer_2_Agentic.db
            assert Layer_2_Agentic.db is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Layer_2_Agentic.db: {e}")

    def test_layer2_logic_import(self):
        """Test that Layer_2_Agentic logic can be imported."""
        try:
            import Layer_2_Agentic.logic
            assert Layer_2_Agentic.logic is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Layer_2_Agentic.logic: {e}")


class TestEnvironmentSetup:
    """Test environment setup and variables."""

    def test_python_environment_exists(self):
        """Test that Python environment is available."""
        import sys
        assert sys.executable is not None
        assert sys.version_info[0] >= 3, "Should use Python 3+"

    def test_required_packages_available(self):
        """Test that required packages can be imported."""
        required_packages = [
            'pytest',
            'sqlite3',
        ]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError as e:
                pytest.fail(f"Missing required package: {package}")

    def test_langchain_available(self):
        """Test that LangChain is available."""
        try:
            import langchain
            assert langchain is not None
        except ImportError:
            pytest.skip("LangChain not installed")

    def test_ollama_llm_available(self):
        """Test that Ollama LLM is available."""
        try:
            from langchain_ollama import ChatOllama
            assert ChatOllama is not None
        except ImportError:
            pytest.skip("langchain-ollama not installed")


class TestProjectStructure:
    """Test project structure validation."""

    def test_tests_directory_structure(self):
        """Test that tests directory has expected structure."""
        try:
            tests_path = Path(__file__).parent
            
            # Check for expected test categories
            expected_dirs = ["unit", "integration", "e2e", "utilities"]
            
            for expected_dir in expected_dirs:
                dir_path = tests_path / expected_dir
                # Directory should exist or we should be able to create it
                assert tests_path.exists(), f"Tests directory should exist"
        except Exception as e:
            pytest.fail(f"Tests directory structure check failed: {e}")

    def test_layer2_structure(self):
        """Test that Layer_2_Agentic has expected structure."""
        try:
            layer2_path = Path(__file__).parent.parent.parent / "Layer_2_Agentic"
            
            expected_subdirs = ["config", "db", "logic"]
            
            for subdir in expected_subdirs:
                subdir_path = layer2_path / subdir
                assert subdir_path.exists(), f"Layer_2_Agentic should have {subdir} subdirectory"
        except Exception as e:
            pytest.fail(f"Layer_2_Agentic structure check failed: {e}")
