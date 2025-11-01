# Project_Hydroscand-Hoses

A three-layer intelligent system for extracting and querying industrial product information from PDF catalogs.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Data Extraction Pipeline                         │
│  PDF → Tables → Products → Hierarchical Database            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Agentic Reasoning Framework                      │
│  Core Logic: Goal → Strategy → Function                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Application Layer                                │
│  Web UI, APIs, User Interactions                            │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Data Extraction
- **PDF to PNG conversion**: High-resolution page rendering
- **Table detection**: Automatic detection using PyMuPDF
- **VLM extraction**: Content extraction using Vision Language Models (Qwen)
- **Hierarchical database**: Categories → Product Families → Individual Products

### Layer 2: Agentic Reasoning Framework
- **Core reasoning engine**: Goal → Strategy → Function workflow
- **Generic function library**: 30 reusable building blocks
- **Template system**: Reusable strategy and function templates
- **Intelligent search**: Semantic search with FTS5 full-text indexing
- **Parallel execution**: Support for concurrent function execution with batching
- **Validation loops**: Multi-level validation with retry mechanisms
- **Database integration**: State tracking and execution history
- **LLM integration**: Powered by language models for intelligent reasoning

### Layer 3: Application Layer
- **Web interface**: Flask-based UI for natural language queries
- **Progress tracking**: Real-time workflow execution visualization
- **Session management**: Multi-user session handling
- **Export capabilities**: Results export and data visualization
- **API endpoints**: RESTful APIs for external integration

## 🎯 System Workflow

```
User Query (Layer 3: Web UI)
    ↓
Goal Definition (Layer 2: parse intent)
    ↓
Strategy Planning (Layer 2: select reasoning approach)
    ↓
Function Execution (Layer 2: execute actions, can be parallel)
    ↓
Multi-level Validation (Layer 2: function → strategy → goal)
    ↓
Data Access (Layer 1: query database)
    ↓
Final Answer (Layer 3: display to user)
```

### Layer Responsibilities

| Layer | Purpose | Components |
|-------|---------|------------|
| **Layer 1** | Data Storage | Database schema, product data, extracted tables |
| **Layer 2** | Reasoning Engine | Config, logic, database connections, workflows |
| **Layer 3** | User Interface | Web app, APIs, templates, progress tracking |

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.9+
python --version

# Ollama with vision model (for Layer 1)
ollama pull qwen3-vl:235b-cloud
ollama serve
```

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Project_Hydroscand-Hoses

# Install dependencies
pip install -r requirements.txt

# Initialize database (Layer 1)
sqlite3 data/products.db < Layer_1-Extraction/schema.sql
```

## 📋 Usage

### Layer 1: Extract Products from PDF

```bash
# Convert PDF pages to PNG
python Layer_1-Extraction/1_pdf_to_png.py PDF/Produktbok.pdf

# Detect and extract tables
python Layer_1-Extraction/3_detect_tables.py

# Extract product data
python Layer_1-Extraction/4_extract_product.py PDF/Produktbok.pdf --page 31
```

