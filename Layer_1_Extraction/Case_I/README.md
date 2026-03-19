# Layer 1 Extraction — Case I (Hydroscand)

## Overview

This folder contains the full **PDF extraction pipeline** for Case I, which processes the Hydroscand industrial product catalog (hydraulic hoses, couplings, and fittings) into a structured SQLite database used by the RCP reasoning engine.

**Goal**: Convert raw Swedish-language PDF catalog pages → hierarchical relational database (`database/harvested.db`) that Layer 2 can query with precision.

---

## Pipeline Architecture

```
PDF Catalog (Hydroscand Produktbok)
        ↓
┌───────────────────────────────────────┐
│  Layer_1a/  Legacy extraction         │  ← Reference implementation
│  (hose products, basic VLM pipeline)  │
└───────────────────────────────────────┘
        ↓ evolved into
┌───────────────────────────────────────┐
│  Layer_1b/  Production extraction     │  ← Active pipeline
│  0. Extract knowledge (intro pages)   │  → product_knowledge table
│  1. PDF → PNG (page rendering)        │  → png_pages/
│  2. Detect headers/footers            │  → page_regions table
│  2b. Extract categories (VLM)         │  → categories table
│  3a. Extract families (VLM)           │  → product_families table
│  3b. Extract products (VLM)           │  → products table
└───────────────────────────────────────┘
        ↓
database/harvested.db
(335 products · 69 families · full-text search enabled)
```

---

## What Was Extracted

| Table | Contents | Rows |
|-------|----------|------|
| `categories` | Top-level product categories (e.g., SPIRALSLANG) | ~10 |
| `product_families` | Named hose/coupling families with shared specs | 69 |
| `products` | Individual SKUs with full spec JSON | 335 |
| `product_knowledge` | Intro-page assembly instructions, standards, ToC | ~40 |

All content is preserved in **Swedish** (the catalog's source language). Full-text search (FTS5) is enabled on both `products` and `product_knowledge`.

---

## Sub-folders

| Folder | Status | Purpose |
|--------|--------|---------|
| [`Layer_1a/`](Layer_1a/) | Legacy / reference | Original hose extraction scripts — kept for reproducibility |
| [`Layer_1b/`](Layer_1b/) | Production | Active pipeline used to build `harvested.db` |

---

## Quick Start (Layer_1b)

Requires Ollama running with a vision model:

```bash
ollama serve
ollama pull qwen2-vl

# From project root:
python database/db_utils.py --init
python Layer_1_Extraction/Case_I/Layer_1b/0_extract_knowledge.py
python Layer_1_Extraction/Case_I/Layer_1b/1_pdf_to_png.py
python Layer_1_Extraction/Case_I/Layer_1b/2b_extract_categories.py
python Layer_1_Extraction/Case_I/Layer_1b/3a_extract_families.py
python Layer_1_Extraction/Case_I/Layer_1b/3b_extract_products_vlm.py

python database/db_utils.py --verify
```

> The pre-populated `database/harvested.db` is already included — re-extraction is only needed if you are adapting the framework to a new PDF catalog.

---

## Case I at a Glance

| Attribute | Value |
|-----------|-------|
| Domain | Hydraulic hoses, couplings, fittings |
| Source | Hydroscand AB — *Produktbok* (Swedish catalog) |
| Language | Swedish |
| Database | `database/harvested.db` (included) |
| Evaluation set | 100 annotated queries (`Experiments/Case_I/test_questions.json`) |
| Results | `Experiments/Case_I/results/` |
