# RCP Framework — Code Repository

Supplementary code for the paper:

> **"A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge"**
> Oscar Ikechukwu, Mehdi Tarkian, Sanjay Nambiar, Marie Jonsson, Christoffer Brax
> Division of Product Realization, IEI, Linköping University
> Funded by Vinnova DART project (grant 2024-01420)

This repository contains the implementation of the **RCP (Relational Control Plane) framework**, a SQL-backed agentic architecture that persists orchestration state as queryable relational records and enforces a six-stage verify-then-summarise control loop. Synthesis is permitted only after retrieved evidence satisfies validation constraints, transforming potential hallucinations into explicit, auditable failures. Two case studies are included: **Case I** (Hydroscand hydraulic product catalog, n=100 queries) and **Case II** (Saab aerospace connector/cable catalog, n=100 queries).

---

## Architecture

<p align="center">
<img width="294" height="645" alt="Agentic_Flowchart" src="https://github.com/user-attachments/assets/4e1be63b-462b-4d9f-9d5e-32bc6630d8f6" />
</p>

| Layer | Role | Key Components |
|-------|------|----------------|
| Layer 1 | Extraction pipeline | PDF rendering, VLM-based parsing, SQLite schema |
| Layer 2 | Reasoning engine | LangGraph workflow, 6-stage control loop, function library |
| Layer 3 | User interface | Flask web app, CLI entry point |

---

## Repository Structure

```
├── Layer_1_Extraction/
│   └── Case_I/                   # Extraction pipeline for Case I (Hydroscand)
│       ├── Layer_1a/             # Legacy extraction (reference)
│       └── Layer_1b/             # Production extraction pipeline
├── Layer_2_Agentic_Reasoning/    # Core RCP reasoning framework
│   ├── config/                   # Configuration: constants, prompts, domain settings
│   ├── db/                       # Database connections and strategy templates
│   └── logic/                    # State graph, workflow nodes, function library
├── Layer_3_User_Interface/          # Web interface and APIs
├── Experiments/
│   ├── Case_I/                   # Case I evaluation (Hydroscand, n=100 queries)
│   │   ├── Baseline_RAG/         # B1: Naive RAG baseline
│   │   ├── Baseline_SQL_Retrieval/  # B2: SQL retrieval baseline
│   │   ├── RCP_Framework/        # B3: RCP framework evaluation
│   │   ├── compute_mcnemar.py    # McNemar's test for statistical significance
│   │   └── test_questions.json             # Annotated query set (100 questions)
│   ├── Case_II/                  # Case II evaluation (Saab, n=100 queries)
│   │   └── test_questions_saab.json  # Annotated query set (100 questions)
│   └── questions/                # Shared test question sets
├── database/                     # SQLite databases and schema
│   ├── harvested.db              # Product database (Case I)
│   ├── agentic.db                # Workflow state database
│   ├── harvested_schema.sql      # Schema definition
│   └── db_utils.py               # Database utilities
├── docs/                         # Architecture and design documentation
├── tests/                        # Unit, integration, and end-to-end tests
├── main.py                       # CLI entry point
└── run_web.py                    # Web server launcher
```

---

## Requirements

- Python 3.12
- [Ollama](https://ollama.com) with a vision model for Layer 1 extraction (e.g., `qwen2-vl`)
- An LLM API key (OpenAI, Anthropic, or local Ollama) for Layer 2 reasoning

---

## Installation

```bash
git clone https://github.com/oscik559/RCP-Framework.git
cd RCP-Framework

pip install -r requirements.txt
# or install in editable mode
pip install -e .
# install test tooling (required to run pytest commands below)
pip install -e ".[test]"
```

Create a `.env` file at the project root:

```bash
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(48))">
FLASK_DEBUG=false
```

---

## Usage

### Layer 1: Extract products from PDF

```bash
# Production pipeline (Layer 1b)
python Layer_1_Extraction/Case_I/Layer_1b/0_extract_knowledge.py
python Layer_1_Extraction/Case_I/Layer_1b/2b_extract_categories.py
python Layer_1_Extraction/Case_I/Layer_1b/3a_extract_families.py
python Layer_1_Extraction/Case_I/Layer_1b/3b_extract_products_vlm.py
```

Requires Ollama running locally (`ollama serve`) with a vision model.
See [Layer_1_Extraction/Case_I/Layer_1b/README.md](Layer_1_Extraction/Case_I/Layer_1b/README.md) for the full pipeline.

### Layer 2 & 3: Query products

**CLI:**
```bash
python main.py
```

Edit the query directly in `main.py`. Debug verbosity is controlled by `debug_level` (0 = silent, 4 = verbose).

**Web interface:**
```bash
python run_web.py
# Open http://localhost:5001
```

---

## Evaluation (Case I & Case II)

The experiment folders contain the three baselines (B1: Naive RAG, B2: SQL Retrieval, B3: RCP) and the annotated query sets used in the paper.

```bash
# Run Case I evaluation
cd Experiments/Case_I
python run_evaluation.py

# Run Case II evaluation
cd Experiments/Case_II
python run_evaluation_saab.py

# Statistical significance (McNemar's test)
python Experiments/Case_I/compute_mcnemar.py
```

Results are written to `results/` within each experiment folder.

---

## Testing

Install test dependencies first if you used only `-r requirements.txt` or `pip install -e .`:

```bash
python -m pip install -e ".[test]"
```

```bash
# All tests
python -m pytest tests/

# Unit tests only
python -m pytest tests/unit/

# With coverage
python -m pytest tests/ --cov=Layer_2_Agentic_Reasoning
```

---

## Database

The pre-populated product database for Case I is included at `database/harvested.db`. The schema is documented in `database/harvested_schema.sql` and `database/README.md`.

```bash
# Inspect or reinitialize the database
python database/db_utils.py --help
```

---

## Documentation

- [SETUP.md](SETUP.md) — detailed setup instructions (Windows, macOS, Linux)
- [docs/graph.png](docs/graph.png) — workflow state graph
- [docs/Case_I/STRATEGY_ARCHITECTURE.md](docs/Case_I/STRATEGY_ARCHITECTURE.md) — RCP strategy design (Case I)
- [docs/Case_I/GENERIC_FUNCTIONS_SUMMARY.md](docs/Case_I/GENERIC_FUNCTIONS_SUMMARY.md) — function library reference
- [docs/Case_I/SPEC_GLOSSARY.md](docs/Case_I/SPEC_GLOSSARY.md) — product database attribute glossary

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code conventions, and how to submit changes.

---

## License

MIT License — see [LICENSE](LICENSE).

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for state machine orchestration
- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- [ChromaDB](https://www.trychroma.com) for vector storage
- [PyMuPDF](https://pymupdf.readthedocs.io) for PDF processing
- [Ollama](https://ollama.com) + Qwen for vision language model inference
