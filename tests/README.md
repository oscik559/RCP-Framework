# Tests

This folder contains all test scripts for the agentic reasoning framework.

## Test Suites

### FAQ Testing
- **test_FAQ.py** - Curated test questions from actual company FAQ (30 questions)
  - Tests with real customer questions from Chapter 1 (Hydraulic Hoses)
  - Interactive test runner with multiple modes
  - Categories: specification, comparison, calculation, standards, etc.

### Strategy Testing
- **test_new_strategies.py** - Tests for newly added reasoning strategies
- **test_strategies_with_real_questions.py** - Strategy testing with real FAQ questions
- **test_agent_with_real_questions.py** - Full agent workflow testing

### Component Testing
- **test_location.py** - Tests for PRODUCT LOCATION strategy
- **test_llm_functions.py** - Direct LLM function testing

## Running Tests

### Prerequisites
```bash
# Ensure you're in project root
cd /Users/worktime/Desktop/Project_Hydroscand-Hoses

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH=Layer_2:$PYTHONPATH
```

### Run All FAQ Tests
```bash
python tests/test_FAQ.py
```

### Run Location Tests
```bash
python tests/test_location.py
```

### Run Strategy Tests
```bash
python tests/test_new_strategies.py
```

### Run Layer 2 Framework Tests

#### Unit Tests
```bash
python tests/layer2/unit/test_database.py
python tests/layer2/unit/test_function_library.py
```

#### Integration Tests
```bash
python tests/layer2/integration/test_workflow.py
python tests/layer2/integration/test_strategies.py
```

#### Performance Tests
```bash
python tests/layer2/performance/strategy_comparison_test.py
```

## Test Organization

```
tests/
├── README.md (this file)
│
├── # High-Level Tests (Root level)
├── test_FAQ.py                              # Real FAQ questions (30 tests)
├── test_agent_with_real_questions.py        # Full workflow tests
├── test_llm_functions.py                    # LLM function tests
├── test_location.py                         # Location strategy tests
├── test_new_strategies.py                   # New strategy tests
├── test_strategies_with_real_questions.py   # Strategy validation tests
│
└── layer2/                                  # Framework-Level Tests
    ├── README.md                            # Layer 2 test documentation
    ├── unit/                                # Unit tests
    │   ├── test_database.py
    │   ├── test_function_library.py
    │   └── test_llm_isolation.py
    ├── integration/                         # Integration tests
    │   ├── test_workflow.py
    │   ├── test_strategies.py
    │   └── test_main_fix.py
    ├── performance/                         # Performance tests
    │   ├── strategy_comparison_test.py
    │   ├── strategy_performance_analyzer.py
    │   └── parallel_strategy_analysis.py
    └── utilities/                           # Test utilities
        ├── database_checker.py
        ├── system_analysis.py
        └── query_analyzer.py
```

## Test Coverage

### Strategies Tested
- ✅ SIMPLE LOOKUP
- ✅ ENHANCED LOOKUP
- ✅ PARALLEL ENHANCED LOOKUP
- ✅ VISUAL LAYOUT
- ✅ PRODUCT COMPARISON
- ✅ TECHNICAL CALCULATION
- ✅ STANDARD COMPLIANCE
- ✅ SMART RECOMMENDATION
- ✅ HIERARCHICAL NAVIGATION
- ✅ SPECIFICATION ANALYSIS
- ✅ PRODUCT LOCATION

### Question Categories Tested
- Specification lookups (temperature, pressure, dimensions)
- Product comparisons (2SN vs 2SC, etc.)
- Technical calculations (flow rate, hose sizing)
- Standards compliance (SAE, ISO, EN, DIN)
- Application-specific queries
- Product selection recommendations
- Certifications and compliance
- Special features
- Product location (page numbers)

## Test Results

Each test outputs:
- ✅ Success/failure status
- Strategy selected
- Answer generated
- Execution time
- Error details (if any)

## Adding New Tests

1. Create test file: `tests/test_<feature>.py`
2. Follow existing test structure:
   ```python
   import sys
   sys.path.insert(0, 'Layer_2')
   from agentic_reasoning.config.session_config import get_default_session_state, get_workflow_config
   from agentic_reasoning.logic.state_graph import get_graph
   
   # Your test code
   ```
3. Update this README with test description
4. Ensure test can run from project root

## Troubleshooting

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=Layer_2:$PYTHONPATH
```

### Database Errors
```bash
# Verify database exists
ls -la data/database/*.db
```

### LLM Connection Issues
```bash
# Check Ollama is running
ollama list
```

## Related Documentation

- **Function Documentation**: See `../docs/GENERIC_FUNCTIONS_SUMMARY.md`
- **Strategy Documentation**: See `../docs/NEW_STRATEGIES_SUMMARY.md`
- **Setup Guide**: See `../docs/SETUP.md`
