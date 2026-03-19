# Layer 3 — User Interface

This layer sits on top of `Layer_2_Agentic_Reasoning` and provides the user-facing entry points: a Flask web application and a CLI runner.

## Files

| File | Purpose |
|------|---------|
| `web_app.py` | Flask web server — query UI with real-time progress tracking |
| `progress_flow.py` | Workflow progress event stream for the web interface |
| `templates/index.html` | Single-page HTML/JS frontend |

## Running

### Web Interface (recommended)
```bash
# From project root
python run_web.py
# Open http://localhost:5001
```

### CLI
```bash
# From project root — edit user_query in main.py first
python main.py
```

## How It Works

```
Browser → Flask (web_app.py)
              ↓
         Layer_2_Agentic_Reasoning  (get_graph().invoke(...))
              ↓
         Goal → Strategy → Function → Validated Answer
              ↓
         JSON response streamed back to browser via progress_flow.py
```

The web app initializes the LangGraph workflow on startup and exposes two endpoints:

- `POST /query` — submit a natural language query, returns a session ID
- `GET /progress/<session_id>` — Server-Sent Events stream of workflow progress
- `GET /result/<session_id>` — final structured answer

## Configuration

All LLM and database settings come from `Layer_2_Agentic_Reasoning/config/`:

- **Domain name / description**: `config/domain_config.py`
- **LLM model**: `config/config_loader.py`
- **Debug verbosity**: `config/debug_config.py` (0 = silent, 4 = verbose)
- **Secret key / debug mode**: `.env` file at project root (`SECRET_KEY`, `FLASK_DEBUG`)

## Dependencies

```
Layer_3_User_Interface
    └── Layer_2_Agentic_Reasoning  (reasoning engine)
         └── database/harvested.db  (product data)
         └── database/agentic.db    (workflow state)
```

Flask, Flask-SocketIO, and python-socketio are installed via `pip install -e .`.

## Troubleshooting

**Emoji/encoding errors on Windows** — handled automatically; `web_app.py` reconfigures stdout to UTF-8 on import.

**Port already in use:**
```bash
# Windows
netstat -ano | findstr :5001
taskkill /PID <pid> /F

# macOS/Linux
lsof -i :5001 && kill -9 <PID>
```

**Workflow not initializing** — ensure Ollama is running (`ollama serve`) and the reasoning LLM is pulled (`ollama pull llama3.2:latest`).

**Import errors** — run from project root with the package installed: `pip install -e .`
