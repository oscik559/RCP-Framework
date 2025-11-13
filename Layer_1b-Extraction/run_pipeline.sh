#!/bin/bash
# Coupling Extraction Pipeline Runner
# This script runs the complete extraction pipeline for the coupling catalog

set -e  # Exit on error

PDF_FILE="Press_Couplings.pdf"
PDF_PATH="Layer_1b-Extraction/${PDF_FILE}"
START_PAGE=${1:-1}
END_PAGE=${2:-10}

echo "========================================="
echo "Coupling Extraction Pipeline"
echo "========================================="
echo "PDF: $PDF_FILE"
echo "Pages: $START_PAGE to $END_PAGE"
echo "========================================="

# Step 1: Convert PDF to PNG and extract pages
echo ""
echo "📄 Step 1: Converting PDF to PNG and extracting pages..."
uv run python -c "
import fitz
from pathlib import Path

# Create output directories
Path('Layer_1b-Extraction/data/png_pages').mkdir(parents=True, exist_ok=True)
Path('Layer_1b-Extraction/data/pdf_pages').mkdir(parents=True, exist_ok=True)

# Open PDF
doc = fitz.open('$PDF_PATH')
total_pages = doc.page_count
print(f'Total pages in PDF: {total_pages}')

# Convert pages
for page_num in range($START_PAGE - 1, min($END_PAGE, total_pages)):
    page = doc.load_page(page_num)
    
    # Save as PNG (300 DPI)
    zoom = 300 / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    png_path = f'Layer_1b-Extraction/data/png_pages/page_{page_num + 1:03d}.png'
    pix.save(png_path)
    print(f'  ✅ Saved: page_{page_num + 1:03d}.png')
    
    # Extract individual PDF page
    pdf_out = fitz.open()
    pdf_out.insert_pdf(doc, from_page=page_num, to_page=page_num)
    pdf_path = f'Layer_1b-Extraction/data/pdf_pages/page_{page_num + 1:03d}.pdf'
    pdf_out.save(pdf_path)
    pdf_out.close()
    print(f'  ✅ Saved: page_{page_num + 1:03d}.pdf')

doc.close()
print(f'✅ Step 1 complete: {min($END_PAGE, total_pages) - $START_PAGE + 1} pages processed')
"

# Step 2: Detect headers and footers
echo ""
echo "📏 Step 2: Detecting headers and footers..."
cd Layer_1b-Extraction
uv run python 2_detect_headers_footers.py --pdf ../Layer_1b-Extraction/$PDF_FILE
cd ..

echo ""
echo "✅ Pipeline setup complete!"
echo "Next steps:"
echo "  - Run table detection: uv run python Layer_1b-Extraction/3_detect_tables.py --pdf Layer_1b-Extraction/$PDF_FILE --page <PAGE>"
echo "  - Run product extraction: uv run python Layer_1b-Extraction/4_extract_product.py --page <PAGE> --test"
