# Database

SQLite databases and supporting utilities for the RCP Framework.

## Files

| File | Purpose |
|------|---------|
| `harvested.db` | Pre-populated product database for Case I (Hydroscand) — 335 products, 69 families |
| `agentic.db` | Workflow state database — persists RCP orchestration records between sessions |
| `temp.db` | Temporary working database created during workflow execution; can be deleted safely |
| `harvested_schema.sql` | Schema definition for `harvested.db` |
| `attribute_glossary.sql` | SQL-backed glossary of product attribute definitions |
| `db_utils.py` | Database utilities: init, verify, inspect |

## Sub-directories

| Directory | Purpose |
|-----------|---------|
| `vector_index/` | ChromaDB vector store for semantic search (Case I embeddings) |
| `dumps/` | CSV and Markdown exports of `harvested.db` for inspection |
| `backups/` | Empty — source PDFs moved to `Layer_1_Extraction/Case_I/Layer_1b/` |

## Quick Reference

```bash
# Inspect the product database
python database/db_utils.py --verify

# Reinitialize the schema (destructive)
python database/db_utils.py --init

# Open in SQLite shell
sqlite3 database/harvested.db
sqlite> SELECT COUNT(*) FROM products;      -- 335
sqlite> SELECT COUNT(*) FROM product_families;  -- 69
sqlite> .tables
```

## Schema Overview

The `harvested.db` schema is documented fully in `harvested_schema.sql`:

| Table | Description |
|-------|-------------|
| `categories` | Top-level product categories (~10 rows) |
| `product_families` | Named product families with shared specs (69 rows) |
| `products` | Individual SKUs with full spec JSON (335 rows) |
| `product_knowledge` | Assembly instructions, standards, catalog intro text (~40 rows) |

Full-text search (FTS5) is enabled on `products` and `product_knowledge`.

## Import Pattern

```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "harvested.db"
```
