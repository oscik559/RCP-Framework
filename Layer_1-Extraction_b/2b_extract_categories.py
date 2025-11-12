#!/usr/bin/env python3
"""
Category Extraction from PDF Header

This script extracts category information from the header region of the first page
of each chapter/section in the PDF.

Format found in header:
- Category name (e.g., "HÖGTRYCKSSLANG")
- Chapter designation (e.g., "KAPITEL 4:2")
- Description text

Saves to database categories table with fields:
- id (auto-increment)
- name
- chapter
- description
- page_number
"""

import os
import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
import json
import re

sys.path.append(str(Path(__file__).parent.parent / "data" / "database"))
from db_utils import DatabaseManager


class CategoryExtractor:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        # Use local database in Layer_1-Extraction_b/data/database/
        db_path = self.script_dir / "data" / "database" / "harvested.db"
        self.db_manager = DatabaseManager(str(db_path))
        self.db_manager.init_database()
        
    def extract_header_text(self, page, header_bbox):
        """Extract all text from header region with color and position info."""
        text_instances = []
        
        # Get text with detailed properties
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
                
            # Check if block is in header region
            block_bbox = block.get("bbox", [0, 0, 0, 0])
            if block_bbox[3] > header_bbox[3]:  # Below header
                continue
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    color = span.get("color", 0)
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    
                    text_instances.append({
                        "text": text,
                        "color": color,
                        "bbox": bbox,
                        "y_pos": bbox[1]  # Top y-coordinate for sorting
                    })
        
        # Sort by vertical position
        text_instances.sort(key=lambda x: x["y_pos"])
        
        return text_instances
    
    def parse_category_info(self, text_instances):
        """Parse category information from header text instances."""
        category_info = {
            "name": "",
            "chapter": "",
            "description": ""
        }
        
        # Orange color typically used for chapter designation
        ORANGE_COLOR = 15492616  # 0xEC5418
        
        # Look for KAPITEL pattern: "KAPITEL 4:2 PRESSKOPPLINGAR"
        # Format: KAPITEL <chapter_num> <category_name>
        chapter_pattern = re.compile(r'(KAPITEL\s+\d+:\d+)\s+(.+)', re.IGNORECASE)
        
        for instance in text_instances:
            text = instance["text"]
            
            # Check for chapter designation with category name
            match = chapter_pattern.search(text)
            if match:
                category_info["chapter"] = match.group(1).strip()
                category_info["name"] = match.group(2).strip()
                continue
            
            # Check for orange text (likely category name)
            if instance["color"] == ORANGE_COLOR:
                # This is likely the category name
                if not category_info["name"]:
                    category_info["name"] = text
                else:
                    # Append if multiple orange texts
                    category_info["name"] += " " + text
                continue
            
            # Everything else goes to description
            # Skip very short texts (likely page numbers or artifacts)
            if len(text) > 5 and text not in category_info["name"] and text != category_info["chapter"]:
                if category_info["description"]:
                    category_info["description"] += " " + text
                else:
                    category_info["description"] = text
        
        # Clean up
        category_info["name"] = category_info["name"].strip()
        category_info["chapter"] = category_info["chapter"].strip()
        category_info["description"] = category_info["description"].strip()
        
        return category_info
    
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
    
    def save_category_to_db(self, category_info, page_number):
        """Save category information to database."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO categories (name, chapter, description, page_number)
                VALUES (?, ?, ?, ?)
            ''', (
                category_info["name"],
                category_info["chapter"],
                category_info["description"],
                page_number
            ))
            
            conn.commit()
            category_id = cursor.lastrowid
            
            print(f"✅ Inserted category to DB (ID: {category_id})")
            print(f"   Name: {category_info['name']}")
            print(f"   Chapter: {category_info['chapter']}")
            print(f"   Page: {page_number}")
            
            return category_id
            
        except Exception as e:
            print(f"❌ Error saving category: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def extract_category_from_page(self, pdf_path, page_number):
        """Extract category from a specific page."""
        print(f"\n=== Extracting Category from Page {page_number} ===")
        
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]  # 0-indexed
        
        # Get exclusion regions from database
        pdf_name = Path(pdf_path).stem
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        if not exclusion_regions:
            print(f"⚠️  No exclusion regions found for page {page_number}")
            # Use default header region (top 60 points)
            header_bbox = [0, 0, page.rect.width, 60]
            footer_bbox = None
        else:
            header_bbox = exclusion_regions["header_region"]
            footer_bbox = exclusion_regions["footer_region"]
            print(f"Using header region: {header_bbox}")
        
        # Extract actual page number from footer
        actual_page_number = page_number  # Default to PDF page number
        if footer_bbox:
            footer_page_num = self.extract_page_number_from_footer(page, footer_bbox)
            if footer_page_num:
                actual_page_number = footer_page_num
                print(f"📄 Footer page number: {actual_page_number}")
        
        # Extract text from header
        text_instances = self.extract_header_text(page, header_bbox)
        
        print(f"Found {len(text_instances)} text instances in header:")
        for inst in text_instances:
            print(f"  - {inst['text']} (color: {inst['color']})")
        
        # Parse category information
        category_info = self.parse_category_info(text_instances)
        
        print(f"\nParsed Category Info:")
        print(f"  Name: {category_info['name']}")
        print(f"  Chapter: {category_info['chapter']}")
        print(f"  Description: {category_info['description'][:100]}..." if len(category_info['description']) > 100 else f"  Description: {category_info['description']}")
        
        # Save to database with actual page number from footer
        if category_info["name"] or category_info["chapter"]:
            category_id = self.save_category_to_db(category_info, actual_page_number)
            doc.close()
            return category_id
        else:
            print("⚠️  No valid category information found")
            doc.close()
            return None
    
    def get_exclusion_regions(self, pdf_name, page_number):
        """Get header/footer regions from database."""
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
            "header_region": [result[2], result[3], result[4], result[5]],
            "footer_region": [result[6], result[7], result[8], result[9]]
        }


def main():
    parser = argparse.ArgumentParser(description="Extract category information from PDF headers")
    parser.add_argument("--pdf", help="Path to PDF file")
    parser.add_argument("--page", type=int, default=5, help="Page number to extract (default: 5)")
    parser.add_argument("--pages", nargs="+", type=int, help="Multiple pages to extract (e.g., --pages 5 16 31)")
    
    args = parser.parse_args()
    
    # Get PDF path - use script directory for relative paths
    script_dir = Path(__file__).parent
    
    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        # Default to Press_Couplings.pdf - check multiple locations
        possible_paths = [
            script_dir / "Press_Couplings.pdf",              # Layer_1-Extraction_b/Press_Couplings.pdf
            script_dir / "PDF" / "Press_Couplings.pdf",      # Layer_1-Extraction_b/PDF/Press_Couplings.pdf
            script_dir.parent / "PDF" / "Press_Couplings.pdf" # Project_Hydroscand-Hoses/PDF/Press_Couplings.pdf
        ]
        
        pdf_path = None
        for path in possible_paths:
            if path.exists():
                pdf_path = path
                break
        
        if not pdf_path:
            print(f"❌ PDF not found in any of these locations:")
            for path in possible_paths:
                print(f"   - {path}")
            return
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    extractor = CategoryExtractor()
    
    # Determine which pages to process
    pages_to_process = args.pages if args.pages else [args.page]
    
    print(f"📖 Extracting categories from {len(pages_to_process)} page(s)")
    print(f"📄 Using PDF: {pdf_path}")
    
    for page_num in pages_to_process:
        extractor.extract_category_from_page(str(pdf_path), page_num)
    
    print(f"\n✅ Category extraction complete!")


if __name__ == "__main__":
    main()
