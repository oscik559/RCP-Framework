# Contributing to RCP Framework

Thank you for your interest in the RCP Framework. This project accompanies the paper:

> *"A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge"*
> Linköping University / Vinnova DART project (grant 2024-01420)

---

## Getting Started

```bash
git clone https://github.com/oscik559/RCP-Framework.git
cd RCP-Framework

python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -e ".[test]"
```

See [SETUP.md](SETUP.md) for full platform-specific instructions (Windows, macOS, Linux).

Requires Python 3.12 and [Ollama](https://ollama.com) for local model inference.

---

## Project Structure

| Folder | Role |
|--------|------|
| `Layer_1_Extraction/` | PDF → PNG → VLM → SQLite extraction pipeline |
| `Layer_2_Agentic_Reasoning/` | Core RCP framework (LangGraph, function library) |
| `Layer_3_User_Interface/` | Flask web UI and CLI entry points |
| `Experiments/` | Case I & II evaluation scripts and results |
| `database/` | SQLite schemas and pre-populated databases |
| `tests/` | Unit, integration, functional, e2e, performance tests |
| `docs/` | Architecture docs, setup guides, diagrams |

---

## Running Tests

```bash
# Full suite
pytest tests/

# Unit tests only
pytest tests/unit/

# With coverage
pytest tests/ --cov=Layer_2_Agentic_Reasoning --cov-report=html
```

All tests live under `tests/` organized by category (`unit/`, `integration/`, `functional/`, `e2e/`, `performance/`). See [tests/README.md](tests/README.md) for conventions.

---

## Code Conventions

- **Imports**: Always use `from Layer_2_Agentic_Reasoning.X import Y` — do not add ad-hoc `sys.path` manipulations in new code.
- **Debug output**: Use the `debug_config` module; do not add bare `print()` calls.
- **Database**: Access via `database/db_utils.py` — do not hardcode paths.
- **New functions**: Add to `Layer_2_Agentic_Reasoning/logic/function_library.py` following the existing `(params: dict) → (success: bool, result)` signature.
- **New strategies**: Add strategy templates to `Layer_2_Agentic_Reasoning/db/templates.py`.

---

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Write tests for any new logic (place in `tests/<category>/`).
3. Ensure `pytest tests/` passes before opening a pull request.
4. Keep pull requests focused — one feature or fix per PR.
5. Reference the relevant paper section or issue in your PR description.

---

## Reporting Issues

Open an issue on [GitHub Issues](https://github.com/oscik559/RCP-Framework/issues) with:
- A minimal reproducible example
- Expected vs. actual behaviour
- Python version, OS, and Ollama model used

---

## Core Team

| Name | Role | Contact |
|------|------|---------|
| Oscar Ikechukwu | Lead developer | oscar.ikechukwu@liu.se |
| Mehdi Tarkian | Supervisor | mehdi.tarkian@liu.se |

---

## License

By contributing you agree that your contributions will be licensed under the [MIT License](LICENSE).
