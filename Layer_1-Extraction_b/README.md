# Layer 1-Extraction_b: Coupling Catalog Extraction

This folder contains specialized extraction scripts for the **Produktbok_2020_Coupling.pdf** catalog.

## Overview

The coupling catalog (Chapter 4:2 - PRESSKOPPLINGAR) has a different structure than the hose catalog and requires specialized extraction:

- **Knowledge-heavy intro pages** (167-169) with assembly instructions, standards, and descriptions
- **Different product hierarchy** - organized by thread type and hose compatibility
- **Different table structures** - no dimension columns, focus on compatibility

## Files

### Extraction Scripts

1. **`1_extract_knowledge.py`** - Extract product knowledge from intro pages
   - Assembly instructions (MONTERINGSANVISNING)
   - Product descriptions (PRODUKTGRUPP 420)
   - Standards and specifications
   - Table of contents (INNEHÅLL)

2. **`2_extract_couplings.py`** - Extract coupling products from catalog pages
   - Product families (Hylsa EN15C, G-gängade, JIC-gängade, etc.)
   - Individual coupling products with specifications
   - Thread types and compatibility

### Supporting Files

- **`EXTRACTION_PLAN.md`** - Detailed extraction strategy and planning
- **`Produktbok_2020_Coupling.pdf`** - Source catalog (Chapter 4:2)

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

## Usage

### Step 1: Extract Knowledge (Intro Pages)

```bash
# Extract knowledge from intro pages 167-169
python 1_extract_knowledge.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --pages 167-169 \
  --category "PRESSKOPPLINGAR"

# Or extract from all pages
python 1_extract_knowledge.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --pages all \
  --category "PRESSKOPPLINGAR"
```

### Step 2: Run Preprocessing (If Not Done)

```bash
# Convert PDF to PNGs (for VLM fallback)
python ../Layer_1-Extraction/1_pdf_to_png.py \
  --pdf Produktbok_2020_Coupling.pdf

# Detect headers/footers
python ../Layer_1-Extraction/2_detect_headers_footers.py \
  --pdf Produktbok_2020_Coupling.pdf

# Extract tables
python ../Layer_1-Extraction/3_detect_tables.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --page 170
```

### Step 3: Extract Coupling Products

```bash
# Extract from single page
python 2_extract_couplings.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --page 170

# Extract from page range
python 2_extract_couplings.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --pages 170-180
```

## Product Structure

### Category
```
PRESSKOPPLINGAR (Chapter 4:2)
```

### Product Families (Examples)
```
├── Hylsa EN15C (4200-07)
├── Hylsa R1AT/DIN EN13N, 2SC (4200-11)
├── Hylsa EN2SN (4200-12)
├── Hylsa 15N/25N/25C (4200-22)
├── Hylsa EN4SP/4SH (4200-19)
├── G-gängade kopplingar (4201-x series)
├── JIC-gängade kopplingar (4213-x series)
├── Metriskt gängade (4279-x series)
├── ORFS-kopplingar (4290-x series)
└── etc.
```

### Product Specifications (JSON)
```json
{
  "type": "COUPLING",
  "artikelnr": "4200-07-04",
  "used_with": "EN15C",
  "hose_id": "1/4\"",
  "thread_type": null,
  "thread_size": null,
  "page": 170
}
```

## Key Differences from Hose Extraction

1. **No dimension tables** - Couplings don't have ID/OD/pressure tables
2. **Thread specifications** - Critical: G-thread, JIC, SAE, ORFS, NPTF
3. **Hose compatibility** - Each coupling lists compatible hoses
4. **Assembly knowledge** - Important to capture separately
5. **Product grouping** - By thread type, not construction

## Validation

Check database status:
```bash
python ../Layer_1-Extraction/db_utils.py --verify
```

Expected output:
```
📊 Database Status: data/database/harvested.db
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

**No tables found:**
```bash
# Run table detection first
python ../Layer_1-Extraction/3_detect_tables.py \
  --pdf Produktbok_2020_Coupling.pdf \
  --page <PAGE_NUMBER>
```

**Import errors:**
```bash
# Ensure you're in the project root directory
cd /Users/worktime/Desktop/Project_Hydroscand-Hoses
python Layer_1-Extraction_b/1_extract_knowledge.py --help
```

**Database not found:**
```bash
# Initialize database
python Layer_1-Extraction/db_utils.py --init
```
