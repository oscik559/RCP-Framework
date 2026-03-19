# macOS Setup Guide

## Prerequisites

### 1. Install Python 3.12+
```bash
# Check Python version
python3 --version

# If needed, install via Homebrew
brew install python@3.12
```

### 2. Install Ollama
```bash
# Install Ollama for LLM functionality
brew install ollama

# Start Ollama service
ollama serve

# In another terminal, pull the required model
ollama pull qwen2.5:3b
```

### 3. Clone the Repository
```bash
git clone https://github.com/oscik559/Project_Hydroscand-Hoses.git
cd Project_Hydroscand-Hoses
```

## Setup Steps

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -e .
# OR use requirements.txt
# pip install -r requirements.txt
```

**Main dependencies that will be installed:**
- langgraph, langchain-core, langchain-ollama (LLM workflow)
- flask (web interface)
- sqlite3 (built-in, for databases)
- Pillow (image processing)
- pandas, openpyxl (data export)

**Why `pip install -e .`?**
- Enables clean imports: `from Layer_2_Agentic_Reasoning.logic import ...`
- No sys.path manipulation needed
- Changes to code immediately reflected

### 3. Verify Installation
```bash
# Test imports
python -c "from Layer_2_Agentic_Reasoning.logic.workflow_types import SessionState; print('✅ Package imports work')"

# Test database initialization
python database/db_utils.py --verify
```

Expected output:
```
📊 Database Status: database/harvested.db
==================================================
page_regions      ✅ EXISTS   (X rows)
categories        ✅ EXISTS   (X rows)
product_families  ✅ EXISTS   (X rows)
products          ✅ EXISTS   (X rows)
product_knowledge ✅ EXISTS   (X rows)
```

### 4. Run the System

#### Command Line Interface
```bash
python main.py
```

#### Web Interface
```bash
cd Layer_3_Application
python web_app.py
```

Then open: http://localhost:5001

## Project Structure (Updated with Underscores)

```
Project_Hydroscand-Hoses/
├── Layer_1_Extraction/Layer_1a/     # PDF extraction pipeline
├── Layer_1_Extraction/Layer_1b/     # Alternative extraction pipeline
├── Layer_2_Agentic_Reasoning/         # Core reasoning engine
│   ├── config/              # Configuration files
│   ├── db/                  # Database connections & schema
│   └── logic/               # Workflow nodes & functions
├── Layer_3_Application/     # Web interface
├── data/                    # Data storage
│   ├── database/            # SQLite databases
│   ├── tables/              # Extracted tables
│   └── png_pages/           # Converted PDF pages
├── tests/                   # Test suites
└── main.py                  # CLI entry point
```

## Important Changes (Recent Updates)

### ✅ Folder Renaming (Python Compatible)
All folders now use underscores instead of hyphens:
- `Layer_2-Agentic` → `Layer_2_Agentic_Reasoning`
- `Layer_3-Application` → `Layer_3_Application`
- `Layer_1a-Extraction` → `Layer_1_Extraction/Layer_1a`
- `Layer_1b-Extraction` → `Layer_1_Extraction/Layer_1b`

### ✅ Module Renaming (Avoid Standard Library Conflicts)
- `logic/types.py` → `logic/workflow_types.py` (avoids shadowing Python's built-in `types` module)

### ✅ Package Installation
The project is now installable as a package:
```bash
pip install -e .
```

This enables:
- Clean imports: `from Layer_2_Agentic_Reasoning.logic import ...`
- No need for sys.path manipulation in most cases
- Editable mode: changes reflect immediately

## Configuration

### Database Paths
Edit `Layer_2_Agentic_Reasoning/config/config_loader.py` if needed:
```python
CONFIG = {
    "agentic_db": "database/agentic.db",      # Workflow tracking
    "harvested_db": "database/harvested.db",  # Product data
    "output_db": "database/output.db",        # Query results
}
```

### LLM Configuration
Models are configured in `Layer_2_Agentic_Reasoning/config/config_loader.py`:
- **Basic LLM**: `qwen2.5:3b` (fast, simple tasks)
- **Reasoning LLM**: `qwen2.5:3b` (complex reasoning)

### Strategy Testing
Enable/disable strategies in `Layer_2_Agentic_Reasoning/config/strategy_testing.py`:
```python
ENABLED_STRATEGIES = [
    "SIMPLE LOOKUP",
    "TABLE SEARCH AND FILTER",
    # "COMPREHENSIVE ANALYSIS",  # Disabled
]
```

## Troubleshooting

### Module Not Found Errors
If you see `ModuleNotFoundError`:
```bash
# Reinstall the package
pip install -e .

# Verify installation
pip list | grep project-hydroscand-hoses
```

### Ollama Connection Errors
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Verify model is available
ollama list
```

### Database Initialization
If databases are missing:
```bash
# Initialize agentic database
python Layer_2_Agentic_Reasoning/db/templates.py

# Check database files exist
ls -lh database/*.db
```

### Import Errors in Direct Script Execution
Some files have `if __name__ == "__main__":` blocks with sys.path setup for direct execution. This is intentional and allows running scripts directly without the package being imported.

## Testing

Run the test suite:
```bash
# All tests
pytest tests/

# Specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

## Key Differences from Windows

1. **Path Separators**: macOS uses `/` (already handled in code with `Path` objects)
2. **Python Command**: Use `python3` instead of `python` (unless aliased)
3. **Virtual Environment Activation**: `source .venv/bin/activate` instead of `.venv\Scripts\Activate.ps1`
4. **Shell**: bash/zsh instead of PowerShell (commands in this guide are bash-compatible)

## What Should Work Out of the Box

✅ **Package imports** - All Layer_* folders are proper Python packages
✅ **Database operations** - SQLite is cross-platform
✅ **LLM integration** - Ollama works on macOS
✅ **Web interface** - Flask runs on all platforms
✅ **PDF extraction** - All scripts use cross-platform libraries

## What Might Need Adjustment

⚠️ **File paths in configuration** - Should auto-detect, but verify `config_loader.py` if issues
⚠️ **Ollama model availability** - Ensure `qwen2.5:3b` is pulled on macOS
⚠️ **Data directory structure** - Clone will preserve structure, but verify `data/` exists

## Quick Start Command Summary

```bash
# 1. Clone and setup
git clone https://github.com/oscik559/Project_Hydroscand-Hoses.git
cd Project_Hydroscand-Hoses
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -e .

# 3. Initialize databases
python Layer_2_Agentic_Reasoning/db/templates.py

# 4. Run CLI
python main.py

# 5. Or run web interface
cd Layer_3_Application
python web_app.py
```

## Support

If you encounter issues specific to macOS, check:
1. Python version compatibility (`python3 --version` should be 3.12+)
2. Virtual environment is activated (prompt shows `(.venv)`)
3. Ollama is running (`ollama serve` in a separate terminal)
4. All dependencies installed (`pip list` should show langgraph, flask, etc.)

---

**Note**: This setup guide assumes you've pushed all recent changes to GitHub. The repository should be in a clean, working state after following these steps on macOS.
