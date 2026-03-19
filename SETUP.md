# Setup Guide — RCP Framework

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | **3.12.x** | Do NOT use 3.13/3.14 — ChromaDB and onnxruntime are incompatible |
| Ollama | latest | Required for local LLM and embedding inference |
| Git | any | For cloning the repository |

---

## 1. Install Python 3.12

### Windows
Download from [python.org](https://www.python.org/downloads/) and select **3.12.x**.
During installation, check **"Add Python to PATH"**.

Verify:
```powershell
python --version   # Must show 3.12.x
```

### macOS
```bash
brew install python@3.12
python3.12 --version   # Must show 3.12.x
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
python3.12 --version
```

---

## 2. Install Ollama

Ollama is required to run LLM inference locally (Layer 2 reasoning and Layer 1 VLM extraction).

### Windows
Download and run the installer from [ollama.com](https://ollama.com/download).
Ollama starts automatically as a background service.

### macOS
```bash
brew install ollama
ollama serve   # Start in a separate terminal
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # Start in a separate terminal
```

### Pull required models
```bash
# Reasoning LLM (required)
ollama pull llama3.2:latest

# Embedding model (required for semantic search / CONTEXTUAL PRODUCT SEARCH strategy)
ollama pull nomic-embed-text

# Vision model (required only for Layer 1 extraction from new PDFs)
ollama pull qwen2-vl
```

Verify Ollama is running:
```bash
ollama list   # Should list pulled models
```

---

## 3. Clone the Repository

```bash
git clone https://github.com/oscik559/RCP-Framework.git
cd RCP-Framework
```

---

## 4. Create Virtual Environment

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Your prompt should now show `(.venv)`.

---

## 5. Install Dependencies

```bash
pip install --upgrade pip
pip install -e .
# Include test dependencies if you want to run pytest
pip install -e ".[test]"
```

> `pip install -e .` installs the project in editable mode, enabling clean imports like
> `from Layer_2_Agentic_Reasoning.logic import ...` without any `sys.path` manipulation.
>
> Alternatively: `pip install -r requirements.txt` (without editable install).

---

## 6. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Web interface secret key (generate once)
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(48))">
FLASK_DEBUG=false

# LLM API keys (only needed if using cloud providers instead of Ollama)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

The framework defaults to **Ollama (local)** — no API keys are required for standard use.

---

## 7. Verify Installation

```bash
# Check package imports
python -c "from Layer_2_Agentic_Reasoning.logic.workflow_types import SessionState; print('OK')"

# Check database
python database/db_utils.py --verify

# Run tests
python -m pytest tests/unit/ -q
```

Expected database output:
```
Database Status: database/harvested.db
page_regions      EXISTS   (X rows)
categories        EXISTS   (X rows)
product_families  EXISTS   (X rows)
products          EXISTS   (X rows)
product_knowledge EXISTS   (X rows)
```

---

## 8. Run the System

### CLI (quickest)
```bash
python main.py
```

Edit the `user_query` variable in [main.py](main.py) to change the query.
Set `debug_level` (0 = silent, 4 = verbose).

### Web Interface
```bash
python run_web.py
# Open http://localhost:5001
```

### Evaluation (Case I)
```bash
cd Experiments/Case_I
python run_evaluation.py --baseline b3 --limit 5   # Quick test (5 questions)
python run_evaluation.py --baseline all             # Full run (100 questions)
```

---

## 9. LLM & Model Configuration

Models are configured in [Layer_2_Agentic_Reasoning/config/config_loader.py](Layer_2_Agentic_Reasoning/config/config_loader.py).

| Setting | Default | Notes |
|---------|---------|-------|
| Basic LLM | `llama3.2:latest` | Used for goal/strategy/function steps |
| Embedding model | `nomic-embed-text` | Required for semantic search |
| Vision model | `qwen2-vl` | Only needed for Layer 1 PDF extraction |

To switch to a cloud provider, set the appropriate API key in `.env` and update `config_loader.py`.

---

## Troubleshooting

### `ModuleNotFoundError: Layer_2_Agentic_Reasoning`
You haven't installed the package in editable mode:
```bash
pip install -e .
```
Always run commands from the **project root** directory.

### Python version error / `onnxruntime` fails
You're not using Python 3.12:
```bash
python --version   # Must be 3.12.x

# Fix (Windows)
py -3.12 -m venv .venv

# Fix (macOS)
python3.12 -m venv .venv
```

### Ollama connection error
```bash
# Check Ollama is running
ollama list

# Start it if not running
ollama serve        # macOS/Linux
# On Windows: Ollama runs as a tray app — check system tray
```

### Semantic search returns nothing
The embedding model isn't pulled:
```bash
ollama pull nomic-embed-text
```

### VS Code doesn't find imports
Select the correct interpreter:
1. `Ctrl+Shift+P` → **Python: Select Interpreter**
2. Choose `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux)

### Windows: emoji characters cause encoding errors
Already handled — [main.py](main.py) and all evaluation scripts reconfigure `stdout` to UTF-8.
If you still see `charmap` errors in another script, add at the top:
```python
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

---

## Platform Differences Summary

| | Windows | macOS / Linux |
|--|---------|---------------|
| Activate venv | `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Python command | `python` | `python3` or `python3.12` |
| Ollama start | Auto (tray app) | `ollama serve` |
| Path separator | `\` (handled by `pathlib`) | `/` |
| Encoding | UTF-8 via `reconfigure()` | UTF-8 by default |
