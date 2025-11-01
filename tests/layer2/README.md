# Tests and Analysis Tools

This folder contains all testing, debugging, and analysis utilities for the SAAB Agentic Reasoning System.

## 📋 Test Files

### Core Tests

- `test_function_library.py` - Unit tests for function library
- `test_database.py` - Database functionality tests  
- `test_workflow.py` - Workflow execution tests
- `conftest.py` - PyTest configuration

### JSON Handling Tests

- `test_json_fix.py` - JSON parsing and cleaning tests
- `test_simple_fix.py` - Simplified JSON fix validation  
- `simple_json_fix.py` - JSON fixing utility functions

### Strategy Testing

- `test_strategies.py` - Individual strategy testing
- `test_parallel_strategy.py` - Parallel strategy validation
- `comprehensive_parallel_testing.py` - Full parallel strategy analysis
- `strategy_performance_analyzer.py` - Performance comparison across strategies

### Integration Tests

- `test_llm_isolation.py` - LLM isolation testing
- `parallel_strategy_analysis.py` - Parallel execution analysis
- `parallel_strategy_success_summary.py` - Success rate summaries

## 🔍 Analysis Tools

### Database Analysis

- `check_db.py` - Database structure and content inspection
- `check_db_schema.py` - Database schema validation
- `check_query.py` - Query validation and testing
- `check_failed_tests.py` - Failed test analysis
- `check_test_structure.py` - Test structure validation
- `analyze_data.py` - Data analysis and exploration

### System Analysis  

- `system_analysis.py` - Overall system performance analysis
- `comprehensive_analysis.py` - Cross-component analysis

### Query Analysis

- `get_failed_queries.py` - Failed query extraction and analysis

## 📊 Results Data

### Test Results

- `failed_queries.txt` - List of failed queries for analysis

## File Organization Standards

All test and analysis files are organized in this `tests/` folder according to these conventions:

- `test_*.py` - Unit and integration tests
- `check_*.py` - Validation and check utilities  
- `*_analysis.py` - Performance and system analysis tools
- Remove temporary/debug files after use
- Keep reusable utilities, remove one-time scripts

## Usage Examples

### Run All Tests

```bash
python -m pytest tests/
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


