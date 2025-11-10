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
import sqlite3
import requests
import base64
from io import BytesIO
sys.path.append(str(Path(__file__).parent.parent / "data" / "database"))
from db_utils import DatabaseManager


class TableDetector:
    def __init__(self):
        """Initialize the TableDetector."""
        # Get script directory for relative paths
        self.script_dir = Path(__file__).parent
        self.pages_dir = self.script_dir / "data/png_pages"
        self.tables_dir = self.script_dir / "data/tables"
        self.db_manager = DatabaseManager()
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        self.db_manager.init_database()
    
    def get_exclusion_regions(self, pdf_name, page_number):
        """
        Get header/footer regions from database to exclude from table detection.
        
        Args:
            pdf_name: PDF filename (without extension)
            page_number: Page number
            
        Returns:
            Dictionary with header and footer regions, or None if not found
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT page_width, page_height, header_x0, header_y0, header_x1, header_y1,
                   footer_x0, footer_y0, footer_x1, footer_y1
            FROM page_regions 
            WHERE pdf_name = ? AND page_number = ?
        ''', (pdf_name, page_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            "page_size": [result[0], result[1]],
            "header_region": fitz.Rect(result[2], result[3], result[4], result[5]),
            "footer_region": fitz.Rect(result[6], result[7], result[8], result[9])
        }
    
    def separate_columns(self, tables, page_width=595):
        """
        Separate tables into left and right columns based on page layout.
        
        Args:
            tables: List of table dictionaries with bbox
            page_width: Page width in points (default 595 for A4)
            
        Returns:
            Tuple of (left_column_tables, right_column_tables)
        """
        column_mid = page_width / 2  # ~297 points for A4
        
        left_col = []
        right_col = []
        
        for table in tables:
            table_center_x = (table["bbox"][0] + table["bbox"][2]) / 2
            
            if table_center_x < column_mid:
                left_col.append(table)
            else:
                right_col.append(table)
        
        # Sort each column by vertical position (top to bottom)
        left_col.sort(key=lambda t: t["bbox"][1])
        right_col.sort(key=lambda t: t["bbox"][1])
        
        return left_col, right_col
    
    def merge_column_tables(self, column_tables, merge_threshold=50):
        """
        Merge tables within a single column that are vertically adjacent.
        
        Args:
            column_tables: List of tables in one column, sorted top to bottom
            merge_threshold: Maximum vertical gap to consider for merging (default: 50 points)
            
        Returns:
            List of merged table dictionaries
        """
        if len(column_tables) <= 1:
            return column_tables
        
        merged = []
        current_group = [column_tables[0]]
        
        for i in range(1, len(column_tables)):
            current = column_tables[i]
            last_in_group = current_group[-1]
            
            # Calculate vertical gap
            vertical_gap = current["bbox"][1] - last_in_group["bbox"][3]
            
            # Calculate width similarity
            last_width = last_in_group["bbox"][2] - last_in_group["bbox"][0]
            current_width = current["bbox"][2] - current["bbox"][0]
            width_ratio = min(last_width, current_width) / max(last_width, current_width) if max(last_width, current_width) > 0 else 0
            
            # COLUMN-AWARE merging criteria:
            # 1. Small vertical gap (<50 points - tables close together)
            # 2. Similar widths (>80% - same column width)
            # 3. Positive gap (no overlaps)
            should_merge = (
                0 < vertical_gap < merge_threshold and
                width_ratio > 0.80
            )
            
            if should_merge:
                current_group.append(current)
            else:
                # Finalize current group and start new one
                if len(current_group) > 1:
                    # Merge the group into one table
                    merged_table = self._merge_table_group(current_group)
                    merged.append(merged_table)
                else:
                    merged.append(current_group[0])
                
                current_group = [current]
        
        # Don't forget the last group
        if len(current_group) > 1:
            merged_table = self._merge_table_group(current_group)
            merged.append(merged_table)
        else:
            merged.append(current_group[0])
        
        # Re-assign table IDs
        for idx, table in enumerate(merged, 1):
            table["table_id"] = idx
        
        return merged
    
    def _merge_table_group(self, table_group):
        """
        Merge a group of tables into a single table with combined bbox.
        
        Args:
            table_group: List of table dictionaries to merge
            
        Returns:
            Merged table dictionary
        """
        # Calculate combined bounding box
        min_x0 = min(t["bbox"][0] for t in table_group)
        min_y0 = min(t["bbox"][1] for t in table_group)
        max_x1 = max(t["bbox"][2] for t in table_group)
        max_y1 = max(t["bbox"][3] for t in table_group)
        
        combined_bbox = [min_x0, min_y0, max_x1, max_y1]
        
        merged_table = {
            "table_id": table_group[0]["table_id"],
            "bbox": combined_bbox,
            "rows": 0,  # Will be updated after VLM extraction
            "columns": 0,
            "area": (max_x1 - min_x0) * (max_y1 - min_y0),
            "content": [],
            "merged_from": len(table_group)
        }
        
        return merged_table
    
    def is_table_in_exclusion_zone(self, table_bbox, exclusion_regions):
        """
        Check if a table intersects with header or footer exclusion regions.
        
        Args:
            table_bbox: Table bounding box as fitz.Rect or [x0, y0, x1, y1]
            exclusion_regions: Dictionary with header_region and footer_region
            
        Returns:
            True if table should be excluded, False otherwise
        """
        if not exclusion_regions:
            return False
        
        # Convert to fitz.Rect if needed
        if isinstance(table_bbox, list):
            table_rect = fitz.Rect(table_bbox)
        else:
            table_rect = table_bbox
        
        # Check if table intersects with header or footer regions
        header_intersects = table_rect.intersects(exclusion_regions["header_region"])
        footer_intersects = table_rect.intersects(exclusion_regions["footer_region"])
        
        return header_intersects or footer_intersects
    
    def detect_tables_in_pdf_page(self, pdf_path, page_number):
        """
        Detect tables in a PDF page using PyMuPDF, excluding header/footer regions.
        
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
        
        # Get exclusion regions from database
        pdf_name = Path(pdf_path).stem
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        if exclusion_regions:
            print(f"Using exclusion regions - Header: {exclusion_regions['header_region']}, Footer: {exclusion_regions['footer_region']}")
        else:
            print("No exclusion regions found in database")
        
        # Find tables using PyMuPDF's table detection
        tables = []
        excluded_tables = []
        
        try:
            # Get all tables on the page
            table_instances = page.find_tables()
            
            for i, table in enumerate(table_instances):
                # Get table bounding box
                bbox = table.bbox  # Returns (x0, y0, x1, y1)
                
                # Check if table is in exclusion zone
                if self.is_table_in_exclusion_zone(list(bbox), exclusion_regions):
                    excluded_tables.append({
                        "table_id": f"excluded_{i + 1}",
                        "bbox": list(bbox),
                        "reason": "In header/footer region"
                    })
                    print(f"Excluded table {i+1} (in header/footer region): {bbox}")
                    continue
                
                table_id = len(tables) + 1
                
                # Store preliminary table info with bbox
                table_info = {
                    "table_id": table_id,
                    "bbox": list(bbox),
                    "rows": 0,  # Will be updated after VLM extraction
                    "columns": 0,  # Will be updated after VLM extraction
                    "area": (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                    "content": []  # Will be filled by VLM
                }
                
                tables.append(table_info)
                print(f"Detected Table {table_id} at {bbox}")
        
        except Exception as e:
            print(f"Error detecting tables: {e}")
        
        # Alternative method: Look for text patterns that suggest tables
        if not tables:
            tables = self._detect_table_patterns(page, exclusion_regions)
        
        doc.close()
        
        print(f"Found {len(tables)} valid tables, excluded {len(excluded_tables)} tables in header/footer regions")
        
        # COLUMN-AWARE MERGING: Separate into columns and merge within each column
        if tables and len(tables) > 1:
            page_width = page.rect.width
            
            # Separate tables into left and right columns
            left_col, right_col = self.separate_columns(tables, page_width)
            print(f"Separated into columns - Left: {len(left_col)}, Right: {len(right_col)}")
            
            # Merge tables within each column
            left_merged = self.merge_column_tables(left_col, merge_threshold=50)
            right_merged = self.merge_column_tables(right_col, merge_threshold=50)
            
            print(f"After column merging - Left: {len(left_col)} → {len(left_merged)}, Right: {len(right_col)} → {len(right_merged)}")
            
            # Combine back together and sort by position
            tables = left_merged + right_merged
            tables.sort(key=lambda t: (t["bbox"][1], t["bbox"][0]))  # Sort top-to-bottom, left-to-right
            
            # Re-assign table IDs
            for idx, table in enumerate(tables, 1):
                table["table_id"] = idx
        
        return tables, page
    
    def _detect_table_patterns(self, page, exclusion_regions=None):
        """
        Fallback method to detect table-like structures using text analysis.
        
        Args:
            page: PyMuPDF page object
            exclusion_regions: Dictionary with header/footer regions to exclude
            
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
                bbox = block["bbox"]
                
                # Check if block is in exclusion zone
                if self.is_table_in_exclusion_zone(list(bbox), exclusion_regions):
                    continue
                
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
    
    def extract_table_with_vlm(self, page, table_bbox, page_number):
        """
        Extract table content using VLM by cropping the table area and sending to qwen model.
        
        Args:
            page: PyMuPDF page object
            table_bbox: Table bounding box (x0, y0, x1, y1)
            page_number: Page number for context
            
        Returns:
            List of lists containing table data, or None if extraction failed
        """
        try:
            # Render the table area to an image
            zoom = 300 / 72.0  # 300 DPI
            mat = fitz.Matrix(zoom, zoom)
            
            # Create a rect for the table area with some padding
            padding = 10  # Add small padding around table
            table_rect = fitz.Rect(
                max(0, table_bbox[0] - padding),
                max(0, table_bbox[1] - padding), 
                min(page.rect.width, table_bbox[2] + padding),
                min(page.rect.height, table_bbox[3] + padding)
            )
            
            # Render just the table area
            pix = page.get_pixmap(matrix=mat, clip=table_rect)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            table_image = Image.open(BytesIO(img_data))
            
            # Convert image to base64 for API
            buffer = BytesIO()
            table_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Try chat API first, then fallback to generate API
            api_endpoints = [
                "http://localhost:11434/api/chat",
                "http://localhost:11434/api/generate"
            ]
            
            prompt_content = """Look at this table image and extract ALL the text content exactly as it appears. 

I need you to read every single cell in the table and return the data as a JSON array. Each row should be an array containing the exact text from each column.

Important instructions:
- Read the ACTUAL text in each cell, don't make up placeholder names
- Include ALL columns you can see (there should be 6-7 columns typically)
- Include the header row with column names like "Artikelnr", "ID mm", etc.
- Include all data rows with product numbers, measurements, etc.
- If a cell contains multiple lines of text, keep them together
- If you see numbers, include them exactly as shown
- Preserve Swedish text exactly as it appears

Example format:
[
  ["Artikelnr", "ID mm", "ID tum", "YD mm", "Arb.tr. MPa", "Böjradie mm", "Vikt kg/m"],
  ["1101-14-04", "6,5", "1/4\"", "13,4", "22,5", "100", "0,21"],
  ...
]

Return ONLY the JSON array with the actual table content."""

            success = False
            content = None
            
            for api_url in api_endpoints:
                try:
                    if "chat" in api_url:
                        # Chat API format
                        payload = {
                            "model": "qwen3-vl:235b-cloud",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt_content,
                                    "images": [img_base64]
                                }
                            ],
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "num_predict": 2000
                            }
                        }
                    else:
                        # Generate API format
                        payload = {
                            "model": "qwen3-vl:235b-cloud",
                            "prompt": prompt_content,
                            "images": [img_base64],
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "num_predict": 2000
                            }
                        }
                    
                    print(f"Trying {api_url}...")
                    response = requests.post(api_url, json=payload, timeout=120)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "chat" in api_url:
                            content = result.get('message', {}).get('content', '').strip()
                        else:
                            content = result.get('response', '').strip()
                        
                        if content:
                            success = True
                            print(f"Successfully got response from {api_url}")
                            break
                    else:
                        print(f"API {api_url} failed with status {response.status_code}")
                        
                except Exception as e:
                    print(f"Error with {api_url}: {e}")
                    continue
            
            if not success or not content:
                print("All VLM API endpoints failed")
                return None
            
            # Try to parse JSON response
            try:
                # Remove any markdown formatting if present
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                table_data = json.loads(content)
                print(f"VLM extracted table with {len(table_data)} rows, {len(table_data[0]) if table_data else 0} columns")
                
                return table_data
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse VLM response as JSON: {e}")
                print(f"Raw response: {content[:200]}...")
                return None
                
        except Exception as e:
            print(f"Error in VLM table extraction: {e}")
            return None
    def draw_table_boxes(self, png_path, tables, pdf_page_size, exclusion_regions=None, page_number=None):
        """
        Draw bounding boxes around detected tables on PNG image and save to tables folder.
        
        Args:
            png_path: Path to PNG image
            tables: List of table dictionaries with bbox info
            pdf_page_size: (width, height) of original PDF page
            exclusion_regions: Optional header/footer regions to show
            page_number: Page number for filename
        """
        # Open PNG image
        image = Image.open(png_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font for labels
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        # Draw exclusion regions first (as background)
        if exclusion_regions:
            # Draw header region
            header_bbox = [
                exclusion_regions["header_region"].x0,
                exclusion_regions["header_region"].y0,
                exclusion_regions["header_region"].x1,
                exclusion_regions["header_region"].y1
            ]
            header_png = self.scale_bbox_to_png(header_bbox, pdf_page_size, image.size)
            draw.rectangle(header_png, outline="red", width=2)
            draw.text((header_png[0] + 5, header_png[1] + 5), "HEADER (EXCLUDED)", 
                     fill="red", font=font_small)
            
            # Draw footer region
            footer_bbox = [
                exclusion_regions["footer_region"].x0,
                exclusion_regions["footer_region"].y0,
                exclusion_regions["footer_region"].x1,
                exclusion_regions["footer_region"].y1
            ]
            footer_png = self.scale_bbox_to_png(footer_bbox, pdf_page_size, image.size)
            draw.rectangle(footer_png, outline="red", width=2)
            draw.text((footer_png[0] + 5, footer_png[1] + 5), "FOOTER (EXCLUDED)", 
                     fill="red", font=font_small)
        
        # Draw detected tables
        for i, table in enumerate(tables):
            # Scale PDF bounding box to PNG coordinates
            pdf_bbox = table["bbox"]
            png_bbox = self.scale_bbox_to_png(
                pdf_bbox, 
                pdf_page_size, 
                image.size
            )
            
            # Choose color
            color = "blue" 
            
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
        
        # Save to tables folder if page_number is provided
        if page_number is not None:
            tables_png_filename = f"page_{page_number:03d}_tables_visualization.png"
            tables_png_path = self.tables_dir / tables_png_filename
            image.save(tables_png_path)
            print(f"Table visualization saved to: {tables_png_path}")
    
    def process_pdf_page(self, pdf_path, page_number, png_path=None):
        """
        Main method to detect tables and create visualization.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to process
            png_path: Optional path to existing PNG, otherwise will look in data/png_pages
            
        Returns:
            Dictionary with detection results
        """
        print(f"Detecting tables in PDF: {pdf_path}, Page: {page_number}")
        
        # Open document (will be used throughout the process)
        doc = fitz.open(pdf_path)
        page_obj = doc.load_page(page_number - 1)
        pdf_page_size = (page_obj.rect.width, page_obj.rect.height)
        
        # Get exclusion regions for visualization
        pdf_name = Path(pdf_path).stem
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        # Detect tables (returns table list and page object - but we already have page_obj)
        tables_list, _ = self.detect_tables_in_pdf_page(pdf_path, page_number)
        
        if not tables_list:
            doc.close()
            print(f"No tables detected on page {page_number}")
            return {
                "page": page_number, 
                "tables": [], 
                "tables_detected": 0,
                "png_path": png_path,
                "individual_table_files": [],
                "visualization": None
            }
        
        print(f"Detected {len(tables_list)} table(s) on page {page_number}")
        
        # Determine PNG path
        if png_path is None:
            pdf_name = Path(pdf_path).stem
            png_filename = f"{pdf_name}_page_{page_number:03d}.png"
            png_path = self.pages_dir / png_filename
        
        if not png_path.exists():
            doc.close()
            print(f"Warning: PNG file not found: {png_path}")
            print("You may need to run pdf_to_png.py first to generate PNG files.")
            return {
                "page": page_number, 
                "tables": tables_list, 
                "tables_detected": len(tables_list),
                "png_path": None,
                "individual_table_files": [],
                "visualization": None
            }
        
        # Draw table bounding boxes FIRST (before VLM extraction)
        print("Drawing table bounding boxes on visualization...")
        self.draw_table_boxes(png_path, tables_list, pdf_page_size, exclusion_regions, page_number)
        
        # NOW extract table content with VLM for each detected table
        print("Extracting table content with VLM...")
        for table in tables_list:
            table_content = self.extract_table_with_vlm(page_obj, table["bbox"], page_number)
            
            # Update table info with extracted content
            rows = len(table_content) if table_content else 0
            cols = len(table_content[0]) if table_content and len(table_content) > 0 else 0
            
            table["rows"] = rows
            table["columns"] = cols
            table["content"] = table_content if table_content else []
            
            # Save individual table data to tables folder
            if table_content:
                table_filename = f"page_{page_number:03d}_table_{table['table_id']}_{rows}x{cols}.json"
                table_path = self.tables_dir / table_filename
                
                individual_table_info = {
                    "page": page_number,
                    "table_id": table['table_id'],
                    "table_bbox": table["bbox"],
                    "rows": rows,
                    "columns": cols,
                    "content": table_content,
                    "extraction_method": "VLM",
                    "model": "qwen3-vl:235b-cloud"
                }
                
                with open(table_path, 'w', encoding='utf-8') as f:
                    json.dump(individual_table_info, f, indent=2, ensure_ascii=False)
                
                print(f"Saved table data: {table_path}")
                print(f"Table {table['table_id']}: {rows}x{cols} at {table['bbox']}")
        
        # Close document after all processing
        doc.close()
        
        # Create summary results (individual tables are already saved in tables folder)
        visualization_file = f"page_{page_number:03d}_tables_visualization.png"
        results = {
            "page": page_number,
            "pdf_page_size": pdf_page_size,
            "png_size": Image.open(png_path).size,
            "tables": tables_list,  # Keep the actual tables list for process_all_pages
            "tables_detected": len(tables_list),
            "individual_table_files": [
                f"page_{page_number:03d}_table_{t['table_id']}_{t['rows']}x{t['columns']}.json" 
                for t in tables_list if t.get('content')
            ],
            "visualization": visualization_file,
            "detection_summary": {
                "total_tables": len(tables_list),
                "largest_table": max(tables_list, key=lambda t: t["area"])["table_id"] if tables_list else None,
                "total_area": sum(t["area"] for t in tables_list)
            }
        }
        
        print(f"Individual table files saved in data/tables/")
        print(f"Table visualization saved in data/tables/")
        
        return results

    def process_all_pages(self, pdf_path, start_page=1):
        """
        Process all pages in a PDF for table detection.
        
        Args:
            pdf_path: Path to PDF file
            start_page: Page number to start from (default: 1)
            
        Returns:
            Dictionary with results for all pages
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        print(f"Processing pages {start_page} to {total_pages} from {pdf_path}")
        
        all_results = {
            "pdf_path": str(pdf_path),
            "total_pages": total_pages,
            "start_page": start_page,
            "pages": {},
            "summary": {
                "pages_with_tables": 0,
                "total_tables": 0,
                "pages_processed": 0
            }
        }
        
        for page_num in range(start_page, total_pages + 1):
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
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Total pages processed: {all_results['summary']['pages_processed']}")
        print(f"Pages with tables: {all_results['summary']['pages_with_tables']}")
        print(f"Total tables detected: {all_results['summary']['total_tables']}")
        print(f"All individual table files and visualizations saved in data/tables/")
        
        return all_results


def main():
    parser = argparse.ArgumentParser(description="Detect tables in PDF pages and visualize on PNG images")
    parser.add_argument("--pdf-path", default="Press_Couplings.pdf", help="Path to PDF file (default: Press_Couplings.pdf)")
    parser.add_argument("--page", type=int, help="Specific page number to process (omit to process all pages)")
    parser.add_argument("--png-path", help="Optional path to specific PNG file (only works with --page)")
    parser.add_argument("--all-pages", action="store_true", help="Process all pages in the PDF")
    
    args = parser.parse_args()
    
    # Get script directory for finding PDF files
    script_dir = Path(__file__).parent
    
    # Find PDF file in multiple locations
    pdf_path = None
    search_paths = [
        Path(args.pdf_path),                      # Absolute or relative to CWD
        script_dir / args.pdf_path,               # Relative to script
        script_dir / "PDF" / args.pdf_path,       # In script's PDF folder
        script_dir.parent / "PDF" / args.pdf_path # In project's PDF folder
    ]
    
    for path in search_paths:
        if path.exists():
            pdf_path = path
            break
    
    if not pdf_path or not pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}")
        print("Searched in:")
        for path in search_paths:
            print(f"  - {path.absolute()}")
        sys.exit(1)
    
