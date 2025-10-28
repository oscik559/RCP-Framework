#!/usr/bin/env python3
"""
Header/Footer Region Marking

This script defines header/footer exclusion regions and saves them to database
for use by table extraction scripts.
"""

import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
import sqlite3
from PIL import Image, ImageDraw, ImageFont


class RegionManager:
    def __init__(self):
        """Initialize the RegionManager."""
        self.db_path = Path("data/products.db")
        self.output_dir = Path("data/output")
        self.pages_dir = Path("data/pages")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Header/Footer detection thresholds (relative to page height)
        self.header_threshold = 0.05  # Top 5% of page for headers
        self.footer_threshold = 0.95  # Bottom 5% of page (from 95% down)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with page regions table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create page_regions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS page_regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_number INTEGER,
                pdf_name TEXT,
                page_width REAL,
                page_height REAL,
                header_x0 REAL,
                header_y0 REAL,
                header_x1 REAL,
                header_y1 REAL,
                footer_x0 REAL,
                footer_y0 REAL,
                footer_x1 REAL,
                footer_y1 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(page_number, pdf_name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_regions_to_database(self, pdf_path, page_number, results):
        """
        Save header/footer region information to database.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number
            results: Detection results dictionary
        """
        pdf_name = Path(pdf_path).stem
        page_size = results["page_size"]
        header_region = results["header_region"]
        footer_region = results["footer_region"]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert or replace region data
            cursor.execute('''
                INSERT OR REPLACE INTO page_regions (
                    page_number, pdf_name, page_width, page_height,
                    header_x0, header_y0, header_x1, header_y1,
                    footer_x0, footer_y0, footer_x1, footer_y1
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_number, pdf_name, page_size[0], page_size[1],
                header_region[0], header_region[1], header_region[2], header_region[3],
                footer_region[0], footer_region[1], footer_region[2], footer_region[3]
            ))
            
            conn.commit()
            print(f"Saved region data to database for page {page_number}")
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_regions_from_database(self, pdf_name=None, page_number=None):
        """
        Get header/footer region information from database.
        
        Args:
            pdf_name: Optional PDF name filter
            page_number: Optional page number filter
            
        Returns:
            List of region records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pdf_name and page_number:
            cursor.execute('''
                SELECT * FROM page_regions 
                WHERE pdf_name = ? AND page_number = ?
            ''', (pdf_name, page_number))
        elif pdf_name:
            cursor.execute('''
                SELECT * FROM page_regions 
                WHERE pdf_name = ?
                ORDER BY page_number
            ''', (pdf_name,))
        else:
            cursor.execute('SELECT * FROM page_regions ORDER BY pdf_name, page_number')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_exclusion_regions(self, pdf_name, page_number):
        """
        Get header/footer regions as exclusion zones for table extraction.
        
        Args:
            pdf_name: PDF filename (without extension)
            page_number: Page number
            
        Returns:
            Dictionary with header and footer regions, or None if not found
        """
        regions = self.get_regions_from_database(pdf_name, page_number)
        
        if not regions:
            return None
        
        region = regions[0]  # Should only be one result
        
        return {
            "page_size": [region[3], region[4]],  # width, height
            "header_region": [region[5], region[6], region[7], region[8]],
            "footer_region": [region[9], region[10], region[11], region[12]]
        }
    
    def define_regions(self, pdf_path, page_number):
        """
        Define header and footer regions for a PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-based)
            
        Returns:
            Dictionary with region information
        """
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
        
        page = doc.load_page(page_number - 1)
        page_rect = page.rect
        page_height = page_rect.height
        page_width = page_rect.width
        
        # Define header and footer regions
        header_region = [0, 0, page_width, page_height * self.header_threshold]
        footer_region = [0, page_height * self.footer_threshold, page_width, page_height]
        
        doc.close()
        
        return {
            "page": page_number,
            "page_size": [page_width, page_height],
            "header_region": header_region,
            "footer_region": footer_region
        }
    
    def mark_regions_on_image(self, page_number, results):
        """
        Mark header/footer regions on PNG image.
        
        Args:
            page_number: Page number
            results: Region results dictionary
        """
        # Find PNG file
        pdf_name = "Produktbok"  # Assuming standard name
        png_filename = f"{pdf_name}_page_{page_number:03d}.png"
        png_path = self.pages_dir / png_filename
        
        if not png_path.exists():
            print(f"Warning: PNG file not found: {png_path}")
            return
        
        # Load image
        image = Image.open(png_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load font
        try:
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
        except:
            font_small = ImageFont.load_default()
        
        # Scale regions to image coordinates
        pdf_size = results["page_size"]
        img_size = image.size
        
        # Calculate scaling factors (assuming 300 DPI)
        scale_factor = 300 / 72.0
        x_scale = img_size[0] / (pdf_size[0] * scale_factor)
        y_scale = img_size[1] / (pdf_size[1] * scale_factor)
        
        # Scale header region
        h = results["header_region"]
        header_box = [
            int(h[0] * scale_factor * x_scale),
            int(h[1] * scale_factor * y_scale),
            int(h[2] * scale_factor * x_scale),
            int(h[3] * scale_factor * y_scale)
        ]
        
        # Scale footer region
        f = results["footer_region"]
        footer_box = [
            int(f[0] * scale_factor * x_scale),
            int(f[1] * scale_factor * y_scale),
            int(f[2] * scale_factor * x_scale),
            int(f[3] * scale_factor * y_scale)
        ]
        
        # Draw regions
        draw.rectangle(header_box, outline="red", width=3)
        draw.text((header_box[0] + 5, header_box[1] + 5), "HEADER REGION", 
                 fill="red", font=font_small)
        
        draw.rectangle(footer_box, outline="red", width=3)
        draw.text((footer_box[0] + 5, footer_box[1] + 5), "FOOTER REGION", 
                 fill="red", font=font_small)
        
        # Save marked image
        output_filename = f"Produktbok_page_{page_number:03d}_regions.png"
        output_path = self.output_dir / output_filename
        image.save(output_path)
        print(f"Marked regions saved: {output_path}")
    
    def process_page(self, pdf_path, page_number):
        """
        Process a single page and save regions to database.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to process
        """
        print(f"Processing page {page_number}")
        
        # Define regions
        results = self.define_regions(pdf_path, page_number)
        
        # Save to database
        self.save_regions_to_database(pdf_path, page_number, results)
        
        # Mark regions on image
        self.mark_regions_on_image(page_number, results)
        
        print(f"Saved regions and marked image for page {page_number}")
        return results
    
    def process_all_pages(self, pdf_path):
        """
        Process all pages and save regions to database.
        
        Args:
            pdf_path: Path to PDF file
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        print(f"Processing {total_pages} pages")
        
        for page_num in range(1, total_pages + 1):
            try:
                self.process_page(pdf_path, page_num)
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
        
        # Show summary
        pdf_name = Path(pdf_path).stem
        regions = self.get_regions_from_database(pdf_name)
        print(f"\nCompleted: {len(regions)} regions saved to database")


def main():
    parser = argparse.ArgumentParser(description="Define header/footer exclusion regions")
    parser.add_argument("--pdf-path", default="PDF/Produktbok.pdf", help="Path to PDF file")
    parser.add_argument("--page", type=int, help="Specific page number to process")
    parser.add_argument("--all-pages", action="store_true", help="Process all pages")
    parser.add_argument("--show-regions", action="store_true", help="Show existing regions")
    
    args = parser.parse_args()
    
    manager = RegionManager()
    
    try:
        if args.show_regions:
            # Show existing regions
            pdf_name = Path(args.pdf_path).stem if args.pdf_path else None
            regions = manager.get_regions_from_database(pdf_name)
            
            if not regions:
                print("No regions found in database")
            else:
                print(f"Found {len(regions)} regions:")
                for region in regions:
                    print(f"  {region[2]} Page {region[1]}: "
                          f"Header[{region[5]:.0f},{region[6]:.0f},{region[7]:.0f},{region[8]:.0f}] "
                          f"Footer[{region[9]:.0f},{region[10]:.0f},{region[11]:.0f},{region[12]:.0f}]")
        
        elif args.all_pages:
            # Process all pages
            pdf_path = Path(args.pdf_path)
            if not pdf_path.exists():
                print(f"Error: PDF file not found: {pdf_path}")
                sys.exit(1)
            manager.process_all_pages(pdf_path)
        
        elif args.page:
            # Process single page
            pdf_path = Path(args.pdf_path)
            if not pdf_path.exists():
                print(f"Error: PDF file not found: {pdf_path}")
                sys.exit(1)
            manager.process_page(pdf_path, args.page)
        
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()