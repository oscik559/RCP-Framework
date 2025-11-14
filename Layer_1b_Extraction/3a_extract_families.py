#!/usr/bin/env python3
"""
Table Bounding Box Visualization Only

This script detects tables and draws bounding boxes WITHOUT VLM extraction.
Use this to verify table detection before running the full extraction.

Features:
- Visualizes tables with blue boxes
- Extracts family information with green boxes
- Maps extracted lines directly to database schema fields
"""

import os
import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import json
sys.path.append(str(Path(__file__).parent.parent / "data" / "database"))
from db_utils import DatabaseManager

# Import CategoryExtractor to reuse category extraction logic
sys.path.append(str(Path(__file__).parent))
from importlib import import_module
extract_categories = import_module('2b_extract_categories')
CategoryExtractor = extract_categories.CategoryExtractor


class TableVisualizer:
    def __init__(self, merge_threshold=10):
        """
        Initialize the TableVisualizer.
        
        Args:
            merge_threshold: Maximum vertical gap (in points) for merging tables.
                           50 = conservative (default)
                           75 = moderate
                           100 = aggressive
        """
        # Get script directory for relative paths
        self.script_dir = Path(__file__).parent
        self.pages_dir = self.script_dir / "data/png_pages"
        self.tables_dir = self.script_dir / "data/tables"
        self.family_dir = self.script_dir / "data/family"  # For family information
        # Use database at root level
        db_path = self.script_dir / "data" / "database" / "harvested.db"
        self.db_manager = DatabaseManager(str(db_path))
        self.merge_threshold = merge_threshold
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        self.family_dir.mkdir(parents=True, exist_ok=True)
        self.products_dir = self.script_dir / "data/products"  # For product tables
        self.products_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        self.db_manager.init_database()
        
        # Initialize category extractor for reuse
        self.category_extractor = CategoryExtractor()
    
    def get_exclusion_regions(self, pdf_name, page_number):
        """Get header/footer regions from database to exclude from table detection."""
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
    
    def is_table_in_exclusion_zone(self, table_bbox, exclusion_regions):
        """Check if a table intersects with header or footer exclusion regions."""
        if not exclusion_regions:
            return False
        
        if isinstance(table_bbox, list):
            table_rect = fitz.Rect(table_bbox)
        else:
            table_rect = table_bbox
        
        header_intersects = table_rect.intersects(exclusion_regions["header_region"])
        footer_intersects = table_rect.intersects(exclusion_regions["footer_region"])
        
        return header_intersects or footer_intersects
    
    def get_category_id_for_page(self, pdf_path, page_number, exclusion_regions):
        """
        Extract category from page header using CategoryExtractor and get/create category_id.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed) 
            exclusion_regions: Dict with header_region
            
        Returns:
            int: category_id from database
        """
        # Open PDF and extract category from header using CategoryExtractor logic
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        
        pdf_name = Path(pdf_path).stem
        
        # Get header region
        if not exclusion_regions or not exclusion_regions.get("header_region"):
            # Use default header region if not available
            header_bbox = [0, 0, page.rect.width, 60]
        else:
            header_bbox = exclusion_regions["header_region"]
        
        # Extract text from header (using CategoryExtractor's logic)
        text_instances = self.category_extractor.extract_header_text(page, header_bbox)
        
        # Parse category information (using CategoryExtractor's logic)
        category_info = self.category_extractor.parse_category_info(text_instances)
        
        doc.close()
        
        if not category_info or not category_info.get("name"):
            print(f"      ⚠️  No category found in header for page {page_number}, using default category_id=1")
            return 1
        
        # Look up category in database by name
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM categories 
            WHERE name = ? 
            LIMIT 1
        ''', (category_info["name"],))
        
        result = cursor.fetchone()
        
        if result:
            category_id = result[0]
            conn.close()
            return category_id
        else:
            # Category not in database yet, insert it
            cursor.execute('''
                INSERT INTO categories (name, chapter, description, page_number)
                VALUES (?, ?, ?, ?)
            ''', (
                category_info["name"],
                category_info.get("chapter", ""),
                category_info.get("description", ""),
                page_number
            ))
            conn.commit()
            category_id = cursor.lastrowid
            print(f"      ✨ Inserted new category '{category_info['name']}' (ID: {category_id})")
            conn.close()
            return category_id
    
    def extract_page_number_from_footer(self, page, footer_region):
        """Extract the actual page number from the footer region of the PDF."""
        # Get text from footer region
        text_instances = page.get_text("dict")["blocks"]
        
        page_numbers = []
        for block in text_instances:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            # Check if block is in footer region
            block_bbox = block.get("bbox", [0, 0, 0, 0])
            if block_bbox[1] < footer_region[1]:  # Above footer
                continue
            
            # Extract text from footer
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    
                    # Look for numbers in the footer
                    if text.isdigit():
                        page_numbers.append(int(text))
        
        # Return the most likely page number (usually the largest number in footer)
        if page_numbers:
            # Return the last number found (usually at the end of footer)
            return page_numbers[-1]
        
        return None
    
    def separate_columns(self, tables, page_width=595):
        """Separate tables into left and right columns based on page layout."""
        column_mid = page_width / 2
        left_col = []
        right_col = []
        
        for table in tables:
            table_center_x = (table["bbox"][0] + table["bbox"][2]) / 2
            if table_center_x < column_mid:
                left_col.append(table)
            else:
                right_col.append(table)
        
        left_col.sort(key=lambda t: t["bbox"][1])
        right_col.sort(key=lambda t: t["bbox"][1])
        return left_col, right_col
    
    def merge_column_tables(self, column_tables, merge_threshold=50):
        """Merge tables within a single column that are vertically adjacent."""
        if len(column_tables) <= 1:
            return column_tables
        
        merged = []
        current_group = [column_tables[0]]
        
        for i in range(1, len(column_tables)):
            current = column_tables[i]
            last_in_group = current_group[-1]
            
            vertical_gap = current["bbox"][1] - last_in_group["bbox"][3]
            last_width = last_in_group["bbox"][2] - last_in_group["bbox"][0]
            current_width = current["bbox"][2] - current["bbox"][0]
            width_ratio = min(last_width, current_width) / max(last_width, current_width) if max(last_width, current_width) > 0 else 0
            
            should_merge = (0 < vertical_gap < merge_threshold and width_ratio > 0.80)
            
            if should_merge:
                current_group.append(current)
            else:
                if len(current_group) > 1:
                    merged_table = self._merge_table_group(current_group)
                    merged.append(merged_table)
                else:
                    merged.append(current_group[0])
                current_group = [current]
        
        if len(current_group) > 1:
            merged_table = self._merge_table_group(current_group)
            merged.append(merged_table)
        else:
            merged.append(current_group[0])
        
        for idx, table in enumerate(merged, 1):
            table["table_id"] = idx
        
        return merged
    
    def merge_adjacent_tables(self, tables, merge_threshold=50):
        """Merge tables that are vertically adjacent, with strict criteria to avoid over-merging."""
        if len(tables) <= 1:
            return tables
        
        sorted_tables = sorted(tables, key=lambda t: (t["bbox"][1], t["bbox"][0]))
        
        merged = []
        current_group = [sorted_tables[0]]
        
        for i in range(1, len(sorted_tables)):
            current = sorted_tables[i]
            last_in_group = current_group[-1]
            
            # Calculate x-overlap more precisely
            x_overlap_left = max(current["bbox"][0], last_in_group["bbox"][0])
            x_overlap_right = min(current["bbox"][2], last_in_group["bbox"][2])
            x_overlap = x_overlap_right - x_overlap_left
            
            # Calculate overlap ratio
            last_width = last_in_group["bbox"][2] - last_in_group["bbox"][0]
            current_width = current["bbox"][2] - current["bbox"][0]
            min_width = min(last_width, current_width)
            overlap_ratio = x_overlap / min_width if min_width > 0 else 0
            
            # Check vertical gap
            vertical_gap = current["bbox"][1] - last_in_group["bbox"][3]
            
            # Similar widths check
            width_ratio = min(last_width, current_width) / max(last_width, current_width) if max(last_width, current_width) > 0 else 0
            
            # STRICT merging criteria:
            # 1. High x-overlap (>85% - definitely same column)
            # 2. Small vertical gap (<50 points AND positive - no overlaps)
            # 3. Very similar widths (>85% - same table structure)
            should_merge = (
                overlap_ratio > 0.85 and 
                0 < vertical_gap < merge_threshold and  
                width_ratio > 0.85
            )
            
            if should_merge:
                current_group.append(current)
            else:
                if len(current_group) > 1:
                    merged_table = self._merge_table_group(current_group)
                    merged.append(merged_table)
                else:
                    merged.append(current_group[0])
                
                current_group = [current]
        
        # Last group
        if len(current_group) > 1:
            merged_table = self._merge_table_group(current_group)
            merged.append(merged_table)
        else:
            merged.append(current_group[0])
        
        # Re-assign table IDs
        for idx, table in enumerate(merged, 1):
            table["table_id"] = idx
        
        print(f"Merged {len(tables)} detected tables into {len(merged)} logical tables")
        return merged
    
    def _merge_table_group(self, table_group):
        """Merge a group of tables into a single table with combined bbox."""
        min_x0 = min(t["bbox"][0] for t in table_group)
        min_y0 = min(t["bbox"][1] for t in table_group)
        max_x1 = max(t["bbox"][2] for t in table_group)
        max_y1 = max(t["bbox"][3] for t in table_group)
        
        combined_bbox = [min_x0, min_y0, max_x1, max_y1]
        
        return {
            "table_id": table_group[0]["table_id"],
            "bbox": combined_bbox,
            "area": (max_x1 - min_x0) * (max_y1 - min_y0),
            "merged_from": len(table_group)
        }
    
    def extract_family_info_above_table(self, pdf_path, page_number, table_bbox, num_lines=6):
        """
        Extract family information from the region above a table using orange text detection.
        Extracts 6 lines but maps to 5 database fields (skipping line 4 for construction_details often empty).
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            table_bbox: Table bounding box [x0, y0, x1, y1]
            num_lines: Number of lines to extract (default: 6)
            
        Returns:
            dict: Family information with database schema fields and bbox
        """
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        
        # Define search region above table
        x0, y0, x1, y1 = table_bbox
        
        # Search in a large area above table to find orange text
        search_height = 100  # Look up to 100 points above table
        search_margin = 5
        search_x0 = x0 - search_margin
        search_x1 = x1 + search_margin
        search_y1 = y0 - 5  # Small gap from table
        search_y0 = max(0, search_y1 - search_height)
        
        # Get text with formatting to detect orange color
        search_rect = fitz.Rect(search_x0, search_y0, search_x1, search_y1)
        text_dict = page.get_text("dict", clip=search_rect)
        
        # Find orange text blocks (family codes are in orange)
        orange_blocks = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        color = span.get("color", 0)
                        # Orange color found in PDF: 15492616 (0xEC5418 = RGB 236,84,24)
                        # Allow range for slight variations
                        if 15400000 <= color <= 15600000:  # Orange range
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            text = span.get("text", "").strip()
                            if text:
                                orange_blocks.append({
                                    "text": text,
                                    "bbox": bbox,
                                    "y0": bbox[1],
                                    "y1": bbox[3]
                                })
        
        # If we found orange text, use it to define the family region
        if orange_blocks:
            # Sort by vertical position (top to bottom)
            orange_blocks.sort(key=lambda b: b["y0"])
            
            # Find the topmost and bottommost orange text
            top_orange_y = orange_blocks[0]["y0"]
            bottom_orange_y = orange_blocks[-1]["y1"]
            
            # Extend region slightly to capture text below orange header
            family_x0 = x0 - 5
            family_x1 = x1 + 5
            family_y0 = max(0, top_orange_y - 3)  # Start just above orange text
            family_y1 = min(search_y1, bottom_orange_y + 40)  # Extend ~40pts below for name/desc
        else:
            # Fallback: use fixed region if no orange text found
            family_height = 42
            margin = 5
            family_x0 = x0 - 5
            family_x1 = x1 + 5
            family_y1 = y0 - margin
            family_y0 = max(0, family_y1 - family_height)
        
        # Extract text from family region using dict method for better character extraction
        family_rect = fitz.Rect(family_x0, family_y0, family_x1, family_y1)
        text_dict_family = page.get_text("dict", clip=family_rect)
        
        # Extract text from dict while preserving line structure
        raw_lines = []
        for block in text_dict_family.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    raw_lines.append(line_text.strip())
        
        doc.close()
        
        # Clean extracted lines
        cleaned_lines = []
        for line in raw_lines:
            # Remove PDF artifacts and normalize unicode
            line = line.replace('\u0015', '').replace('\u0012', '').replace('\u0005', '')
            # Fix PDF encoding issues - degree symbol often extracted as \x98
            line = line.replace('\x98', '°')
            # Fix common OCR issues
            line = line.replace('4niied', 'Unified').replace('4nified', 'Unified')
            cleaned_lines.append(line if line.strip() else "")
        
        # Ensure we have exactly num_lines (pad with empty strings if needed)
        while len(cleaned_lines) < num_lines:
            cleaned_lines.append("")
        
        # Take only the requested number of lines
        family_lines = cleaned_lines[:num_lines]
        
        # Smart field mapping based on content
        # Line 0: family_code (always)
        # Line 1: name (always)
        # Find "PRODUKTGRUPP" to identify subtitle line
        # Everything between name and subtitle goes to construction_details
        
        family_code = family_lines[0] if len(family_lines) > 0 else ""
        name = family_lines[1] if len(family_lines) > 1 else ""
        
        # Find which line contains "PRODUKTGRUPP" for subtitle
        subtitle_line_idx = -1
        for i in range(2, len(family_lines)):
            if "PRODUKTGRUPP" in family_lines[i]:
                subtitle_line_idx = i
                break
        
        # Build construction_details from lines between name and subtitle
        construction_parts = []
        if subtitle_line_idx > 2:
            # Lines 2 to (subtitle_line_idx - 1) go to construction_details
            for i in range(2, subtitle_line_idx):
                if family_lines[i]:
                    construction_parts.append(family_lines[i])
        
        construction_details = "\n".join(construction_parts)
        subtitle = family_lines[subtitle_line_idx] if subtitle_line_idx >= 0 else ""
        
        # Clean family_code: replace tilde with dash
        family_code = family_code.replace("~", "-")
        
        return {
            "family_code": family_code,
            "name": name,
            "description": "",  # Empty for this extraction
            "construction_details": construction_details,
            "subtitle": subtitle,
            "bbox": [family_x0, family_y0, family_x1, family_y1]
        }
    
    def save_family_information(self, actual_page_number, families_data, pdf_path, pdf_page_number, exclusion_regions):
        """
        Save family information to JSON file and database.
        
        Args:
            actual_page_number: Actual page number from footer (for database storage)
            families_data: List of family information dictionaries
            pdf_path: Path to PDF file (for category extraction)
            pdf_page_number: PDF page number (for opening correct page)
            exclusion_regions: Dict with header_region (for category extraction)
        """
        # Save to JSON file
        output_file = self.family_dir / f"page_{actual_page_number:03d}_family_info.json"
        
        structured_data = {
            "page_number": actual_page_number,
            "total_families": len(families_data),
            "families": families_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
        
        print(f"   📋 Saved family information to {output_file.name}")
        
        # Insert into database
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get category_id for this page by extracting category from header
        # Use pdf_page_number to open the correct page in the PDF
        category_id = self.get_category_id_for_page(pdf_path, pdf_page_number, exclusion_regions)
        
        for family in families_data:
            try:
                # Build construction_details JSON
                construction_json = json.dumps({
                    "details": family.get("construction_details", "")
                }, ensure_ascii=False) if family.get("construction_details") else None
                
                # Insert family with category_id from database
                cursor.execute('''
                    INSERT OR REPLACE INTO product_families 
                    (category_id, family_code, name, subtitle, description, construction_details, page_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    category_id,
                    family.get("family_code", ""),
                    family.get("name", ""),
                    family.get("subtitle", ""),
                    family.get("description", ""),
                    construction_json,
                    actual_page_number  # Use actual_page_number for database storage
                ))
                
                # Get the inserted family ID
                family_db_id = cursor.lastrowid
                family["db_id"] = family_db_id
                
                print(f"      ✅ Inserted family {family.get('family_code')} to DB (ID: {family_db_id})")
                
            except Exception as e:
                print(f"      ⚠️  Error inserting family {family.get('family_code')} to DB: {e}")
        
        conn.commit()
        conn.close()
        
        return True
    
    def detect_tables_in_pdf_page(self, pdf_path, page_number):
        """Detect tables in a PDF page using PyMuPDF, excluding header/footer regions."""
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
        
        page = doc.load_page(page_number - 1)
        
        # Get exclusion regions
        pdf_name = Path(pdf_path).stem
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        if exclusion_regions:
            print(f"Using exclusion regions - Header: {exclusion_regions['header_region']}, Footer: {exclusion_regions['footer_region']}")
        
        # Find tables
        tables = []
        excluded_tables = []
        
        try:
            table_instances = page.find_tables()
            
            for i, table in enumerate(table_instances):
                bbox = table.bbox
                
                if self.is_table_in_exclusion_zone(list(bbox), exclusion_regions):
                    excluded_tables.append({
                        "table_id": f"excluded_{i + 1}",
                        "bbox": list(bbox),
                        "reason": "In header/footer region"
                    })
                    print(f"Excluded table {i+1} (in header/footer region)")
                    continue
                
                table_id = len(tables) + 1
                
                table_info = {
                    "table_id": table_id,
                    "bbox": list(bbox),
                    "area": (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                }
                
                tables.append(table_info)
                print(f"Detected Table {table_id} at {bbox}")
        
        except Exception as e:
            print(f"Error detecting tables: {e}")
        
        print(f"Found {len(tables)} valid tables, excluded {len(excluded_tables)} in header/footer")
        
        # COLUMN-AWARE MERGING
        if tables and len(tables) > 1:
            page_width = page.rect.width
            
            # Separate into columns
            left_col, right_col = self.separate_columns(tables, page_width)
            print(f"Separated into columns - Left: {len(left_col)}, Right: {len(right_col)}")
            
            # Merge within each column
            left_merged = self.merge_column_tables(left_col, merge_threshold=self.merge_threshold)
            right_merged = self.merge_column_tables(right_col, merge_threshold=self.merge_threshold)
            
            print(f"After column merging (threshold={self.merge_threshold}pt) - Left: {len(left_col)} → {len(left_merged)}, Right: {len(right_col)} → {len(right_merged)}")
            
            # Combine and sort
            tables = left_merged + right_merged
            tables.sort(key=lambda t: (t["bbox"][1], t["bbox"][0]))
            
            # Re-assign IDs
            for idx, table in enumerate(tables, 1):
                table["table_id"] = idx
        
        doc.close()
        
        return tables, exclusion_regions
    
    def scale_bbox_to_png(self, pdf_bbox, pdf_page_size, png_size, dpi=300):
        """Scale bounding box coordinates from PDF space to PNG image space."""
        scale_factor = dpi / 72.0
        
        expected_png_width = int(pdf_page_size[0] * scale_factor)
        expected_png_height = int(pdf_page_size[1] * scale_factor)
        
        x_scale = png_size[0] / expected_png_width
        y_scale = png_size[1] / expected_png_height
        
        x0 = int(pdf_bbox[0] * scale_factor * x_scale)
        y0 = int(pdf_bbox[1] * scale_factor * y_scale)
        x1 = int(pdf_bbox[2] * scale_factor * x_scale)
        y1 = int(pdf_bbox[3] * scale_factor * y_scale)
        
        return [x0, y0, x1, y1]
    
    def draw_table_boxes(self, png_path, tables, pdf_page_size, exclusion_regions, page_number, pdf_name=None, families_data=None):
        """Draw bounding boxes around detected tables and family regions on PNG image."""
        image = Image.open(png_path)
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        # Draw exclusion regions
        if exclusion_regions:
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
        
        # Draw family regions (if provided)
        if families_data:
            for family in families_data:
                # Use the bbox that was calculated during extraction (based on orange text detection)
                family_pdf_bbox = family.get("bbox")
                if not family_pdf_bbox:
                    continue
                
                family_png_bbox = self.scale_bbox_to_png(family_pdf_bbox, pdf_page_size, image.size)
                
                # Draw family region box (green)
                draw.rectangle(family_png_bbox, outline="green", width=3)
                
                # Add family label
                family_label = f"Family {family.get('family_id', '?')}"
                # Use family_code for label
                if family.get("family_code"):
                    family_label += f": {family['family_code']}"
                
                label_x = family_png_bbox[0]
                label_y = max(0, family_png_bbox[1] - 25)
                
                bbox_label = draw.textbbox((label_x, label_y), family_label, font=font)
                draw.rectangle([bbox_label[0]-2, bbox_label[1]-2, bbox_label[2]+2, bbox_label[3]+2], 
                              fill="white", outline="green")
                draw.text((label_x, label_y), family_label, fill="green", font=font)
                
                # Draw connecting line from family to table
                table_id = family.get("table_id")
                table = next((t for t in tables if t["table_id"] == table_id), None)
                if table:
                    family_center_x = (family_png_bbox[0] + family_png_bbox[2]) / 2
                    family_bottom = family_png_bbox[3]
                    table_png_bbox = self.scale_bbox_to_png(table["bbox"], pdf_page_size, image.size)
                    table_center_x = (table_png_bbox[0] + table_png_bbox[2]) / 2
                    table_top = table_png_bbox[1]
                    
                    # Draw connecting line
                    draw.line([(family_center_x, family_bottom), (table_center_x, table_top)], 
                             fill="green", width=2)
        
        # Draw detected tables
        for i, table in enumerate(tables):
            pdf_bbox = table["bbox"]
            png_bbox = self.scale_bbox_to_png(pdf_bbox, pdf_page_size, image.size)
            
            color = "blue"
            draw.rectangle(png_bbox, outline=color, width=3)
            
            label = f"Table {table['table_id']}"
            if table.get('merged_from'):
                label += f" (merged {table['merged_from']})"
            
            label_x = png_bbox[0]
            label_y = max(0, png_bbox[1] - 25)
            
            bbox_label = draw.textbbox((label_x, label_y), label, font=font)
            draw.rectangle([bbox_label[0]-2, bbox_label[1]-2, bbox_label[2]+2, bbox_label[3]+2], 
                          fill="white", outline=color)
            draw.text((label_x, label_y), label, fill=color, font=font)
        
        # Save visualization with PDF name
        if pdf_name is None:
            pdf_name = "document"
        tables_png_filename = f"{pdf_name}_page_{page_number:03d}_tables_visualization.png"
        tables_png_path = self.tables_dir / tables_png_filename
        image.save(tables_png_path)
        print(f"✅ Visualization saved: {tables_png_path}")
        
        return tables_png_path
    
    def visualize_page(self, pdf_path, page_number):
        """Visualize table detection for a single page."""
        print(f"\n=== Page {page_number} ===")
        
        # Get PDF page dimensions and extract actual page number from footer
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        pdf_page_size = (page.rect.width, page.rect.height)
        
        # Get exclusion regions to find footer
        pdf_name = Path(pdf_path).stem
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        # Extract actual page number from footer
        actual_page_number = page_number  # Default to PDF page number
        if exclusion_regions and exclusion_regions.get("footer_region"):
            footer_page_num = self.extract_page_number_from_footer(page, exclusion_regions["footer_region"])
            if footer_page_num:
                actual_page_number = footer_page_num
                print(f"📄 Footer page number: {actual_page_number}")
        
        doc.close()
        
        # Detect tables
        tables, exclusion_regions = self.detect_tables_in_pdf_page(pdf_path, page_number)
        
        if not tables:
            print(f"No tables detected on page {page_number}")
            return None
        
        # Get PNG path
        pdf_name = Path(pdf_path).stem
        png_filename = f"{pdf_name}_page_{page_number:03d}.png"
        png_path = self.pages_dir / png_filename
        
        if not png_path.exists():
            print(f"⚠️  PNG not found: {png_path}")
            return None
        
        # Extract family information for each table
        print(f"\n📖 Extracting family information for {len(tables)} tables...")
        families_data = []
        
        for i, table in enumerate(tables, 1):
            table_bbox = table["bbox"]
            family_info = self.extract_family_info_above_table(pdf_path, page_number, table_bbox)
            
            # Add table association
            family_info["table_id"] = table["table_id"]
            family_info["family_id"] = i
            families_data.append(family_info)
            
            # Display extracted family info
            print(f"   Family {i} (Table {table['table_id']}):")
            print(f"      family_code: {family_info.get('family_code', '')}")
            print(f"      name: {family_info.get('name', '')}")
            print(f"      description: {family_info.get('description', '')}")
            print(f"      subtitle: {family_info.get('subtitle', '')}")
            print(f"      construction_details: {family_info.get('construction_details', '')}")
        
        # Draw visualization (with family regions)
        pdf_name = Path(pdf_path).stem
        viz_path = self.draw_table_boxes(png_path, tables, pdf_page_size, exclusion_regions, page_number, pdf_name, families_data)
        
        # Save family information with actual page number from footer
        # Pass both actual_page_number (for storage) and page_number (for PDF extraction)
        self.save_family_information(actual_page_number, families_data, pdf_path, page_number, exclusion_regions)
        
        return {
            "page": page_number,
            "tables_detected": len(tables),
            "families_extracted": len(families_data),
            "visualization": viz_path
        }
    
    def visualize_all_pages(self, pdf_path, start_page=1, end_page=None):
        """Visualize table detection for all pages."""
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        if end_page is None:
            end_page = total_pages
        
        print(f"Visualizing tables for pages {start_page} to {end_page}")
        
        results = []
        total_tables = 0
        
        for page_num in range(start_page, end_page + 1):
            try:
                result = self.visualize_page(pdf_path, page_num)
                if result:
                    results.append(result)
                    total_tables += result["tables_detected"]
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Pages processed: {len(results)}")
        print(f"Total tables detected: {total_tables}")
        print(f"Visualizations saved in: {self.tables_dir}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Visualize table detection without VLM extraction")
    parser.add_argument("--pdf-path", default="Press_Couplings.pdf", help="Path to PDF file")
    parser.add_argument("--page", type=int, help="Specific page number to visualize")
    parser.add_argument("--start-page", type=int, default=5, help="Starting page (default: 5)")
    parser.add_argument("--end-page", type=int, help="Ending page (default: last page)")
    parser.add_argument("--merge-threshold", type=int, default=50, 
                       help="Vertical gap threshold for merging tables in points (default: 50, try 75-100 for more merging)")
    parser.add_argument("--no-merge", action="store_true",
                       help="Disable table merging entirely (keeps all detected tables separate)")
    
    args = parser.parse_args()
    
    # Find PDF file
    script_dir = Path(__file__).parent
    pdf_path = None
    search_paths = [
        Path(args.pdf_path),
        script_dir / args.pdf_path,
        script_dir / "PDF" / args.pdf_path,
        script_dir.parent / "PDF" / args.pdf_path
    ]
    
    for path in search_paths:
        if path.exists():
            pdf_path = path
            break
    
    if not pdf_path:
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Initialize visualizer with threshold
    if args.no_merge:
        print("Table merging DISABLED - keeping all tables separate")
        visualizer = TableVisualizer(merge_threshold=0)
    else:
        print(f"Using merge threshold: {args.merge_threshold} points")
        visualizer = TableVisualizer(merge_threshold=args.merge_threshold)
    
    try:
        if args.page is not None:
            # Single page
            visualizer.visualize_page(pdf_path, args.page)
        else:
            # All pages
            visualizer.visualize_all_pages(pdf_path, args.start_page, args.end_page)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
