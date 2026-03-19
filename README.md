# RCP Framework — Code Repository

Supplementary code for the paper:

> **"A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge"**
> Oscar Ikechukwu, Mehdi Tarkian, Sanjay Nambiar, Marie Jonsson, Christoffer Brax
> Division of Product Realization, IEI, Linköping University
> Funded by Vinnova DART project (grant 2024-01420)

This repository contains the implementation of the **RCP (Retrieve–Contextualize–Plan) framework**, a three-layer agentic architecture for querying structured engineering knowledge from industrial PDF catalogs. Two case studies are included: **Case I** (Hydroscand hydraulic product catalog) and **Case II** (Saab aerospace connector catalog).

---

## Architecture

```
Layer 1: Data Extraction
  PDF → PNG → VLM Extraction → Hierarchical SQLite Database

Layer 2: Agentic Reasoning (RCP Framework)
  Goal → Strategy → Function → Validated Answer

Layer 3: Application
  Web UI / CLI / API
```

| Layer | Role | Key Components |
|-------|------|----------------|
| Layer 1 | Extraction pipeline | PDF rendering, VLM-based parsing, SQLite schema |
| Layer 2 | Reasoning engine | LangGraph workflow, function library, vector search |
| Layer 3 | User interface | Flask web app, CLI entry point |

---

## Repository Structure

```
├── Layer_1a_Extraction/          # Baseline extraction (legacy, kept for reference)
├── Layer_1b_Extraction/          # Production extraction pipeline
├── Layer_2_Agentic/              # Core RCP reasoning framework
│   ├── config/                   # Configuration: constants, prompts, domain settings
│   ├── db/                       # Database connections and strategy templates
│   └── logic/                    # State graph, workflow nodes, function library
├── Layer_3_Application/          # Web interface and APIs
├── Layer_Experiments_Case_I/     # Case I evaluation (Hydroscand, n=100 queries)
│   ├── Baseline_RAG/             # B1: Naive RAG baseline
│   ├── Baseline_SQL_Retrieval/   # B2: SQL retrieval baseline
│   ├── RCP_Framework/            # B3: RCP framework evaluation
│   ├── compute_mcnemar.py        # McNemar's test for statistical significance
│   └── test_questions_appendix_b.json  # Annotated query set (100 questions)
├── Layer_Experiments_Case_II/    # Case II evaluation (Saab, n=100 queries)
│   └── test_questions_saab.json  # Annotated query set (100 questions)
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
git clone https://github.com/oscik559/Hydroscand_Produktbok.git
cd Hydroscand_Produktbok

pip install -r requirements.txt
# or install in editable mode
pip install -e .
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
python Layer_1b_Extraction/0_extract_knowledge.py
python Layer_1b_Extraction/2b_extract_categories.py
python Layer_1b_Extraction/3a_extract_families.py
python Layer_1b_Extraction/3b_extract_products_vlm.py
```

Requires Ollama running locally (`ollama serve`) with a vision model.
See [Layer_1b_Extraction/README.md](Layer_1b_Extraction/README.md) for the full pipeline.

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
cd Layer_Experiments_Case_I
python run_evaluation.py

# Run Case II evaluation
cd Layer_Experiments_Case_II
python run_evaluation_saab.py

# Statistical significance (McNemar's test)
python Layer_Experiments_Case_I/compute_mcnemar.py
```

Results are written to `results/` within each experiment folder. The consolidated results used in the paper are in `results_appendix_b/`.

---

## Testing

```bash
# All tests
python -m pytest tests/

# Unit tests only
python -m pytest tests/unit/

# With coverage
python -m pytest tests/ --cov=Layer_2_Agentic
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

- [docs/SETUP.md](docs/SETUP.md) — detailed setup instructions
- [docs/STRATEGY_ARCHITECTURE.md](docs/STRATEGY_ARCHITECTURE.md) — RCP framework design
- [docs/GENERIC_FUNCTIONS_SUMMARY.md](docs/GENERIC_FUNCTIONS_SUMMARY.md) — function library reference
- [docs/graph.png](docs/graph.png) — workflow state graph

---

## License

MIT License — see [LICENSE](LICENSE).

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for state machine orchestration
- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- [ChromaDB](https://www.trychroma.com) for vector storage
- [PyMuPDF](https://pymupdf.readthedocs.io) for PDF processing
- [Ollama](https://ollama.com) + Qwen for vision language model inference
