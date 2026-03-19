# Layer 1a: Basic Extraction Scripts (Legacy)

## Overview
This directory contains the **original/legacy** extraction scripts for processing PDF catalogs. These scripts provide basic extraction functionality and serve as reference implementations.

**Status**: Legacy - maintained for reference and simple extraction tasks  
**Current Production**: See `Layer_1_Extraction/Layer_1b` for the actively maintained pipeline

## Purpose
- PDF to PNG conversion
- Header/footer detection  
- Table detection using PyMuPDF
- Basic product extraction using Vision Language Models (VLM)
- Image extraction from PDFs

## Scripts

### 1. `1_pdf_to_png.py`
Converts PDF pages to high-resolution PNG images.

```bash
python Layer_1_Extraction/Layer_1a/1_pdf_to_png.py Layer_1_Extraction/Layer_1a/High-Pressure_Hose.pdf
```

**Output**: `Layer_1_Extraction/Layer_1a/data/png_pages/` - PNG images of each page

### 2. `2_detect_headers_footers.py`
Identifies and marks header/footer regions on pages.

```bash
python Layer_1_Extraction/Layer_1a/2_detect_headers_footers.py
```

### 3. `3_detect_tables.py`
Detects tables in PDF pages using PyMuPDF's built-in table detection.

```bash
python Layer_1_Extraction/Layer_1a/3_detect_tables.py
```

**Output**: `Layer_1_Extraction/Layer_1a/data/tables/` - JSON files with table data

### 4. `4_extract_product.py`
Extracts product specifications using Vision Language Models (Ollama + Qwen).

```bash
python Layer_1_Extraction/Layer_1a/4_extract_product.py Layer_1_Extraction/Layer_1a/High-Pressure_Hose.pdf --page 31
```

**Options**:
- `--page N`: Extract from specific page number
- `--ollama-url URL`: Ollama API endpoint (default: http://localhost:11434)
- `--model NAME`: VLM model (default: qwen2-vl)

### 5. `5_extract_images.py`
Extracts embedded images from PDF pages.

```bash
python Layer_1_Extraction/Layer_1a/5_extract_images.py
```

**Output**: `Layer_1_Extraction/Layer_1a/data/output/` - Extracted images

## Sample Data
- `High-Pressure_Hose.pdf` - Sample hydraulic hose catalog (Swedish)

## Requirements
- **Ollama** with vision model (qwen2-vl or similar)
- **PyMuPDF** (fitz) for PDF processing
- **Pillow** for image handling

## Output Locations

All Layer 1a outputs are stored in `Layer_1_Extraction/Layer_1a/data/`:

- `Layer_1_Extraction/Layer_1a/data/png_pages/` - PNG conversions of PDF pages
- `Layer_1_Extraction/Layer_1a/data/tables/` - Extracted table data (JSON format)
- `Layer_1_Extraction/Layer_1a/data/output/` - Visualization images with bounding boxes
- `Layer_1_Extraction/Layer_1a/data/exports/` - CSV/Excel exports (if applicable)

**Core databases** are in project root:
- `database/harvested.db` - Product database
- `database/agentic.db` - Workflow state

## Migration to Layer 1b
If you need advanced features:
- Hierarchical extraction (Categories → Families → Products)
- Standardized database schema (`database/harvested.db`)
- Knowledge extraction from intro pages
- Full-text search indexing

→ **Use Layer 1b instead**: See `Layer_1_Extraction/Layer_1b/README.md`

## Notes
- Scripts are designed to run independently
- Some scripts may require Ollama server running (`ollama serve`)
- Output paths are configured for project root execution
- These scripts are maintained for backward compatibility and simple tasks