def main():
    parser = argparse.ArgumentParser(description="Detect tables in PDF pages and visualize on PNG images")
    parser.add_argument("--pdf-path", default="Press_Couplings.pdf", help="Path to PDF file (default: Press_Couplings.pdf)")
    parser.add_argument("--page", type=int, help="Specific page number to process (omit to process all pages)")
    parser.add_argument("--png-path", help="Optional path to specific PNG file (only works with --page)")
    parser.add_argument("--all-pages", action="store_true", help="Process all pages in the PDF")
    parser.add_argument("--start-page", type=int, default=5, help="Starting page number for batch processing (default: 5)")
    
    args = parser.parse_args()
    
    # Get script directory for finding PDF files
    script_dir = Path(__file__).parent
    
    # Find PDF file in multiple locations
    pdf_path = None
    search_paths = [
        Path(args.pdf_path),                      # Absolute or relative to CWD
        script_dir / args.pdf_path,               # Relative to script
        script_dir / "PDF" / args.pdf_path,       # In script's PDF folder
        script_dir.parent / "PDF" / args.pdf_path # In project's PDF folder
    ]
    
    for path in search_paths:
        if path.exists():
            pdf_path = path
            break
    
    if not pdf_path or not pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}")
        print("Searched in:")
        for path in search_paths:
            print(f"  - {path.absolute()}")
        sys.exit(1)
    
    # Initialize detector
    detector = TableDetector()
    
    try:
        # Determine processing mode
        if args.page is not None:
            # Process single page
            results = detector.process_pdf_page(
                pdf_path, 
                args.page, 
                png_path=Path(args.png_path) if args.png_path else None
            )
            
            # Print single page summary
            tables_count = results["tables_detected"]
            if tables_count > 0:
                print(f"\n=== Table Detection Summary ===")
                print(f"Page: {results['page']}")
                print(f"Tables detected: {tables_count}")
                print(f"Individual table files: {results['individual_table_files']}")
                print(f"Visualization saved: {results['visualization']}")
                print(f"All files saved in data/tables/")
            else:
                print(f"\nNo tables detected on page {args.page}")
        else:
            # Process all pages starting from start_page
            print(f"Processing all pages starting from page {args.start_page}...")
            results = detector.process_all_pages(pdf_path, start_page=args.start_page)
            
    except Exception as e:
        print(f"Error during table detection: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()