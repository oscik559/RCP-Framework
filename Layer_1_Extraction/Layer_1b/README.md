# Layer 1b: Production Extraction Pipeline

**Status**: ✅ **Production** - Actively maintained extraction system  
**Database**: `database/harvested.db`  
**Legacy Alternative**: See `Layer_1_Extraction/Layer_1a` for basic/reference scripts

## Overview

This directory contains the **production-grade** extraction pipeline for processing industrial product catalogs. It extracts hierarchical product data (Categories → Families → Products) into a structured SQLite database.

### Key Features
✅ Hierarchical extraction with proper relationships  
✅ Swedish language support (UTF-8)  
✅ Vision Language Model (VLM) integration  
✅ Full-text search (FTS5) enabled  
✅ Comprehensive product knowledge extraction  
✅ Thread compatibility and standards tracking

## Architecture

```
PDF Catalog
    ↓
┌─────────────────────────────────────────┐
│  0. Extract Knowledge (intro pages)     │  → product_knowledge table
├─────────────────────────────────────────┤
│  1. PDF to PNG (page rendering)         │  → Layer_1_Extraction/Layer_1b/data/png_pages/
├─────────────────────────────────────────┤
│  2. Detect Headers/Footers              │  → page_regions table
├─────────────────────────────────────────┤
│  2b. Extract Categories                 │  → categories table
├─────────────────────────────────────────┤
│  3a. Extract Families                   │  → product_families table
├─────────────────────────────────────────┤
│  3b. Extract Products (VLM)             │  → products table
└─────────────────────────────────────────┘
    ↓
Hierarchical Database (harvested.db)
```

## Sample Data
- `Press_Couplings.pdf` - Swedish coupling catalog (production)
- `Press_Couplings_en.pdf` - English coupling catalog (reference)

## Files

### Extraction Scripts

1. **`0_extract_knowledge.py`** - Extract product knowledge from intro pages
   - Assembly instructions (MONTERINGSANVISNING)
   - Product descriptions and standards
   - Table of contents and specifications

2. **`1_pdf_to_png.py`** - Convert PDF pages to high-resolution PNG images

3. **`2_detect_headers_footers.py`** - Identify page structure and regions

4. **`2b_extract_categories.py`** - Extract top-level product categories using VLM

5. **`3a_extract_families.py`** - Extract product families with specifications using VLM

6. **`3a_visualize_tables.py`** - Visualize detected tables (diagnostic tool)

7. **`3b_extract_products_vlm.py`** - Extract individual products using VLM

### Database Utilities
- Imports from canonical location: `database/db_utils.py`
- See `database/README.md` for database documentation

## Database Schema

The extraction uses the shared `harvested.db` database with an extended schema:

### New Table: `product_knowledge`
```sql
- pdf_name          -- Source PDF
- page_number       -- Page location
- category          -- "PRESSKOPPLINGAR"
- knowledge_type    -- "DESCRIPTION", "ASSEMBLY", "STANDARDS", "TOC"
- section_title     -- Section heading
- content           -- Full text content
- content_language  -- "sv" (Swedish)
```

### Existing Tables (Reused)
- `categories` - "PRESSKOPPLINGAR" (Chapter 4:2)
- `product_families` - Coupling families (4200-07, 4201-1, etc.)
- `products` - Individual coupling products
- Full-text search enabled via FTS5

## Prerequisites

### 1. Ollama with Vision Model
```bash
# Start Ollama server
ollama serve

# Pull a vision model
ollama pull qwen2-vl
```

### 2. Database Initialization
```bash
# Initialize database with schema
python database/db_utils.py --init

# Verify database status
python database/db_utils.py --verify
```

## Recommended Workflow

```bash
# 1. Initialize database
python database/db_utils.py --init

# 2. Extract knowledge (optional but recommended)
python Layer_1_Extraction/Layer_1b/0_extract_knowledge.py --pdf Press_Couplings.pdf --all

# 3. Convert PDF to images
python Layer_1_Extraction/Layer_1b/1_pdf_to_png.py Press_Couplings.pdf

# 4. Detect page structure
python Layer_1_Extraction/Layer_1b/2_detect_headers_footers.py

# 5. Extract categories
python Layer_1_Extraction/Layer_1b/2b_extract_categories.py --pdf Press_Couplings.pdf

# 6. Extract families
python Layer_1_Extraction/Layer_1b/3a_extract_families.py --pdf Press_Couplings.pdf

# 7. Extract products
python Layer_1_Extraction/Layer_1b/3b_extract_products_vlm.py --pdf Press_Couplings.pdf

# 8. Verify database
python database/db_utils.py --verify
```

## Output Locations
- **Database**: `database/harvested.db` (project root)
- **Images**: `Layer_1_Extraction/Layer_1b/data/png_pages/`
- **Visualizations**: `Layer_1_Extraction/Layer_1b/data/output/`
- **Tables**: `Layer_1_Extraction/Layer_1b/data/tables/` (JSON format)

## Validation

Check database status:
```bash
python ../Layer_1_Extraction/Layer_1a/db_utils.py --verify
```

Expected output:
```
📊 Database Status: database/harvested.db
==================================================
page_regions    ✅ EXISTS   (X rows)
categories      ✅ EXISTS   (X rows)
product_families ✅ EXISTS   (X rows)
products        ✅ EXISTS   (X rows)
product_knowledge ✅ EXISTS  (X rows)  ← New table
```

## Next Steps

1. ✅ Schema updated with `product_knowledge` table
2. ✅ Extraction scripts created
3. ⏳ Run preprocessing on coupling PDF
4. ⏳ Extract knowledge from intro pages
5. ⏳ Extract coupling products
6. ⏳ Validate extracted data
7. ⏳ Cross-reference with hose products

## Notes

- **Language**: All content preserved in Swedish
- **Thread standards**: G (ISO 228), JIC (SAE J514), ORFS, NPTF, BSP
- **Compatibility mapping**: Links to hose families via "Används med" field
- **Assembly diagrams**: Referenced but not extracted (manual process)

## Troubleshooting

### Ollama Connection Errors
```bash
# Ensure Ollama is running
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Database Errors
```bash
# Reinitialize database
python database/db_utils.py --init

# Check database status
python database/db_utils.py --verify
```

### Import Errors
- Ensure scripts run from project root
- Database utilities imported from `database/db_utils.py`
- Package should be installed: `pip install -e .`

## Migration from Layer 1a
Layer 1b provides:
- ✅ Standardized database schema
- ✅ Hierarchical data model
- ✅ Full-text search
- ✅ Better VLM integration
- ✅ Production-ready pipeline

To migrate, follow the recommended workflow above with your PDF.
