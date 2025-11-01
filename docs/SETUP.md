# Project Setup Guide

## Prerequisites

**Python 3.12.12 REQUIRED**

⚠️ **Do NOT use Python 3.14** - ChromaDB dependencies are incompatible

## Installation Steps

### 1. Install Python 3.12 (macOS)
```bash
brew install python@3.12
```

### 2. Create Virtual Environment
```bash
# Use Python 3.12 specifically
python3.12 -m venv .venv
```

### 3. Activate Virtual Environment
```bash
source .venv/bin/activate
```

### 4. Upgrade pip
```bash
pip install --upgrade pip
```

### 5. Install All Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- **Layer 1**: PDF processing (requests, Pillow, PyMuPDF)
- **Layer 2**: Agentic reasoning system (LangChain, LangGraph, ChromaDB, etc.)

## Verification

### Check Python Version
```bash
python --version
# Should output: Python 3.12.12
```

### Check Installed Packages
```bash
pip list | grep -E "(langchain|chromadb)"
```

Expected output:
```
chromadb                    1.3.0
langchain                   1.0.3
langchain-anthropic         1.0.1
langchain-chroma            1.0.0
langchain-classic           1.0.0
langchain-community         0.4.1
langchain-core              1.0.2
langchain-ollama            1.0.0
langchain-openai            1.0.1
langchain-text-splitters    1.0.0
```

### Run Tests
```bash
python Layer_2/test_layer2_complete.py
```

Expected: **6/6 tests passing** ✅

## Project Structure

```
Project_Hydroscand-Hoses/
├── requirements.txt          # All dependencies (Layer 1 + Layer 2)
├── data/                     # Database files
│   └── harvested_db.db      # Hydroscand product database
├── Layer_2/                  # Agentic reasoning system
│   ├── agentic_reasoning/
│   │   ├── config/          # Domain configurations
│   │   ├── database/        # Schema and connections
│   │   └── logic/           # LLM helpers and workflow
│   └── test_layer2_complete.py
└── .venv/                    # Virtual environment (Python 3.12)
```

## Common Issues

### Issue: "No module named 'chromadb'"
**Solution:** Verify you're using Python 3.12, not 3.14
```bash
python --version  # Must be 3.12.x
```

### Issue: Import errors in VS Code
**Solution:** 
1. Press `Cmd+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose `.venv/bin/python` (3.12.12)

### Issue: "onnxruntime" or "pypika" errors
**Solution:** You're using Python 3.14. Start over with Python 3.12:
```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file for API keys (optional):
```bash
# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...

# Ollama runs locally, no API key needed
```

## Running the System

### Test Layer 2 Components
```bash
python Layer_2/test_layer2_complete.py
```

### Run Main Agentic System (coming soon)
```bash
python Layer_2/main.py
```

## Package Inventory

**Total Packages:** 141+ installed

**Key Dependencies:**
- langgraph 1.0.2
- langchain 1.0.3
- chromadb 1.3.0 ✅
- langchain-chroma 1.0.0 ✅
- SQLAlchemy 2.0.44
- pydantic 2.12.3
- numpy 2.3.4

**LLM Providers:**
- OpenAI (openai 2.6.1)
- Anthropic (anthropic 0.72.0)
- Ollama (ollama 0.6.0)

## Documentation

- `PYTHON_VERSION_GUIDE.md` - Python version details
- `MIGRATION_COMPLETE.md` - Migration summary
- `SETUP.md` - This file

## Status

✅ Python 3.12.12 installed  
✅ Virtual environment configured  
✅ All 141+ packages installed  
✅ ChromaDB working  
✅ All tests passing (6/6)  
✅ Ready for development
