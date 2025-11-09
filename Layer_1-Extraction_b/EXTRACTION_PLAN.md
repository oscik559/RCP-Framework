# Extraction Plan: Produktbok_2020_Coupling.pdf

## Overview
This PDF contains press couplings (PRESSKOPPLINGAR) catalog - Chapter 4:2.
The extraction requires both knowledge capture and structured product data extraction.

## Phase 1: Knowledge Extraction (Intro Pages)

### Pages to Process: 167-169
These pages contain:
- Product group descriptions (PRODUKTGRUPP 420)
- Assembly instructions (MONTERINGSANVISNING)
- Standards and specifications
- General coupling information

### Database Extension Required:
```sql
-- Add to harvested_schema.sql
CREATE TABLE IF NOT EXISTS product_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_name TEXT NOT NULL,
    category TEXT,                         -- "PRESSKOPPLINGAR"
    knowledge_type TEXT,                   -- "DESCRIPTION", "ASSEMBLY", "STANDARDS", "TOC"
    section_title TEXT,                    -- Section heading
    content TEXT,                          -- Full extracted text
    page_number INTEGER,
    bounding_box TEXT,                     -- JSON: [x0, y0, x1, y1]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_pdf ON product_knowledge(pdf_name);
CREATE INDEX idx_knowledge_type ON product_knowledge(knowledge_type);
CREATE INDEX idx_knowledge_category ON product_knowledge(category);
```

### Extraction Method:
- Use text extraction (PDF is searchable)
- Identify sections by font size and formatting
- Preserve Swedish text exactly as-is
- Store assembly diagrams as separate image references

## Phase 2: Product Data Extraction (Pages 170+)

### Product Structure:
```
CATEGORY: PRESSKOPPLINGAR (Chapter 4:2)
├── FAMILY: Hylsa EN15C (PRODUKTGRUPP 420)
│   ├── 4200-07-04 (EN15C, 1/4")
│   ├── 4200-07-05 (EN15C, 5/16")
│   └── ...
├── FAMILY: Hylsa R1AT/DIN EN13N, 2SC
│   ├── 4200-11-03 (EN1RN, 2SC, 3/16")
│   ├── 4200-11-04 (EN1RN, 2SC, 1/4")
│   └── ...
├── FAMILY: G-gängade kopplingar (G-threaded)
│   ├── 4201-1 (60° kon, pressad mutter)
│   └── ...
└── FAMILY: JIC-gängade kopplingar (JIC-threaded)
    ├── 4213-1 (fty 74° kon, pressad mutter)
    └── ...
```

### Product Family Construction Details:
Store in JSON format in `product_families.construction_details`:
```json
{
  "connection_type": "PRESS COUPLING",
  "hose_compatibility": "Hylsa EN15C",
  "thread_standard": "EN 853 2SC / DIN EN 13N",
  "produktgrupp": "420",
  "assembly_method": "Press fitting",
  "standards": ["EN 853", "DIN EN 13N"],
  "features": ["Non conductive", "Heavy duty"],
  "recommended_for": "High pressure hydraulic hoses"
}
```

### Product Specifications:
Store in `products.specifications` as JSON:
```json
{
  "type": "COUPLING",
  "artikelnr": "4200-07-04",
  "anvands_med": "EN15C",
  "slang_id": "1/4\"",
  "thread_type": null,
  "thread_size": null,
  "kod": null,
  "page": 170
}
```

## Phase 3: Table Extraction Integration

### Pre-extract Tables:
Run `3_detect_tables.py` on the coupling PDF to extract structured table data.

### Table Structure Expected:
Tables contain columns like:
- Artikelnr (Article number)
- Används med / Avnänds med (Used with)
- Slang ID (Hose ID)
- Thread specifications
- Page references

## Implementation Steps

### Step 1: Create extraction script
```bash
cp Layer_1-Extraction/4_extract_product.py Layer_1-Extraction_b/1_extract_coupling_knowledge.py
```

Modify to:
1. Extract knowledge sections from intro pages
2. Store in new `product_knowledge` table
3. Preserve diagrams and images

### Step 2: Adapt product extraction
```bash
cp Layer_1-Extraction/4_extract_product.py Layer_1-Extraction_b/2_extract_coupling_products.py
```

Modify to:
1. Focus on coupling-specific structure
2. Handle different table formats (no dimensions tables, focus on compatibility)
3. Extract thread specifications correctly

### Step 3: PDF preprocessing
```bash
# Convert PDF to PNGs for VLM fallback
python Layer_1-Extraction/1_pdf_to_png.py --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf

# Detect headers/footers
python Layer_1-Extraction/2_detect_headers_footers.py --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf

# Extract tables
python Layer_1-Extraction/3_detect_tables.py --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf
```

## Key Differences from Hose Extraction

1. **No dimension tables**: Couplings focus on compatibility, not dimensions
2. **Thread specifications**: Critical for couplings (G-threads, JIC, SAE, etc.)
3. **Hose compatibility**: Each coupling specifies which hose types it works with
4. **Assembly instructions**: Important knowledge to capture separately
5. **Product groups**: Different grouping (by thread type vs. hose construction)

## Expected Output

### Database Population:
- **1 Category**: PRESSKOPPLINGAR
- **~15-20 Product Families**: Different coupling types
- **~200-300 Products**: Individual article numbers
- **~10-15 Knowledge Entries**: Assembly guides, descriptions, standards

### Knowledge Base:
- Assembly instructions with diagrams
- Product group descriptions
- Compatibility matrices
- Standards and specifications

## Next Steps After Extraction

1. **Validation**: Check extracted data against PDF
2. **Cross-referencing**: Link couplings to compatible hoses
3. **Search optimization**: Ensure FTS index includes coupling-specific terms
4. **API Integration**: Make coupling data available in Layer 3 application
