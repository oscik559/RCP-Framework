# Project_Hydroscand-Hoses

A two-layer intelligent system for extracting and querying industrial product information from PDF catalogs.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Data Extraction Pipeline                         │
│  PDF → Tables → Products → Hierarchical Database            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Agentic Reasoning System                         │
│  Natural Language Queries → Intelligent Answers             │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Data Extraction
- **PDF to PNG conversion**: High-resolution page rendering
- **Table detection**: Automatic detection using PyMuPDF
- **VLM extraction**: Content extraction using Vision Language Models (Qwen)
- **Hierarchical database**: Categories → Product Families → Individual Products

### Layer 2: Agentic Query System
- **Natural language interface**: Ask questions in plain English/Swedish
- **Multi-agent reasoning**: Goal → Strategy → Function workflow
- **Intelligent search**: Semantic search with FTS5 full-text indexing
- **Complex queries**: Product comparisons, filtering, specifications lookup

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
sqlite3 data/products.db < Layer_1/schema.sql
```

## 📋 Usage

### Layer 1: Extract Products from PDF

```bash
# Convert PDF pages to PNG
python Layer_1/1_pdf_to_png.py PDF/Produktbok.pdf

# Detect and extract tables
python Layer_1/3_detect_tables.py

# Extract product data
python Layer_1/4_extract_product.py PDF/Produktbok.pdf --page 31
```

**Options:**
- `--page N`: Extract from page N
- `--ollama-url URL`: Ollama API URL (default: http://localhost:11434)
- `--model NAME`: VLM model name (default: qwen3-vl:235b-cloud)

**Output:**
- **Database**: `data/products.db` - Hierarchical product database
- **Tables**: `data/tables/` - Extracted table data (JSON)
- **Visualizations**: `output/` - Images with bounding boxes

### Layer 2: Query Products

```bash
cd Layer_2
python main.py
```

Edit queries in `main.py`:
```python
# Example queries
user_query = "What are the specifications of product 1059-01-04?"
user_query = "Find all products in HÖGTRYCKSSLANG category"
user_query = "Compare product 1059-01-04 with 1059-01-06"
```

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
- product_id (FOREIGN KEY)
- spec_key
- spec_value
- unit

## Troubleshooting

**Connection refused**: Make sure Ollama is running (`ollama serve`)
**No model**: Pull a vision model first (`ollama pull qwen2-vl`)
**No products extracted**: Check that the page contains product specification tables