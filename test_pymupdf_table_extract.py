#!/usr/bin/env python3
"""
Test PyMuPDF's built-in table extraction (no VLM needed!)
"""
import fitz
from pathlib import Path
import json


def test_pymupdf_extraction():
    """Test if PyMuPDF can extract table content directly without VLM"""
    
    print("=== Testing PyMuPDF Built-in Table Extraction ===\n")
    
    pdf_path = Path("Layer_1-Extraction_b/Press_Couplings.pdf")
    doc = fitz.open(pdf_path)
    page = doc.load_page(4)  # Page 5 (0-indexed)
    
    print(f"✅ Loaded page 5\n")
    
    # Find tables using PyMuPDF
    tables = page.find_tables()
    
    print(f"Found {len(tables.tables)} tables\n")
    
    for i, table in enumerate(tables, 1):
        print(f"📊 Table {i}:")
        print(f"   BBox: {table.bbox}")
        print(f"   Rows: {table.row_count}")
        print(f"   Cols: {table.col_count}")
        
        # Extract table content using PyMuPDF's built-in extractor
        try:
            # Method 1: extract() - returns list of lists
            table_data = table.extract()
            
            print(f"   ✅ Extracted {len(table_data)} rows")
            
            # Show first few rows
            print(f"\n   Data preview:")
            for row_idx, row in enumerate(table_data[:5]):
                print(f"      Row {row_idx}: {row}")
            
            # Save to JSON
            output = {
                "page": 5,
                "table_id": i,
                "bbox": list(table.bbox),
                "rows": len(table_data),
                "columns": len(table_data[0]) if table_data else 0,
                "content": table_data,
                "extraction_method": "PyMuPDF_Native",
                "model": "none"
            }
            
            output_file = Path(f"test_pymupdf_table_{i}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"   💾 Saved to: {output_file}\n")
            
        except Exception as e:
            print(f"   ❌ Error extracting: {e}\n")
    
    doc.close()
    print("\n✅ Test complete!")
    print("\n💡 If tables extracted successfully, we don't need VLM at all!")


if __name__ == "__main__":
    test_pymupdf_extraction()
