# Centralized Database Structure

## ✅ Completed Reorganization

### Directory Structure

```
Project_Hydroscand-Hoses/
├── data/
│   └── database/              # 🎯 CENTRALIZED DATABASE
│       ├── db_utils.py        # Database utilities (shared)
│       ├── harvested_schema.sql  # Schema definition (shared)
│       ├── harvested.db       # Production database
│       └── harvested_test.db  # Test database
│
├── Layer_1a_Extraction/        # Hose extraction
│   ├── 1_pdf_to_png.py
│   ├── 2_detect_headers_footers.py  # imports from database/
│   ├── 3_detect_tables.py           # imports from database/
│   ├── 4_extract_product.py         # imports from database/
│   └── 5_extract_images.py
│
└── Layer_1b_Extraction/      # Coupling extraction
    ├── Press_Couplings.pdf
    ├── 0_extract_knowledge.py       # imports from database/
    ├── 1_pdf_to_png.py
    ├── 2_detect_headers_footers.py  # imports from database/
    ├── 3_detect_tables.py           # imports from database/
    ├── 4_extract_product.py         # imports from database/
    ├── run_pipeline.sh
    └── data/                   # Coupling-specific data
        ├── pdf_pages/
        ├── png_pages/
        └── tables/
```

## Benefits

✅ **Single source of truth** for database schema
✅ **Unified database utilities** - no duplication
✅ **Easy maintenance** - update in one place
✅ **Both hose and coupling data** in same database
✅ **Consistent imports** across all scripts

## Import Pattern

All scripts now use:
```python
import sys
from pathlib import Path

# Add database to path
sys.path.append(str(Path(__file__).parent.parent / "database"))
from db_utils import DatabaseManager
```

## Database Access

### From Any Script:
```python
# Production database
db_manager = DatabaseManager("database/harvested.db")

# Test database  
db_manager = DatabaseManager("database/harvested_test.db")
```

### From Command Line:
```bash
# Verify production database
uv run python database/db_utils.py --verify

# Verify test database
uv run python database/db_utils.py \
  --db-path database/harvested_test.db \
  --verify
```

## Next Steps

Now that the structure is clean, you can:

1. **Run table detection** on coupling pages
   ```bash
   cd Layer_1b_Extraction
   uv run python 3_detect_tables.py --pdf-path Press_Couplings.pdf --page 2
   ```

2. **Extract products** using the test database
   ```bash
   cd Layer_1b_Extraction
   uv run python 4_extract_product.py --page 2 --test
   ```

3. **Query both hose and coupling data** from single database
   ```bash
   sqlite3 database/harvested.db
   > SELECT COUNT(*) FROM products;
   > SELECT * FROM product_knowledge LIMIT 5;
   ```
