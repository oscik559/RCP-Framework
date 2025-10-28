#!/usr/bin/env python3
"""
Table Detection and Bounding Box Visualization

This script detects tables in PDF pages using PyMuPDF and draws bounding boxes
around detected tables on the corresponding PNG images.
"""

import os
import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import json


class TableDetector:
    def __init__(self):
        """Initialize the TableDetector."""
        self.output_dir = Path("data/output")
        self.pages_dir = Path("data/pages")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_tables_in_pdf_page(self, pdf_path, page_number):
        """
        Detect tables in a PDF page using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-based)
            
        Returns:
            List of table dictionaries with bounding boxes and metadata
        """
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
        
        page = doc.load_page(page_number - 1)  # Convert to 0-based
        
        # Find tables using PyMuPDF's table detection
        tables = []
        
        try:
            # Get all tables on the page
            table_instances = page.find_tables()
            
            for i, table in enumerate(table_instances):
                # Get table bounding box
                bbox = table.bbox  # Returns (x0, y0, x1, y1)
                
                # Extract table content
                table_data = table.extract()
                
                # Count rows and columns
                rows = len(table_data) if table_data else 0
                cols = len(table_data[0]) if table_data and len(table_data) > 0 else 0
                
                table_info = {
                    "table_id": i + 1,
                    "bbox": list(bbox),
                    "rows": rows,
                    "columns": cols,
                    "area": (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                    "content_preview": table_data[:3] if table_data else []  # First 3 rows
                }
                
                tables.append(table_info)
                
                print(f"Table {i+1}: {rows}x{cols} at {bbox}")
        
        except Exception as e:
            print(f"Error detecting tables: {e}")
        
        # Alternative method: Look for text patterns that suggest tables
        if not tables:
            tables = self._detect_table_patterns(page)
        
        doc.close()
        return tables
    
    def _detect_table_patterns(self, page):
        """
        Fallback method to detect table-like structures using text analysis.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of detected table regions
        """
        tables = []
        
        # Get all text blocks
        blocks = page.get_text("dict")["blocks"]
        
        # Look for blocks with tabular data patterns
        table_candidates = []
        
        for block in blocks:
            if "lines" in block:
                # Analyze text patterns in this block
                lines = block["lines"]
                
                # Count lines with numeric data (potential table rows)
                numeric_lines = 0
                for line in lines:
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    
                    # Check if line contains numbers and separators (table-like)
                    if any(char.isdigit() for char in line_text) and \
                       any(sep in line_text for sep in ["\t", "  ", "|"]):
                        numeric_lines += 1
                
                # If many lines have numeric/tabular patterns, consider it a table
                if numeric_lines >= 3 and len(lines) >= 4:
                    bbox = block["bbox"]
                    table_info = {
                        "table_id": len(table_candidates) + 1,
                        "bbox": bbox,
                        "rows": len(lines),
                        "columns": "estimated",
                        "area": (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                        "detection_method": "text_pattern",
                        "content_preview": []
                    }
                    table_candidates.append(table_info)
        
        return table_candidates
    
    def scale_bbox_to_png(self, pdf_bbox, pdf_page_size, png_size, dpi=300):
        """
        Scale bounding box coordinates from PDF space to PNG image space.
        
        Args:
            pdf_bbox: [x0, y0, x1, y1] in PDF coordinate system
            pdf_page_size: (width, height) of PDF page in points
            png_size: (width, height) of PNG image in pixels
            dpi: DPI used when creating PNG
            
        Returns:
            Scaled bounding box [x0, y0, x1, y1] in PNG coordinates
        """
        # PDF coordinates are in points (72 DPI), PNG is at specified DPI
        scale_factor = dpi / 72.0
        
        # Calculate expected PNG size based on PDF page size
        expected_png_width = int(pdf_page_size[0] * scale_factor)
        expected_png_height = int(pdf_page_size[1] * scale_factor)
        
        # Calculate actual scaling factors
        x_scale = png_size[0] / expected_png_width
        y_scale = png_size[1] / expected_png_height
        
        # Apply scaling to bounding box
        x0 = int(pdf_bbox[0] * scale_factor * x_scale)
        y0 = int(pdf_bbox[1] * scale_factor * y_scale)
        x1 = int(pdf_bbox[2] * scale_factor * x_scale)
        y1 = int(pdf_bbox[3] * scale_factor * y_scale)
        
        return [x0, y0, x1, y1]
    
    def draw_table_boxes(self, png_path, tables, pdf_page_size, output_path):
        """
        Draw bounding boxes around detected tables on PNG image.
        
        Args:
            png_path: Path to PNG image
            tables: List of table dictionaries with bbox info
            pdf_page_size: (width, height) of original PDF page
            output_path: Path to save annotated image
        """
        # Open PNG image
        image = Image.open(png_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font for labels
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        
        for i, table in enumerate(tables):
            # Scale PDF bounding box to PNG coordinates
            pdf_bbox = table["bbox"]
            png_bbox = self.scale_bbox_to_png(
                pdf_bbox, 
                pdf_page_size, 
                image.size
            )
            
            # Choose color
            color = "red" 
            
            # Draw bounding box
            draw.rectangle(png_bbox, outline=color, width=3)
            
            # Add label
            label = f"Table {table['table_id']}"
            if table.get('rows') and table.get('columns'):
                label += f" ({table['rows']}x{table['columns']})"
            
            # Position label above the box
            label_x = png_bbox[0]
            label_y = max(0, png_bbox[1] - 25)
            
            # Draw label background
            bbox = draw.textbbox((label_x, label_y), label, font=font)
            draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], 
                          fill="white", outline=color)
            
            # Draw label text
            draw.text((label_x, label_y), label, fill=color, font=font)
        
        # Save annotated image
        image.save(output_path)
        print(f"Table detection visualization saved: {output_path}")
    
    def process_pdf_page(self, pdf_path, page_number, png_path=None):
        """
        Main method to detect tables and create visualization.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to process
            png_path: Optional path to existing PNG, otherwise will look in data/pages
            
        Returns:
            Dictionary with detection results
        """
        print(f"Detecting tables in PDF: {pdf_path}, Page: {page_number}")
        
        # Get PDF page dimensions
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        pdf_page_size = (page.rect.width, page.rect.height)
        doc.close()
        
        # Detect tables
        tables = self.detect_tables_in_pdf_page(pdf_path, page_number)
        
        if not tables:
            print(f"No tables detected on page {page_number}")
            return {"page": page_number, "tables": [], "png_path": png_path}
        
        print(f"Detected {len(tables)} table(s) on page {page_number}")
        
        # Determine PNG path
        if png_path is None:
            pdf_name = Path(pdf_path).stem
            png_filename = f"{pdf_name}_page_{page_number:03d}.png"
            png_path = self.pages_dir / png_filename
        
        if not png_path.exists():
            print(f"Warning: PNG file not found: {png_path}")
            print("You may need to run pdf_to_png.py first to generate PNG files.")
            return {"page": page_number, "tables": tables, "png_path": None}
        
        # Create output visualization
        pdf_name = Path(pdf_path).stem
        output_filename = f"{pdf_name}_page_{page_number:03d}_tables.png"
        output_path = self.output_dir / output_filename
        
        # Draw table bounding boxes
        self.draw_table_boxes(png_path, tables, pdf_page_size, output_path)
        
        # Save table detection results as JSON
        json_filename = f"{pdf_name}_page_{page_number:03d}_tables.json"
        json_path = self.output_dir / json_filename
        
        results = {
            "page": page_number,
            "pdf_page_size": pdf_page_size,
            "png_size": Image.open(png_path).size,
            "tables": tables,
            "visualization": str(output_path),
            "detection_summary": {
                "total_tables": len(tables),
                "largest_table": max(tables, key=lambda t: t["area"])["table_id"] if tables else None,
                "total_area": sum(t["area"] for t in tables)
            }
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Detection results saved: {json_path}")
        
        return results

    def process_all_pages(self, pdf_path):
        """
        Process all pages in a PDF for table detection.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with results for all pages
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        print(f"Processing {total_pages} pages from {pdf_path}")
        
        all_results = {
            "pdf_path": str(pdf_path),
            "total_pages": total_pages,
            "pages": {},
            "summary": {
                "pages_with_tables": 0,
                "total_tables": 0,
                "pages_processed": 0
            }
        }
        
        for page_num in range(1, total_pages + 1):
            try:
                print(f"\n--- Processing page {page_num}/{total_pages} ---")
                results = self.process_pdf_page(pdf_path, page_num)
                
                all_results["pages"][page_num] = results
                all_results["summary"]["pages_processed"] += 1
                
                if results["tables"]:
                    all_results["summary"]["pages_with_tables"] += 1
                    all_results["summary"]["total_tables"] += len(results["tables"])
                
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                all_results["pages"][page_num] = {
                    "page": page_num,
                    "error": str(e),
                    "tables": []
                }
        
        # Save overall summary
        pdf_name = Path(pdf_path).stem
        summary_path = self.output_dir / f"{pdf_name}_all_tables_summary.json"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Total pages processed: {all_results['summary']['pages_processed']}")
        print(f"Pages with tables: {all_results['summary']['pages_with_tables']}")
        print(f"Total tables detected: {all_results['summary']['total_tables']}")
        print(f"Summary saved: {summary_path}")
        
        return all_results


def main():
    parser = argparse.ArgumentParser(description="Detect tables in PDF pages and visualize on PNG images")
    parser.add_argument("--pdf-path", default="PDF/Produktbok.pdf", help="Path to PDF file (default: PDF/Produktbok.pdf)")
    parser.add_argument("--page", type=int, help="Specific page number to process (omit to process all pages)")
    parser.add_argument("--png-path", help="Optional path to specific PNG file (only works with --page)")
    parser.add_argument("--all-pages", action="store_true", help="Process all pages in the PDF")
    
    args = parser.parse_args()
    
    # Check if PDF exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Initialize detector
    detector = TableDetector()
    
    try:
        # Determine processing mode
        if args.all_pages or args.page is None:
            # Process all pages
            results = detector.process_all_pages(pdf_path)
        else:
            # Process single page
            results = detector.process_pdf_page(
                pdf_path, 
                args.page, 
                png_path=Path(args.png_path) if args.png_path else None
            )
            
            # Print single page summary
            tables = results["tables"]
            if tables:
                print(f"\n=== Table Detection Summary ===")
                print(f"Page: {results['page']}")
                print(f"Tables detected: {len(tables)}")
                for table in tables:
                    print(f"  Table {table['table_id']}: {table['rows']}x{table.get('columns', '?')} "
                          f"at {table['bbox']} (area: {table['area']:.0f})")
            else:
                print(f"\nNo tables detected on page {args.page}")
            
    except Exception as e:
        print(f"Error during table detection: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()