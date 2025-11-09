#!/usr/bin/env python3
"""
Coupling Product Extractor
===========================

Specialized extractor for coupling (presskopplingar) products.
Adapted from the hose product extractor with coupling-specific logic.

Key differences from hose extraction:
- Focus on thread specifications (G-thread, JIC, SAE, ORFS, etc.)
- Hose compatibility instead of dimensions
- Different table structures
- Assembly requirements

USAGE:
-----
python 2_extract_couplings.py --pdf Produktbok_2020_Coupling.pdf --page 170
python 2_extract_couplings.py --pdf Produktbok_2020_Coupling.pdf --pages 170-180
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
import fitz  # PyMuPDF

# Add Layer_1-Extraction to path
sys.path.append(str(Path(__file__).parent.parent / "Layer_1-Extraction"))
from db_utils import DatabaseManager


class CouplingExtractor:
    """
    Extracts coupling product data from catalog pages.
    
    Handles:
    - Product families (e.g., Hylsa EN15C, G-gängade kopplingar)
    - Individual coupling products with specifications
    - Thread types and compatibility information
    - Hose compatibility mappings
    """
    
    def __init__(self):
        """Initialize coupling extractor."""
        self.db_manager = DatabaseManager()
        
        if not self.db_manager.init_database():
            raise RuntimeError("Database initialization failed")
        
        self.tables_dir = Path("data/tables")
        self.tables_dir.mkdir(parents=True, exist_ok=True)
    
    def load_table_data(self, page_number):
        """
        Load pre-extracted table data for a page.
        
        Args:
            page_number (int): Page number
            
        Returns:
            list: List of table dictionaries
        """
        tables = []
        
        # Look for all tables on this page
        table_files = sorted(self.tables_dir.glob(f"page_{page_number:03d}_table_*.json"))
        
        for table_file in table_files:
            try:
                with open(table_file, 'r', encoding='utf-8') as f:
                    table_data = json.load(f)
                    tables.append(table_data)
            except Exception as e:
                print(f"⚠️  Could not load {table_file}: {e}")
        
        return tables
    
    def extract_page_text(self, pdf_path, page_number):
        """
        Extract text from page.
        
        Args:
            pdf_path (Path): Path to PDF
            page_number (int): Page number (1-based)
            
        Returns:
            dict: Page text and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)
            
            text_dict = page.get_text("dict")
            plain_text = page.get_text("text")
            
            result = {
                'page_number': page_number,
                'text_dict': text_dict,
                'plain_text': plain_text
            }
            
            doc.close()
            return result
            
        except Exception as e:
            print(f"❌ Error extracting page {page_number}: {e}")
            return None
    
    def parse_coupling_family(self, text, page_number):
        """
        Parse coupling family information from page text.
        
        Args:
            text (str): Page text
            page_number (int): Page number
            
        Returns:
            dict: Family information or None
        """
        # Look for family code patterns (e.g., "4200-07", "4201-1")
        import re
        family_pattern = r'(\d{4}-\d{1,2})'
        
        # Look for family names (e.g., "Hylsa EN15C", "G-gängade kopplingar")
        # This is simplified - in production you'd use more sophisticated parsing
        
        # For now, return None - this needs to be enhanced with actual patterns
        return None
    
    def extract_products_from_table(self, table_data, family_id, page_number):
        """
        Extract individual products from table data.
        
        Args:
            table_data (dict): Table dictionary
            family_id (int): Parent family ID
            page_number (int): Page number
            
        Returns:
            list: List of product dictionaries
        """
        products = []
        
        content = table_data.get('content', [])
        if not content:
            return products
        
        # Detect header row (first row usually)
        headers = content[0] if content else []
        
        # Process data rows
        for row_idx, row in enumerate(content[1:], start=1):
            if not row or len(row) == 0:
                continue
            
            # Extract article number (usually first column)
            article_nr = row[0].strip() if row else ""
            
            if not article_nr or not article_nr[0].isdigit():
                continue
            
            # Build specifications
            specs = {
                'type': 'COUPLING',
                'artikelnr': article_nr,
                'page': page_number
            }
            
            # Try to extract common coupling fields
            for col_idx, value in enumerate(row[1:], start=1):
                if col_idx < len(headers):
                    header = headers[col_idx].strip().lower()
                    
                    # Map header to spec field
                    if 'används' in header or 'anvands' in header:
                        specs['used_with'] = value.strip()
                    elif 'slang' in header:
                        specs['hose_id'] = value.strip()
                    elif 'gäng' in header or 'gang' in header:
                        specs['thread'] = value.strip()
                    elif 'dimension' in header:
                        specs['dimension'] = value.strip()
                    else:
                        # Generic field
                        specs[f'col_{col_idx}'] = value.strip()
            
            products.append({
                'product_code': article_nr,
                'specifications': json.dumps(specs, ensure_ascii=False),
                'page_number': page_number
            })
        
        return products
    
    def save_category(self, name, chapter, description=None):
        """
        Save or get category.
        
        Args:
            name (str): Category name
            chapter (str): Chapter code
            description (str): Optional description
            
        Returns:
            int: Category ID
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Try to find existing
        cursor.execute("""
            SELECT id FROM categories
            WHERE name = ? AND chapter = ?
        """, (name, chapter))
        
        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]
        
        # Create new
        cursor.execute("""
            INSERT INTO categories (name, chapter, description)
            VALUES (?, ?, ?)
        """, (name, chapter, description))
        
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return category_id
    
    def save_family(self, category_id, family_code, name, **kwargs):
        """
        Save or get product family.
        
        Args:
            category_id (int): Parent category ID
            family_code (str): Family code
            name (str): Family name
            **kwargs: Additional family fields
            
        Returns:
            int: Family ID
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Try to find existing
        cursor.execute("""
            SELECT id FROM product_families
            WHERE family_code = ? AND name = ?
        """, (family_code, name))
        
        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]
        
        # Create new
        cursor.execute("""
            INSERT INTO product_families (
                category_id,
                family_code,
                name,
                subtitle,
                description,
                construction_details,
                page_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            category_id,
            family_code,
            name,
            kwargs.get('subtitle'),
            kwargs.get('description'),
            kwargs.get('construction_details'),
            kwargs.get('page_number')
        ))
        
        family_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return family_id
    
    def save_product(self, family_id, product_code, specifications, page_number):
        """
        Save product to database.
        
        Args:
            family_id (int): Parent family ID
            product_code (str): Product code
            specifications (str): JSON specifications
            page_number (int): Page number
            
        Returns:
            bool: Success status
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    family_id,
                    product_code,
                    specifications,
                    page_number
                ) VALUES (?, ?, ?, ?)
            """, (family_id, product_code, specifications, page_number))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️  Error saving product {product_code}: {e}")
            conn.close()
            return False
    
    def process_page(self, pdf_path, page_number):
        """
        Process a single page.
        
        Args:
            pdf_path (Path): PDF path
            page_number (int): Page number
            
        Returns:
            dict: Processing statistics
        """
        print(f"\n📄 Processing page {page_number}...")
        
        stats = {
            'families': 0,
            'products': 0
        }
        
        # Load table data
        tables = self.load_table_data(page_number)
        
        if not tables:
            print(f"   ⚠️  No tables found for page {page_number}")
            print(f"   💡 Run: python Layer_1-Extraction/3_detect_tables.py --pdf {pdf_path} first")
            return stats
        
        print(f"   Found {len(tables)} tables")
        
        # For coupling catalog, we need manual family mapping
        # This is a simplified version - you'd enhance this with actual parsing
        
        # Example: Create a default family for demonstration
        category_id = self.save_category(
            name="PRESSKOPPLINGAR",
            chapter="4:2",
            description="Press couplings for hydraulic hoses"
        )
        
        # Create a placeholder family
        # In production, you'd parse the page text to extract family info
        family_id = self.save_family(
            category_id=category_id,
            family_code="4200-XX",  # Placeholder
            name=f"Couplings from page {page_number}",
            page_number=page_number
        )
        stats['families'] = 1
        
        # Extract products from tables
        for table in tables:
            products = self.extract_products_from_table(table, family_id, page_number)
            
            for product in products:
                success = self.save_product(
                    family_id,
                    product['product_code'],
                    product['specifications'],
                    product['page_number']
                )
                
                if success:
                    stats['products'] += 1
        
        print(f"   ✅ Extracted: {stats['families']} families, {stats['products']} products")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Extract coupling products from catalog"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF file"
    )
    parser.add_argument(
        "--page",
        type=int,
        help="Single page to process"
    )
    parser.add_argument(
        "--pages",
        help="Page range (e.g., '170-180')"
    )
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    extractor = CouplingExtractor()
    
    # Determine page range
    if args.page:
        pages = [args.page]
    elif args.pages:
        start, end = map(int, args.pages.split('-'))
        pages = range(start, end + 1)
    else:
        print("❌ Specify --page or --pages")
        sys.exit(1)
    
    print(f"\n🔧 Extracting couplings from {pdf_path.name}")
    print(f"📖 Pages: {list(pages)}")
    
    total_stats = {'families': 0, 'products': 0}
    
    for page_num in pages:
        stats = extractor.process_page(pdf_path, page_num)
        total_stats['families'] += stats['families']
        total_stats['products'] += stats['products']
    
    print(f"\n✅ Extraction complete!")
    print(f"   Total families: {total_stats['families']}")
    print(f"   Total products: {total_stats['products']}")


if __name__ == "__main__":
    main()
