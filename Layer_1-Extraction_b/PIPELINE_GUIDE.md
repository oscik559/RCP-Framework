# Layer_1-Extraction_b Pipeline Setup

## Directory Structure

```
Layer_1-Extraction_b/
├── Press_Couplings.pdf          # Source PDF
├── 0_extract_knowledge.py       # Optional: Extract intro/description pages
├── 1_pdf_to_png.py              # Step 1: Convert PDF to PNG
├── 2_detect_headers_footers.py  # Step 2: Detect page regions
├── 3_detect_tables.py           # Step 3: Detect and bbox tables
├── 4_extract_product.py         # Step 4: Extract products
├── db_utils.py                  # Database utilities
├── run_pipeline.sh              # Automated pipeline runner
└── data/                        # All extracted data goes here
    ├── database/
    │   ├── harvested.db         # Production database
    │   └── harvested_test.db    # Test database
    ├── pdf_pages/               # Individual PDF pages
    │   ├── page_001.pdf
    │   ├── page_002.pdf
    │   └── ...
    ├── png_pages/               # PNG images of pages
    │   ├── page_001.png
    │   ├── page_002.png
    │   └── ...
    └── tables/                  # Extracted table data
        ├── page_002_table_1.json
        ├── page_002_tables_visualization.png
        └── ...
```

## Pipeline Steps

### Step 1: Convert PDF to PNG and Extract Pages

```bash
cd /Users/worktime/Desktop/Project_Hydroscand-Hoses

# Convert pages 1-10 (modify range as needed)
./Layer_1-Extraction_b/run_pipeline.sh 1 10
```

This will:
- ✅ Create `data/png_pages/page_XXX.png` (for visualization)
- ✅ Create `data/pdf_pages/page_XXX.pdf` (for text extraction)
- ✅ Detect headers/footers and save to database

### Step 2: Detect Tables on Specific Pages

```bash
cd Layer_1-Extraction_b

# Detect tables on page 2 (PRODUKTGRUPP 420)
uv run python 3_detect_tables.py --pdf Press_Couplings.pdf --page 2

# Or detect on multiple pages
uv run python 3_detect_tables.py --pdf Press_Couplings.pdf --pages 2-10
```

This will:
- ✅ Detect table bounding boxes
- ✅ Extract table content using VLM
- ✅ Save to `data/tables/page_XXX_table_Y.json`
- ✅ Create visualization PNG with bboxes

### Step 3: Extract Products

```bash
cd Layer_1-Extraction_b

# Extract from page with --test flag (uses harvested_test.db)
uv run python 4_extract_product.py --page 2 --test

# Extract from page range
uv run python 4_extract_product.py --pages 2-10 --test
```

This will:
- ✅ Load pre-extracted table data
- ✅ Parse product families and products
- ✅ Save to database (test or production)

## Current Status

### ✅ Completed:
- [x] PNG pages created (pages 1-5)
- [x] PDF pages created (pages 1-5)
- [x] Header/footer detection completed (all 26 pages)
- [x] Database schema updated with product_knowledge table
- [x] Test database created

### ⏳ Next Steps:
1. Run table detection on product pages
2. Test product extraction on page 2
3. Verify extracted data
4. Run full pipeline on all product pages

## Quick Commands Reference

```bash
# From project root
cd /Users/worktime/Desktop/Project_Hydroscand-Hoses

# Run full pipeline for pages 1-26
./Layer_1-Extraction_b/run_pipeline.sh 1 26

# Detect tables on page 2
cd Layer_1-Extraction_b
uv run python 3_detect_tables.py --pdf Press_Couplings.pdf --page 2

# Extract products from page 2 (test mode)
uv run python 4_extract_product.py --page 2 --test

# Verify database
uv run python db_utils.py --db-path data/database/harvested_test.db --verify

# Check what was extracted
sqlite3 data/database/harvested_test.db "SELECT COUNT(*) FROM products;"
```

## Important Notes

- **All paths are relative to Layer_1-Extraction_b/** when running scripts from that folder
- **Database files**: `data/database/harvested.db` (production) and `data/database/harvested_test.db` (testing)
- **Always use --test flag** during testing to avoid touching production database
- **Table data**: Saved in `data/tables/` as JSON files
- **Images**: Both PNG and PDF formats saved for flexibility

## Troubleshooting

### Database path errors
- Make sure you're running from `Layer_1-Extraction_b/` directory
- Database will be created at `data/database/harvested.db` relative to where you run from

### Missing PNG files
- Run the pipeline script first: `./run_pipeline.sh 1 10`
- Check `data/png_pages/` folder exists

### Table detection fails
- Ensure PNG pages exist first
- Check that PDF path is correct relative to current directory
