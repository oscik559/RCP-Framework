# Copilot Instructions for Project_Hydroscand-Hoses

## Overview
This project is a three-layer intelligent system for extracting, reasoning about, and querying industrial product data from PDF catalogs. It is organized into three main layers:
- **Layer 1: Extraction** (PDF → Tables → Products → Database)
- **Layer 2: Agentic Reasoning** (Goal → Strategy → Function, with LLM and workflow orchestration)
- **Layer 3: Application** (Web UI, APIs, progress tracking)

## Key Architectural Patterns
- **Centralized Database**: All product, family, and knowledge data is stored in `data/database/harvested.db` (see `db_utils.py` and `harvested_schema.sql`).
- **Layer Separation**: Extraction, reasoning, and UI logic are strictly separated. Cross-layer imports use explicit path manipulation (see `sys.path.insert` in Layer 3).
- **Agentic Reasoning**: Layer 2 uses a Goal → Strategy → Function pattern, with reusable function libraries and strategy templates. See `Layer_2-Agentic/agentic_reasoning/logic/function_library.py` and `templates.py`.
- **VLM Integration**: Vision Language Models (Ollama + Qwen) are used for table and product extraction in Layer 1. Model and API configuration is passed via CLI args.
- **Testing**: All tests are in `tests/`, organized by unit, integration, performance, and utilities. Use `pytest tests/` for full suite.

## Developer Workflows
- **Extract Data**: Run Layer 1 scripts to convert PDF pages to PNG, detect tables, and extract products. Example:
  ```pwsh
  python Layer_1-Extraction/1_pdf_to_png.py PDF/Produktbok.pdf
  python Layer_1-Extraction/3_detect_tables.py
  python Layer_1-Extraction/4_extract_product.py PDF/Produktbok.pdf --page 31
  ```
- **Query Data**: Use Layer 2 (main.py) for CLI queries, or Layer 3 (web_app.py) for web UI. Example:
  ```pwsh
  python main.py
  cd Layer_3-Application
  python web_app.py
  ```
- **Database Access**: Use `db_utils.py` for verification and schema management. Example:
  ```pwsh
  python data/database/db_utils.py --verify
  ```
- **Testing**: Run `pytest tests/` or individual test files for diagnostics.

## Project-Specific Conventions
- **Hierarchical Data Model**: Categories → Product Families → Products, with JSON fields for specs and bounding boxes.
- **Full-Text Search**: FTS5 enabled for product and knowledge tables.
- **Swedish Language**: All catalog content is preserved in Swedish.
- **Thread Standards**: Coupling extraction focuses on thread compatibility (G, JIC, ORFS, NPTF, BSP).
- **Debug Levels**: Set in `main.py` (0=SILENT, 4=VERBOSE).
- **Output Locations**: Extracted tables in `data/tables/`, visualizations in `output/`, exports in `data/exports/`.

## Integration Points
- **Ollama**: Required for VLM extraction. Start with `ollama serve` and pull the correct model.
- **LangGraph/LangChain**: Used for workflow orchestration and LLM integration in Layer 2.
- **Flask**: Web UI in Layer 3.

## Example File References
- `Layer_1-Extraction/4_extract_product.py`: Product extraction logic
- `Layer_2-Agentic/agentic_reasoning/logic/function_library.py`: Core function library
- `Layer_3-Application/web_app.py`: Web interface
- `data/database/db_utils.py`: Database utilities
- `tests/`: All test scripts

## Troubleshooting
- **Ollama errors**: Ensure server is running and model is pulled
- **Database errors**: Verify path and schema with `db_utils.py`
- **Import errors**: Run scripts from project root, check path manipulation
- **Web UI issues**: Confirm Flask is installed and Layer 2 is accessible

---

_If any conventions or workflows are unclear, please ask for clarification or examples from the codebase._
