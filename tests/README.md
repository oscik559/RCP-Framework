# Test Suite for RCP Framework

## Overview

This directory contains all tests for the RCP Framework, organized into 4 logical categories based on testing scope and strategy.

## Directory Structure

```
tests/
├── unit/                          # Unit tests - individual components (8 files, 40+ tests)
│   ├── test_database.py          # Database schema and connections
│   ├── test_config_loader.py     # Configuration management
│   ├── test_debug_config.py      # Debug configuration
│   ├── test_db_connections.py    # Database connection management
│   ├── test_llm_helpers.py       # LLM helpers and initialization
│   ├── test_llm_retry.py         # LLM retry logic
│   ├── test_workflow_config.py   # Workflow and strategy configuration
│   └── test_utilities.py         # Project structure and environment
│
├── integration/                   # Integration tests - multi-component workflows (4 files, 15+ tests)
│   ├── test_context_management.py# Context and session management
│   ├── test_system_setup.py      # Complete system initialization
│   ├── test_llm_functions.py     # LLM-powered functions
│   └── test_strategies_basic.py  # Strategy implementations
│
├── e2e/                          # End-to-end tests - real-world scenarios (2 files, 10+ tests)
│   ├── test_strategies_e2e.py    # Strategies with real product questions
│   └── test_agent_e2e.py         # Full agent workflow with realistic queries
│
└── utilities/                    # Utility/diagnostic scripts (not pytest tests)
    ├── database_checker.py       # Database verification
    ├── inspect_agentic_db.py    # Inspect agentic database
    ├── diagnose_ollama.py       # Diagnose Ollama setup
    └── [other diagnostic tools]
```

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Verify individual components work correctly in isolation

**8 test files with 40+ test cases:**
- Database schema, connections, and operations
- Configuration loading and validation
- Debug configuration management
- Database connection context managers
- LLM initialization and helpers
- LLM retry logic and error handling
- Workflow and strategy configuration
- Project structure and environment validation

### Integration Tests (`integration/`)
**Purpose**: Verify components work together correctly

**4 test files with 15+ test cases:**
- Context and session management
- Complete system initialization
- LLM-powered functions with real data
- Strategy implementations with sample scenarios

### End-to-End Tests (`e2e/`)
**Purpose**: Validate complete workflows with real product data

**2 test files with 10+ test cases:**
- Strategies with real Hydroscand questions
- Full agent execution with realistic queries

### Utility Tests (`utilities/`)
**Purpose**: Diagnostic and verification scripts (not standard pytest tests)

These are standalone Python scripts for:
- Database inspection and verification
- Ollama diagnostics
- System analysis
- Query analysis

Run individually: `python tests/utilities/script_name.py`

## Running Tests

### Prerequisite
Install test tooling first:

```bash
python -m pip install -e ".[test]"
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Category
```bash
pytest tests/unit/           # All unit tests
pytest tests/integration/    # All integration tests
pytest tests/e2e/            # All end-to-end tests
```

### Run Specific Test File
```bash
pytest tests/unit/test_config_loader.py
pytest tests/integration/test_system_setup.py
```

### Run Specific Test
```bash
pytest tests/unit/test_utilities.py::TestPathUtilities::test_project_root_detection
```

### Run with Coverage
```bash
pytest tests/ --cov=Layer_2_Agentic_Reasoning --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v --tb=short
```

### Run Utility Diagnostics
```bash
python tests/utilities/database_checker.py
python tests/utilities/diagnose_ollama.py
python tests/utilities/inspect_agentic_db.py
```

## Adding New Tests

### Unit Test Guidelines

1. **When to Create Unit Tests**:
   - Testing individual functions in isolation
   - Configuration loading and validation
   - Database connection management
   - Import validation
   - Helper function behavior

2. **Naming Conventions**:
   - File: `test_<component_name>.py`
   - Class: `class Test<Component>:`
   - Function: `def test_<specific_scenario>():`

3. **Template**:
```python
"""
Unit tests for [component].
"""

import pytest

class TestComponentName:
    """Test [component] functionality."""

    def test_feature_works(self):
        """Test that feature works as expected."""
        # Arrange
        input_data = ...
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result is not None

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Integration Test Guidelines

1. **When to Create Integration Tests**:
   - Testing workflows spanning multiple components
   - Database + LLM interaction
   - Multi-stage processing pipelines
   - System setup verification

2. **Location**: `tests/integration/test_<workflow_name>.py`

### End-to-End Test Guidelines

1. **When to Create E2E Tests**:
   - Testing complete workflows with real data
   - Real product questions from Hydroscand catalog
   - Full strategy execution

2. **Location**: `tests/e2e/test_<scenario_name>.py`

## VS Code Testing Integration

Tests are automatically discovered and shown in the Testing tab:

1. Open Testing tab (left sidebar)
2. Click "Run All" or run individual tests
3. View results with pass/fail indicators

Configuration in `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests", "-v"],
    "python.testing.unittestEnabled": false
}
```

## Test Statistics

| Category | Files | Tests |
|----------|-------|-------|
| Unit | 8 | 40+ |
| Integration | 4 | 15+ |
| E2E | 2 | 10+ |
| **Total** | **14** | **65+** |

## Common Issues & Solutions

### Import Errors
- Ensure running from project root: `cd RCP-Framework`
- Check Layer_2_Agentic_Reasoning imports use correct module name (not `agentic_reasoning`)

### Database Errors
- Verify `database/harvested.db` exists
- Run: `python database/db_utils.py --verify`

### LLM/Ollama Errors
- Check Ollama is running: `ollama serve`
- Check model is pulled: `ollama list`

### Connection Timeouts
- Increase timeout in `Layer_2_Agentic_Reasoning/db/connection.py`
- Check database file permissions

## File Organization Standards

All tests should be stored in `tests/` directory for reuse and discoverability:

✅ **Correct**: `tests/unit/test_config_loader.py`  
❌ **Wrong**: `test_config_loader.py` in project root

## References

- [pytest documentation](https://docs.pytest.org/)
- [Layer_2_Agentic_Reasoning module structure](../Layer_2_Agentic_Reasoning/)
- [Copilot instructions for test creation](../.github/copilot-instructions.md)
