# ✅ Database Schema & Extraction Scripts - READY!

## Status: COMPLETE ✅

The database schema has been successfully updated and extraction scripts have been created for the coupling catalog.

---

## 1️⃣ Database Schema - UPDATED ✅

### New Table Added: `product_knowledge`

```sql
CREATE TABLE IF NOT EXISTS product_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_name TEXT NOT NULL,
    page_number INTEGER,
    category TEXT,
    knowledge_type TEXT NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    content_language TEXT DEFAULT 'sv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Features:
- ✅ Full-text search enabled (FTS5)
- ✅ Automatic triggers for search index sync
- ✅ Indexes on pdf_name, page_number, category, knowledge_type
- ✅ Knowledge types: DESCRIPTION, ASSEMBLY, STANDARDS, TOC, INTRO, TECHNICAL, SAFETY, OTHER

### Database Verification:
```bash
$ python3 Layer_1-Extraction/db_utils.py --verify

📊 Database Status: data/database/harvested.db
==================================================
page_regions      ✅ EXISTS   (40 rows)
categories        ✅ EXISTS   (1 rows)
product_families  ✅ EXISTS   (69 rows)
products          ✅ EXISTS   (335 rows)
product_knowledge ✅ EXISTS   (0 rows)  ← NEW TABLE READY
```

---

## 2️⃣ Extraction Scripts - CREATED ✅

### Script 1: `1_extract_knowledge.py`

**Purpose:** Extract product knowledge from intro/reference pages

**Features:**
- Text extraction with section identification
- Automatic section type classification
- Saves to `product_knowledge` table
- Preserves Swedish text

**Usage:**
```bash
# Extract knowledge from specific pages
python3 Layer_1-Extraction_b/1_extract_knowledge.py \
  --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf \
  --pages 167-169 \
  --category "PRESSKOPPLINGAR"

# Extract from all pages
python3 Layer_1-Extraction_b/1_extract_knowledge.py \
  --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf \
  --pages all \
  --category "PRESSKOPPLINGAR"
```

**Extracts:**
- Assembly instructions (MONTERINGSANVISNING)
- Product group descriptions (PRODUKTGRUPP 420)
- Standards and specifications
- Table of contents (INNEHÅLL)
- Technical information
- Safety guidelines

---

### Script 2: `2_extract_couplings.py`

**Purpose:** Extract coupling products from catalog pages

**Features:**
- Table-based extraction
- Thread specification parsing
- Hose compatibility mapping
- Hierarchical storage (category → family → product)

**Usage:**
```bash
# Extract from single page
python3 Layer_1-Extraction_b/2_extract_couplings.py \
  --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf \
  --page 170

# Extract from page range
python3 Layer_1-Extraction_b/2_extract_couplings.py \
  --pdf Layer_1-Extraction_b/Produktbok_2020_Coupling.pdf \
  --pages 170-180
```

**Extracts:**
- Product families (Hylsa EN15C, G-gängade, JIC-gängade, etc.)
- Individual coupling products with specifications
- Thread types (G-thread, JIC, SAE, ORFS, etc.)
- Hose compatibility information

---

## 3️⃣ Supporting Documentation - CREATED ✅

### Files Created:

1. **`EXTRACTION_PLAN.md`** - Detailed extraction strategy
2. **`README.md`** - Usage guide and documentation
3. **Updated `harvested_schema.sql`** - Extended database schema
4. **Updated `db_utils.py`** - Includes product_knowledge in checks

---

## 4️⃣ Next Steps - ACTION REQUIRED ⏳

### Before Running Extraction:

1. **Install Python dependencies** (if not already installed):
   ```bash
   pip install pymupdf  # For PyMuPDF (fitz)
   ```

2. **Verify PDF location:**
   ```bash
   ls -la Layer_1-Extraction_b/*.pdf
   ```
   - Found: `Press_Couplings.pdf`
   - May need to rename or use this file

3. **Run preprocessing** (if tables not extracted yet):
   ```bash
   # Extract tables from the coupling PDF
   python3 Layer_1-Extraction/3_detect_tables.py \
     --pdf Layer_1-Extraction_b/Press_Couplings.pdf \
     --all-pages
   ```

### Recommended Extraction Sequence:

```bash
# Step 1: Extract knowledge from intro pages
python3 Layer_1-Extraction_b/1_extract_knowledge.py \
  --pdf Layer_1-Extraction_b/Press_Couplings.pdf \
  --pages 167-169 \
  --category "PRESSKOPPLINGAR"

# Step 2: Extract coupling products
python3 Layer_1-Extraction_b/2_extract_couplings.py \
  --pdf Layer_1-Extraction_b/Press_Couplings.pdf \
  --pages 170-180

# Step 3: Verify results
python3 Layer_1-Extraction/db_utils.py --verify
```

---

## 5️⃣ Key Differences from Hose Extraction

| Aspect | Hose Catalog | Coupling Catalog |
|--------|-------------|------------------|
| **Tables** | Dimension tables (ID, OD, pressure) | Compatibility tables (thread, hose) |
| **Key Specs** | Dimensions, pressure ratings | Thread type, hose compatibility |
| **Product Groups** | By construction type | By thread standard |
| **Knowledge** | Construction details | Assembly instructions |
| **Standards** | EN 857, DNV, MSHA | G-thread, JIC, SAE, ORFS |

---

## 6️⃣ Files Updated

### Modified:
- ✅ `Layer_1-Extraction/harvested_schema.sql` - Added product_knowledge table
- ✅ `Layer_1-Extraction/db_utils.py` - Updated table checks

### Created:
- ✅ `Layer_1-Extraction_b/1_extract_knowledge.py`
- ✅ `Layer_1-Extraction_b/2_extract_couplings.py`
- ✅ `Layer_1-Extraction_b/README.md`
- ✅ `Layer_1-Extraction_b/EXTRACTION_PLAN.md`

---

## 7️⃣ Database Schema Summary

```
🗄️ harvested.db
├── page_regions (40 rows)
├── categories (1 row)
│   └── Will add: PRESSKOPPLINGAR (4:2)
├── product_families (69 rows)
│   └── Will add: Coupling families (4200-07, 4201-1, etc.)
├── products (335 rows)
│   └── Will add: Individual coupling products
└── product_knowledge (0 rows) ← NEW!
    └── Will add: Assembly instructions, descriptions, standards

📚 Full-text search tables:
├── product_families_fts
└── product_knowledge_fts ← NEW!
```

---

## 8️⃣ Ready to Extract! 🚀

**Everything is prepared and ready to go:**

✅ Database schema extended
✅ Extraction scripts created
✅ Documentation written
✅ Database initialized

**Just need to:**
1. Install PyMuPDF if needed: `pip install pymupdf`
2. Verify PDF location
3. Run the extraction scripts!

---

## Questions?

- **Schema location:** `Layer_1-Extraction/harvested_schema.sql`
- **Database location:** `data/database/harvested.db`
- **Scripts location:** `Layer_1-Extraction_b/`
- **Documentation:** `Layer_1-Extraction_b/README.md`
