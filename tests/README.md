# Test Suite for Hydroscand Produktbok

## Overview

This directory contains all tests for the Hydroscand Product Catalog system, organized into logical categories based on testing scope and strategy.

## Directory Structure

```
tests/
├── unit/                          # Unit tests - individual components
│   ├── test_database.py          # Database schema and connections
│   ├── test_function_library.py  # Function library execution
│   ├── test_llm_isolation.py     # LLM context isolation checks
│   └── test_llm_retry.py         # LLM retry logic
│
├── integration/                   # Integration tests - multi-component workflows
│   ├── test_workflow.py          # Workflow node execution
│   ├── test_context_management.py# Context and session management
│   ├── test_system_setup.py      # Complete system initialization
│   └── test_location_query.py    # Location-based queries
│
├── functional/                    # Functional tests - feature validation
│   ├── test_generic_functions.py # Core generic functions (search, filter, compare, calculate, convert)
│   ├── test_llm_functions.py     # LLM-powered functions (analyze, lookup, extract attributes)
│   └── test_strategies_basic.py  # Strategy implementations with sample scenarios
│
├── e2e/                          # End-to-end tests - real-world scenarios
│   ├── test_strategies_e2e.py    # Strategies with real product questions
│   └── test_agent_e2e.py         # Full agent workflow with realistic queries
│
└── performance/                   # Performance benchmarking
    └── test_parallel_strategy.py # Parallel strategy execution analysis
```

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Verify individual components work correctly in isolation

- **test_database.py**: Validates database schema, connections, and tri-state success fields
- **test_function_library.py**: Tests individual function execution and parameter validation
- **test_llm_isolation.py**: Ensures LLM calls don't contaminate context between invocations
- **test_llm_retry.py**: Tests LLM retry logic and error handling

### Integration Tests (`integration/`)
**Purpose**: Verify components work together correctly

- **test_workflow.py**: Tests workflow node interactions
- **test_context_management.py**: Validates session context handling
- **test_system_setup.py**: End-to-end system initialization verification
- **test_location_query.py**: Tests location-based product queries

### Functional Tests (`functional/`)
**Purpose**: Validate specific features work as designed

- **test_generic_functions.py**: Tests core functions with sample data
- **test_llm_functions.py**: Tests LLM-powered functions
- **test_strategies_basic.py**: Tests strategy implementations with sample scenarios

### End-to-End Tests (`e2e/`)
**Purpose**: Validate complete workflows with real product data

- **test_strategies_e2e.py**: Strategies with real Hydroscand product questions
- **test_agent_e2e.py**: Full agent execution with realistic queries

### Performance Tests (`performance/`)
**Purpose**: Benchmark and analyze performance characteristics

- **test_parallel_strategy.py**: Analyzes parallel strategy execution performance

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Category
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/
pytest tests/e2e/
pytest tests/performance/
```

### Run Specific Test File
```bash
pytest tests/unit/test_database.py
pytest tests/functional/test_generic_functions.py
```

### Run with Coverage
```bash
pytest tests/ --cov=Layer_2_Agentic
```

## Adding New Tests

### Guidelines

1. **Choose the Right Category**:
   - `unit/` - Isolated component tests
   - `integration/` - Multi-component workflows
   - `functional/` - Feature validation with sample data
   - `e2e/` - Real scenarios with real data
   - `performance/` - Benchmarking

2. **Naming Conventions**:
   - File: `test_<feature_name>.py`
   - Function: `def test_<scenario>()`
   - Class: `class Test<Component>()`

3. **File Organization**: Store all tests in appropriate subdirectory for reuse and discoverability

## VS Code Testing Integration

Tests are automatically discovered and can be run from the Testing tab:

1. Open Testing tab (left sidebar)
2. Tests organized by category
3. Click to run individual tests or entire categories
4. View results with pass/fail indicators

Configuration in `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestPath": "pytest"
}
```

## Statistics

**Total Tests**: 63+  
**Categories**: 5 (Unit, Integration, Functional, E2E, Performance)  
**Test Files**: 14

## 📊 Results Data

### Test Results

- `failed_queries.txt` - List of failed queries for analysis

## File Organization Standards

# Tests Directory

This directory contains all tests for the Project_Hydroscand-Hoses system.

## 📁 Structure

```
tests/
├── test_*.py              # High-level integration tests
├── unit/                  # Unit tests for individual components
├── integration/           # Integration tests for workflows
├── performance/           # Performance and benchmarking tests
└── utilities/             # Testing utilities and diagnostics
```

## Usage Examples

## 🚀 Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Categories
```bash
# High-level integration tests
pytest tests/test_*.py

# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Performance tests
pytest tests/performance/
```

### Run Individual Test Files
```bash
# System verification
python tests/test_layer2_complete.py

# Function tests
python tests/test_new_functions.py

# Ollama diagnostics
python tests/diagnose_ollama.py
```

### Strategy Performance Analysis

```bash
python tests/strategy_performance_analyzer.py
```

### Database Inspection

```bash
python tests/check_db.py
```

### Debug Specific Issues

```bash
python tests/debug_lookup_analysis.py
```

All tools are designed for reuse during development and troubleshooting.


