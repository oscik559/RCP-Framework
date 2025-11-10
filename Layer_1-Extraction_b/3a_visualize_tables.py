#!/usr/bin/env python3
"""
Table Bounding Box Visualization Only

This script detects tables and draws bounding boxes WITHOUT VLM extraction.
Use this to verify table detection before running the full extraction.
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
        self.db_manager = DatabaseManager()
        self.merge_threshold = merge_threshold
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        self.db_manager.init_database()
    
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
    
    def draw_table_boxes(self, png_path, tables, pdf_page_size, exclusion_regions, page_number):
        """Draw bounding boxes around detected tables on PNG image."""
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
        
        # Save visualization
        tables_png_filename = f"page_{page_number:03d}_tables_visualization.png"
        tables_png_path = self.tables_dir / tables_png_filename
        image.save(tables_png_path)
        print(f"✅ Visualization saved: {tables_png_path}")
        
        return tables_png_path
    
    def visualize_page(self, pdf_path, page_number):
        """Visualize table detection for a single page."""
        print(f"\n=== Page {page_number} ===")
        
        # Get PDF page dimensions
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)
        pdf_page_size = (page.rect.width, page.rect.height)
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
        
        # Draw visualization
        viz_path = self.draw_table_boxes(png_path, tables, pdf_page_size, exclusion_regions, page_number)
        
        return {
            "page": page_number,
            "tables_detected": len(tables),
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
        visualizer = TableVisualizer(merge_threshold=0)  # Setting to 0 disables merging
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