**Options:**
- `--page N`: Extract from page N
- `--ollama-url URL`: Ollama API URL (default: http://localhost:11434)
- `--model NAME`: VLM model name (default: qwen3-vl:235b-cloud)

**Output:**
- **Database**: `data/products.db` - Hierarchical product database
- **Tables**: `data/tables/` - Extracted table data (JSON)
- **Visualizations**: `output/` - Images with bounding boxes

### Layer 2 & 3: Query Products

**Option 1: Command Line (Layer 2 Direct)**
```bash
python main.py
```

Edit queries in `main.py` (at project root):
```python
# Example queries
user_query = "What are the specifications of product 1059-01-04?"
user_query = "Find all products in HÖGTRYCKSSLANG category"
user_query = "Compare product 1059-01-04 with 1059-01-06"
```

**Debug Levels** (set in `main.py`):
- **0 = SILENT**: No debug output
- **1 = MINIMAL**: Only major workflow steps
- **2 = NORMAL**: Standard progress indicators (recommended)
- **3 = DETAILED**: Function parameters and outputs
- **4 = VERBOSE**: All debug information

**Option 2: Web Interface (Layer 3)**
```bash
cd Layer_3
python app/web_app.py
```

Then open: `http://localhost:5001`

**Quick Start Guide**: See [`QUICK_START.md`](QUICK_START.md) for detailed integration guide

## 🗄️ Database Schema

### Hierarchical Structure

```sql
categories (LEVEL 1: Top-level product groups)
  ├── id, name, chapter, description, page_number
  │
  └── product_families (LEVEL 2: Product lines)
        ├── id, category_id, family_code, name, subtitle
        ├── construction_details (JSON)
        ├── applications (TEXT, FTS5 indexed)
        │
        └── products (LEVEL 3: Individual SKUs)
              ├── id, family_id, product_code, variant_suffix
              ├── configuration_type, specifications (JSON)
              └── bounding_box (JSON), page_number
```

### Example Data

```
HÖGTRYCKSSLANG (Category)
  └── 1059-01 HYDROSCAND T8081 (Family)
        ├── 1059-01-04 (Product)
        ├── 1059-01-06 (Product)
        └── 1059-01-08 (Product)
```

## 📁 Project Structure

```
Project_Hydroscand-Hoses/
├── Layer_1-Extraction/                    # Data extraction pipeline
│   ├── 1_pdf_to_png.py
│   ├── 3_detect_tables.py
│   ├── 4_extract_product.py
│   └── schema.sql
│
├── Layer_2-Agentic/                    # Agentic reasoning framework (CORE)
│   └── agentic_reasoning/
│       ├── config/             # Configuration files
│       │   ├── constants.py
│       │   ├── config.yaml
│       │   ├── prompts.yaml
│       │   ├── debug_config.py
│       │   ├── session_config.py
│       │   └── domain_config.py
│       ├── db/                 # Database connection & schemas
│       │   ├── connection.py
│       │   ├── database_manager.py
│       │   └── migrations/
│       ├── logic/              # Core reasoning logic
│       │   ├── state_graph.py          # LangGraph workflow
│       │   ├── workflow_nodes.py       # Goal/Strategy/Function nodes
│       │   ├── function_library.py     # 30 generic functions
│       │   ├── templates.py            # Strategy templates
│       │   ├── llm_helpers.py          # LLM integration
│       │   └── vector_helpers.py       # Vector search
│       └── pipelines/          # Pre-built reasoning pipelines
│
├── Layer_3-Application/                    # Application layer (UI/APIs)
│   ├── README.md              # Layer 3 documentation
│   └── app/
│       ├── web_app.py         # Flask web interface
│       ├── progress_flow.py   # Progress tracking
│       └── templates/         # HTML templates
│           └── index.html
│
├── data/                       # Data storage
│   ├── products.db            # Product database
│   ├── tables/                # Extracted table data
│   └── exports/               # CSV exports
│
├── docs/                       # Documentation
│   ├── graph.md               # Workflow diagram
│   ├── SETUP.md
│   └── [other docs]
│
├── tests/                      # All tests
│   ├── test_*.py              # High-level tests
│   └── layer2/                # Framework tests
│       ├── unit/
│       ├── integration/
│       ├── performance/
│       └── utilities/
│
├── main.py                     # CLI entry point
├── QUICK_START.md             # Integration guide
└── README.md                  # This file
```

## 🔌 Layer 2 Integration

The Layer 2 framework is **domain-agnostic** and can be adapted for any use case. See [`QUICK_START.md`](QUICK_START.md) for detailed integration guide.

### Key Integration Steps:

1. **Define domain-specific functions** in `Layer_2-Agentic/agentic_reasoning/logic/function_library.py`
2. **Create strategy templates** in `Layer_2-Agentic/agentic_reasoning/logic/templates.py`
3. **Configure your database** in `Layer_2-Agentic/agentic_reasoning/config/domain_config.py`
4. **Set up LLM provider** in `Layer_2-Agentic/agentic_reasoning/logic/llm_helpers.py`
5. **Test with queries** by running `main.py`

### Example Workflows

**Simple Query:**
```
Query: "Find product 1059-01-04"
  ↓ Goal: "Retrieve product information"
  ↓ Strategy: "Database Lookup"
  ↓ Functions: [query_database]
  ↓ Answer: Product specifications
```

**Complex Query:**
```
Query: "Compare product A with B"
  ↓ Goal: "Provide comparative analysis"
  ↓ Strategy: "Multi-Product Comparison"
  ↓ Functions: [get_product(A), get_product(B), compare_specs, summarize]
  ↓ Answer: Detailed comparison
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run Layer 2 framework tests
python -m pytest tests/layer2/

# Run specific test
python -m pytest tests/test_workflow.py
```

## 📝 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Integration guide for Layer 2 framework
- **[docs/](docs/)** - Detailed documentation and architecture diagrams
- **[docs/graph.md](docs/graph.md)** - Visual workflow architecture

## 🔍 Troubleshooting

### Layer 1 (Data Extraction)
- **Connection refused**: Make sure Ollama is running (`ollama serve`)
- **No model**: Pull a vision model first (`ollama pull qwen2-vl`)
- **No products extracted**: Check that the page contains product specification tables

### Layer 2 (Agentic Reasoning)
- **LLM not responding**: Check API keys are set correctly
- **Functions not found**: Ensure functions are registered in function library
- **Database errors**: Verify database path in `domain_config.py`
- **Import errors**: Make sure you're running from project root

## 🤝 Contributing

This framework is designed to be extended:
1. Implement domain-specific functions
2. Create strategy templates for common patterns
3. Configure database schema for your data
4. Test with real-world queries

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

**Layer 1:**
- PyMuPDF for PDF processing
- Ollama + Qwen for vision language models

**Layer 2:**
- LangGraph for state machine orchestration
- LangChain for LLM integration
- ChromaDB for vector storage
- SQLite for state persistence