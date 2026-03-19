# Copilot Instructions for RCP-Framework

## Overview
This project is a three-layer intelligent system for extracting, reasoning about, and querying industrial product data from PDF catalogs. It is organized into three main layers:
- **Layer 1: Extraction** (PDF → Tables → Products → Database)
- **Layer 2: Agentic Reasoning** (Goal → Strategy → Function, with LLM and workflow orchestration)
- **Layer 3: Application** (Web UI, APIs, progress tracking)

## Key Architectural Patterns
- **Centralized Database**: All product, family, and knowledge data is stored in `database/harvested.db` (see `database/db_utils.py` and `database/harvested_schema.sql`).
- **Layer Separation**: Extraction, reasoning, and UI logic are strictly separated. Package installed via `pip install -e .` for clean imports.
- **Agentic Reasoning**: Layer 2 uses a Goal → Strategy → Function pattern, with reusable function libraries and strategy templates. See `Layer_2_Agentic/logic/function_library.py` and `Layer_2_Agentic/db/templates.py`.
- **VLM Integration**: Vision Language Models (Ollama + Qwen) are used for table and product extraction in Layer 1. Model and API configuration is passed via CLI args.
- **Testing**: All tests are organized in `tests/` by category (unit, integration, functional, e2e, performance). Use `pytest tests/` for full suite. See `tests/README.md` for guidelines.

## Developer Workflows
- **Extract Data**: Run Layer 1 scripts to convert PDF pages to PNG, detect tables, and extract products. Example:
  ```pwsh
  python Layer_1a_Extraction/1_pdf_to_png.py Layer_1a_Extraction/High-Pressure_Hose.pdf
  python Layer_1a_Extraction/3_detect_tables.py
  python Layer_1a_Extraction/4_extract_product.py Layer_1a_Extraction/High-Pressure_Hose.pdf --page 31
  ```
- **Query Data**: Use Layer 2 (main.py) for CLI queries, or Layer 3 (web_app.py) for web UI. Example:
  ```pwsh
  python main.py
  cd Layer_3_Application
  python web_app.py
  ```
- **Database Access**: Use `database/db_utils.py` for verification and schema management. Example:
  ```pwsh
  python database/db_utils.py --verify
  ```
- **Testing**: Run `pytest tests/` or individual test files for diagnostics.

## Test Organization & Guidelines

### Test Directory Structure
```
tests/
├── unit/              # Component isolation tests
├── integration/       # Multi-component workflow tests
├── functional/        # Feature validation with sample data
├── e2e/              # End-to-end tests with real product data
└── performance/      # Performance benchmarking
```

### When to Create Tests
- **Unit tests** (`tests/unit/test_*.py`): New functions, database operations, LLM logic
- **Integration tests** (`tests/integration/test_*.py`): Workflows spanning multiple layers
- **Functional tests** (`tests/functional/test_*.py`): New features/strategies with generic/sample data
- **E2E tests** (`tests/e2e/test_*.py`): Realistic scenarios with real product database
- **Performance tests** (`tests/performance/test_*.py`): Algorithm optimization/benchmarking

### Test Naming Conventions
- File: `test_<feature_name>.py` (e.g., `test_product_search.py`)
- Function: `def test_<scenario>()` (e.g., `def test_high_temperature_hoses()`)
- Class: `class Test<Component>()` (e.g., `class TestDatabaseSchema()`)

### Test Creation Checklist
1. ✅ Choose correct category (unit/integration/functional/e2e/performance)
2. ✅ Create file in appropriate `tests/<category>/` subdirectory
3. ✅ Use correct imports: `from Layer_2_Agentic...` (NOT `agentic_reasoning`)
4. ✅ Add docstrings explaining what is tested
5. ✅ Use descriptive test names that indicate the scenario
6. ✅ Store in `tests/` for reuse (DO NOT create on project root)
7. ✅ Verify with: `pytest tests/ --collect-only`
8. ✅ Update `tests/README.md` if adding new test category

### Example Test
```python
# tests/functional/test_product_search.py
"""Test product search functionality."""

from Layer_2_Agentic.logic.function_library import func_search_products

def test_search_by_material():
    """Test searching products by material type (rubber)."""
    params = {
        "database_path": "database/harvested.db",
        "keywords": "rubber",
        "limit": 5
    }
    
    success, result = func_search_products(params)
    
    assert success, f"Search failed: {result}"
    assert result['Count'] > 0, "Should find rubber products"
```

### Test Execution
```bash
# Run all tests
pytest tests/

# Run specific category
pytest tests/functional/

# Run specific test
pytest tests/functional/test_product_search.py::test_search_by_material

# View in VS Code Testing tab (left sidebar)
```

- **Testing**: Run `pytest tests/` or use VS Code Testing tab (left sidebar). See `tests/README.md` for detailed guidelines.

## Project-Specific Conventions
- **Hierarchical Data Model**: Categories → Product Families → Products, with JSON fields for specs and bounding boxes.
- **Full-Text Search**: FTS5 enabled for product and knowledge tables.
- **Swedish Language**: All catalog content is preserved in Swedish.
- **Thread Standards**: Coupling extraction focuses on thread compatibility (G, JIC, ORFS, NPTF, BSP).
- **Debug Levels**: Set in `main.py` (0=SILENT, 4=VERBOSE).
- **Output Locations**: 
  - Layer 1a outputs: `Layer_1a_Extraction/data/` (tables, png_pages, output, exports)
  - Layer 1b outputs: `Layer_1b_Extraction/data/` (png_pages, tables, etc.)
  - Core databases: `database/` (harvested.db, agentic.db)
  - Vector index: `vector_index/`

## Integration Points
- **Ollama**: Required for VLM extraction. Start with `ollama serve` and pull the correct model.
- **LangGraph/LangChain**: Used for workflow orchestration and LLM integration in Layer 2.
- **Flask**: Web UI in Layer 3.

## Example File References
- `Layer_1a_Extraction/4_extract_product.py`: Product extraction logic
- `Layer_2_Agentic/logic/function_library.py`: Core function library
- `Layer_3_Application/web_app.py`: Web interface
- `database/db_utils.py`: Database utilities
- `tests/`: All test scripts

## Troubleshooting
- **Ollama errors**: Ensure server is running and model is pulled
- **Database errors**: Verify path and schema with `db_utils.py`
- **Import errors**: Run scripts from project root, check path manipulation
- **Web UI issues**: Confirm Flask is installed and Layer 2 is accessible

---

_If any conventions or workflows are unclear, please ask for clarification or examples from the codebase._
