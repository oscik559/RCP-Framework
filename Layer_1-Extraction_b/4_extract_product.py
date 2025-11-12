#!/usr/bin/env python3
"""
Coupling Product Extractor
===========================

Enhanced extractor for coupling (presskopplingar) products that captures:
- Product codes (e.g., 4270-2, 4200-11)
- Product descriptions (e.g., M-gängad, G-gängad)
- Thread specifications (e.g., Rak inv., 24° låtsningskona)
- Product groups (e.g., PRODUKTGRUPP 300)
- Technical specifications from tables

EXTRACTION STRATEGY:
-------------------
1. Extract text blocks from PDF to find product headers
2. Match product codes using regex patterns
3. Extract descriptive text near product codes
4. Load table data for specifications
5. Combine into complete product records

USAGE:
-----
python 4_extract_product.py --pdf Press_Couplings.pdf --page 5
python 4_extract_product.py --pdf Press_Couplings.pdf --pages 5-10
"""

import os
import sys
import json
import sqlite3
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF

# Add current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from db_utils import DatabaseManager


class CouplingExtractor:
    """
    Enhanced coupling extractor that captures product details from text and tables.
    
    Extracts:
    - Product codes (4270-2, 4200-11, etc.)
    - Product descriptions (M-gängad, G-gängad, etc.)
    - Thread specifications (Rak inv., 24° låtsningskona med O-ring)
    - Product groups (PRODUKTGRUPP 300)
    - Table specifications (dimensions, pressures, etc.)
    """
    
    # Regex patterns for product extraction
    PRODUCT_CODE_PATTERN = re.compile(r'\b(\d{4}-\d{1,2}[A-Z]*)\b')
    PRODUCT_GROUP_PATTERN = re.compile(r'PRODUKTGRUPP\s+(\d+)', re.IGNORECASE)
    
    def __init__(self, use_test_db=False):
        """
        Initialize coupling extractor.
        
        Args:
            use_test_db (bool): If True, use harvested_test.db instead of harvested.db
        """
        # Use test database if requested, default to Layer_1-Extraction_b/data/database
        script_dir = Path(__file__).parent
        if use_test_db:
            db_path = script_dir / "data/database/harvested_test.db"
        else:
            db_path = script_dir / "data/database/harvested.db"
        
        self.db_manager = DatabaseManager(str(db_path))
        
        if not self.db_manager.init_database():
            raise RuntimeError("Database initialization failed")
        
        # Use main project tables directory  
        main_data_dir = script_dir.parent / "data"
        self.tables_dir = main_data_dir / "tables"
        
        # Local directories
        local_data_dir = script_dir / "data"
        local_data_dir.mkdir(parents=True, exist_ok=True)
        self.regions_dir = local_data_dir / "regions"
        self.regions_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Using database: {db_path}")
        print(f"📁 Tables directory: {self.tables_dir}")
        print(f"📁 Regions directory: {self.regions_dir}")
    
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
    
    def load_family_regions(self, page_number):
        """
        Load family regions detected above tables.
        
        Args:
            page_number (int): Page number
            
        Returns:
            list: List of family region dictionaries
        """
        family_regions = []
        
        # Load family regions file
        regions_file = self.regions_dir / f"page_{page_number:03d}_family_regions.json"
        
        if not regions_file.exists():
            print(f"⚠️  No family regions found: {regions_file.name}")
            return family_regions
        
        try:
            with open(regions_file, 'r', encoding='utf-8') as f:
                regions_data = json.load(f)
                family_regions = regions_data.get('family_regions', [])
                
        except Exception as e:
            print(f"⚠️  Could not load family regions: {e}")
        
        return family_regions
    
    def extract_page_text(self, pdf_path, page_number):
        """
        Extract text from page with position information.
        
        Args:
            pdf_path (Path): Path to PDF
            page_number (int): Page number (1-based)
            
        Returns:
            dict: Page text and metadata including text blocks with positions
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)
            
            # Get text with detailed structure
            text_dict = page.get_text("dict")
            plain_text = page.get_text("text")
            
            # Get text blocks with positions
            blocks = page.get_text("blocks")  # Returns tuples: (x0, y0, x1, y1, "text", block_no, block_type)
            
            result = {
                'page_number': page_number,
                'text_dict': text_dict,
                'plain_text': plain_text,
                'blocks': blocks,
                'page_width': page.rect.width,
                'page_height': page.rect.height
            }
            
            doc.close()
            return result
            
        except Exception as e:
            print(f"❌ Error extracting page {page_number}: {e}")
            return None
    
    def save_product_knowledge(self, content, page_number, pdf_name="Press_Couplings.pdf", 
                             knowledge_type="TECHNICAL", section_title=None, category="PRESSKOPPLINGAR"):
        """
        Save product knowledge/documentation to database.
        
        Args:
            content (str): Text content to save
            page_number (int): Page number
            pdf_name (str): Source PDF filename  
            knowledge_type (str): Type of knowledge (TECHNICAL, DESCRIPTION, etc.)
            section_title (str): Section heading
            category (str): Product category
            
        Returns:
            bool: Success status
        """
        if not content or len(content.strip()) < 10:
            return False
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO product_knowledge (
                    pdf_name,
                    page_number,
                    category,
                    knowledge_type,
                    section_title,
                    content,
                    content_language
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pdf_name,
                page_number,
                category,
                knowledge_type,
                section_title,
                content.strip(),
                'sv'  # Swedish content
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"      ✗ Error saving knowledge: {e}")
            conn.close()
            return False
    
    def extract_and_save_page_knowledge(self, page_data, page_number, pdf_name):
        """
        Extract and save general page knowledge (non-product specific content).
        
        Args:
            page_data (dict): Page data from extract_page_text
            page_number (int): Page number
            pdf_name (str): PDF filename
        """
        plain_text = page_data.get('plain_text', '')
        
        if plain_text and len(plain_text.strip()) > 50:
            # Save as general technical content
            self.save_product_knowledge(
                content=plain_text,
                page_number=page_number,
                pdf_name=pdf_name,
                knowledge_type="TECHNICAL",
                section_title=f"Page {page_number} Content"
            )
    
    def extract_family_info_from_region(self, family_region: Dict, page_data: Dict) -> Dict:
        """
        Extract family information from a detected family region.
        
        Args:
            family_region (Dict): Family region with bbox coordinates
            page_data (Dict): Page data from extract_page_text
            
        Returns:
            Dict: Extracted family information
        """
        bbox = family_region['bbox']
        blocks = page_data.get('blocks', [])
        
        # Extract text from blocks within the family region
        family_text_blocks = []
        
        for block in blocks:
            if len(block) < 5:
                continue
            
            x0, y0, x1, y1, text, *_ = block
            
            # Check if block overlaps with family region
            if (x0 < bbox[2] and x1 > bbox[0] and 
                y0 < bbox[3] and y1 > bbox[1]):
                
                family_text_blocks.append({
                    'bbox': [x0, y0, x1, y1],
                    'text': text.strip(),
                    'y_center': (y0 + y1) / 2
                })
        
        # Sort blocks by vertical position (top to bottom)
        family_text_blocks.sort(key=lambda b: b['y_center'])
        
        # Extract family components
        family_info = {
            'family_code': None,
            'family_name': None,
            'description': None,
            'product_group': None,
            'raw_text': '',
            'text_blocks': family_text_blocks
        }
        
        # Combine all text for analysis
        all_text = ' '.join([block['text'] for block in family_text_blocks])
        family_info['raw_text'] = all_text
        
        # Basic pattern matching for key information
        lines = all_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for product group
            if 'PRODUKTGRUPP' in line.upper():
                group_match = re.search(r'PRODUKTGRUPP\s+(\d+)', line, re.IGNORECASE)
                if group_match:
                    family_info['product_group'] = group_match.group(1)
            
            # Look for family code (4-digit numbers)
            elif re.match(r'^\d{4}$', line):
                family_info['family_code'] = line
            
            # Look for family names (common threading types)
            elif any(term in line for term in ['gängad', 'Gängad', 'inv.', 'låtsningskona']):
                if not family_info['family_name']:
                    family_info['family_name'] = line
                else:
                    # Additional description
                    family_info['description'] = line
        
        return family_info
    
    def find_product_headers(self, blocks: List, page_width: float) -> List[Dict]:
        """
        Find product header blocks containing product codes and descriptions.
        
        Args:
            blocks: Text blocks from PyMuPDF
            page_width: Page width for column detection
            
        Returns:
            List of product header dictionaries with position and text
        """
        product_headers = []
        
        for block in blocks:
            if len(block) < 5:
                continue
            
            x0, y0, x1, y1, text, *_ = block
            text = text.strip()
            
            # Look for product codes (e.g., 4270-2, 4200-11)
            product_codes = self.PRODUCT_CODE_PATTERN.findall(text)
            
            if product_codes:
                # Extract product group if present
                product_group_match = self.PRODUCT_GROUP_PATTERN.search(text)
                product_group = product_group_match.group(1) if product_group_match else None
                
                # Determine column (left or right)
                center_x = (x0 + x1) / 2
                column = 'left' if center_x < page_width / 2 else 'right'
                
                # Extract description lines (usually near product code)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                for product_code in product_codes:
                    # Find the line with this product code
                    code_line_idx = None
                    for idx, line in enumerate(lines):
                        if product_code in line:
                            code_line_idx = idx
                            break
                    
                    # Extract description (lines after product code)
                    description_parts = []
                    if code_line_idx is not None and code_line_idx + 1 < len(lines):
                        # Get up to 3 lines after product code
                        for i in range(code_line_idx + 1, min(code_line_idx + 4, len(lines))):
                            desc = lines[i]
                            # Skip if it looks like another product code or group
                            if not self.PRODUCT_CODE_PATTERN.match(desc) and 'PRODUKTGRUPP' not in desc:
                                description_parts.append(desc)
                    
                    product_headers.append({
                        'product_code': product_code,
                        'description': ' | '.join(description_parts),
                        'product_group': product_group,
                        'bbox': (x0, y0, x1, y1),
                        'column': column,
                        'full_text': text
                    })
        
        return product_headers
    
    def match_products_with_tables(self, product_headers: List[Dict], tables: List[Dict]) -> Dict:
        """
        Match product headers with their corresponding specification tables.
        
        Args:
            product_headers: List of product header dictionaries
            tables: List of table dictionaries with bbox information
            
        Returns:
            Dictionary mapping product codes to their table data
        """
        matches = {}
        
        for product in product_headers:
            product_code = product['product_code']
            product_y = product['bbox'][3]  # Bottom of product header
            column = product['column']
            
            # Find the closest table below this product in the same column
            closest_table = None
            min_distance = float('inf')
            
            for table in tables:
                table_bbox = table.get('bbox', [0, 0, 0, 0])
                table_y = table_bbox[1]  # Top of table
                
                # Check if table is in same column
                table_center_x = (table_bbox[0] + table_bbox[2]) / 2
                table_column = 'left' if table_center_x < 297.5 else 'right'
                
                if table_column != column:
                    continue
                
                # Check if table is below product header
                if table_y > product_y:
                    distance = table_y - product_y
                    if distance < min_distance:
                        min_distance = distance
                        closest_table = table
            
            if closest_table:
                matches[product_code] = {
                    'product_info': product,
                    'table_data': closest_table
                }
            else:
                # No table found, still save product info
                matches[product_code] = {
                    'product_info': product,
                    'table_data': None
                }
        
        return matches
    
    def extract_products_from_table(self, table_data, product_info, page_number):
        """
        Extract individual products from table data and store table content in DB.
        
        Args:
            table_data (dict): Table dictionary
            product_info (dict): Product information (family_info or legacy product_info)
            page_number (int): Page number
            
        Returns:
            list: List of product dictionaries
        """
        products = []
        
        # Handle both family_info and legacy product_info structures
        if 'family_code' in product_info:
            # New family_info structure
            family_code = product_info['family_code']
            description = product_info['family_name']
            product_group = product_info['product_group']
            bbox = None  # Family regions don't have individual bbox
        else:
            # Legacy product_info structure
            family_code = product_info.get('product_code')
            description = product_info.get('description')
            product_group = product_info.get('product_group')
            bbox = product_info.get('bbox')
        
        if not table_data:
            # No table, create single product from info only
            specs = {
                'type': 'COUPLING',
                'description': description,
                'product_group': product_group,
                'page': page_number,
                'extraction_source': 'header_only'
            }
            
            return [{
                'product_code': family_code,
                'product_name': description,
                'specifications': json.dumps(specs, ensure_ascii=False),
                'page_number': page_number,
                'bbox': bbox,
                'table_data': None
            }]
        
        content = table_data.get('content', [])
        if not content:
            return products
        
        # Store the complete table structure for reference
        table_metadata = {
            'table_bbox': table_data.get('bbox'),
            'table_dimensions': f"{len(content)}x{len(content[0]) if content else 0}",
            'extraction_source': 'table_content',
            'raw_table_data': table_data  # Store complete table data
        }
        
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
            
            # Build comprehensive specifications including table position
            specs = {
                'type': 'COUPLING',
                'family_code': family_code,
                'family_description': description,
                'product_group': product_group,
                'artikelnr': article_nr,
                'page': page_number,
                'table_row': row_idx,
                'extraction_source': 'table_content'
            }
            
            # Extract structured field mappings from table headers and values
            field_mappings = {}
            for col_idx, value in enumerate(row[1:], start=1):
                if col_idx < len(headers):
                    header = headers[col_idx].strip()
                    clean_value = value.strip() if value else ""
                    
                    if clean_value:
                        # Store with original header name and normalized key
                        field_key = header.lower().replace(' ', '_').replace('-', '_')
                        specs[header] = clean_value  # Original header
                        specs[field_key] = clean_value  # Normalized key
                        field_mappings[header] = clean_value
            
            # Add table metadata to specifications
            specs['table_metadata'] = table_metadata
            specs['field_mappings'] = field_mappings
            specs['headers'] = headers
            
            products.append({
                'product_code': article_nr,
                'product_name': f"{description} - {article_nr}",
                'specifications': json.dumps(specs, ensure_ascii=False),
                'page_number': page_number,
                'bbox': table_data.get('bbox'),
                'table_data': table_data,  # Include full table data
                'table_row_index': row_idx,
                'table_headers': headers
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
            family_code (str): Family code (e.g., 4270-2)
            name (str): Family name
            **kwargs: Additional family fields
            
        Returns:
            int: Family ID
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Try to find existing by family_code
        cursor.execute("""
            SELECT id FROM product_families
            WHERE family_code = ?
        """, (family_code,))
        
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
        
        print(f"   📦 Created family: {family_code} - {name}")
        return family_id
    
    def save_extracted_table(self, table_data, page_number, pdf_name="Press_Couplings.pdf"):
        """
        Save raw extracted table data to database for later analysis.
        
        Args:
            table_data (dict): Complete table data from JSON
            page_number (int): Page number
            pdf_name (str): Source PDF filename
            
        Returns:
            int: Table ID if saved successfully, None otherwise
        """
        if not table_data:
            return None
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if extracted_tables table exists, create if needed
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extracted_tables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    table_number INTEGER NOT NULL,
                    bbox TEXT,
                    table_data TEXT NOT NULL,
                    dimensions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(filename, page_number, table_number)
                )
            """)
            
            bbox = table_data.get('bbox', [])
            bbox_json = json.dumps(bbox) if bbox else None
            
            content = table_data.get('content', [])
            dimensions = f"{len(content)}x{len(content[0]) if content else 0}"
            
            # Extract table number from filename or use sequence
            cursor.execute("""
                SELECT COALESCE(MAX(table_number), 0) + 1 
                FROM extracted_tables 
                WHERE filename = ? AND page_number = ?
            """, (pdf_name, page_number))
            
            table_number = cursor.fetchone()[0]
            
            # Store complete table data as JSON
            cursor.execute("""
                INSERT OR REPLACE INTO extracted_tables (
                    filename,
                    page_number, 
                    table_number,
                    bbox,
                    table_data,
                    dimensions
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pdf_name,
                page_number,
                table_number,
                bbox_json,
                json.dumps(table_data, ensure_ascii=False),
                dimensions
            ))
            
            table_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"      📊 Saved table {table_number} ({dimensions}) for page {page_number}")
            return table_id
            
        except Exception as e:
            print(f"      ✗ Error saving table data: {e}")
            conn.rollback()
            conn.close()
            return None

    def save_product(self, family_id, product_code, product_name, specifications, page_number, bbox=None, table_data=None):
        """
        Save product to database with enhanced table tracking.
        
        Args:
            family_id (int): Parent family ID
            product_code (str): Product code
            product_name (str): Product name/description
            specifications (str): JSON specifications
            page_number (int): Page number
            bbox (tuple): Bounding box (x0, y0, x1, y1)
            table_data (dict): Associated table data
            
        Returns:
            bool: Success status
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            bbox_json = json.dumps(bbox) if bbox else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    family_id,
                    product_code,
                    specifications,
                    bounding_box,
                    page_number
                ) VALUES (?, ?, ?, ?, ?)
            """, (family_id, product_code, specifications, bbox_json, page_number))
            
            conn.commit()
            conn.close()
            
            print(f"      ✓ {product_code}: {product_name}")
            return True
            
        except Exception as e:
            print(f"      ✗ Error saving product {product_code}: {e}")
            conn.close()
            return False
    
    def process_page(self, pdf_path, page_number):
        """
        Process a single page with enhanced product extraction.
        
        Args:
            pdf_path (Path): PDF path
            page_number (int): Page number
            
        Returns:
            dict: Processing statistics
        """
        print(f"\n📄 Processing page {page_number}...")
        
        stats = {
            'families': 0,
            'products': 0,
            'product_headers': 0
        }
        
        # Extract page text
        page_data = self.extract_page_text(pdf_path, page_number)
        if not page_data:
            print(f"   ❌ Failed to extract page text")
            return stats
        
        # Find product headers
        product_headers = self.find_product_headers(
            page_data['blocks'],
            page_data['page_width']
        )
        
        stats['product_headers'] = len(product_headers)
        
        if not product_headers:
            print(f"   ⚠️  No product headers found on page {page_number}")
            return stats
        
        print(f"   Found {len(product_headers)} product headers")
        for ph in product_headers:
            print(f"      • {ph['product_code']}: {ph['description'][:50] if ph['description'] else 'No description'}")
        
        # Save general page knowledge (non-product text content)
        self.extract_and_save_page_knowledge(page_data, page_number, pdf_path.name)
        
        # Load table data and family regions
        tables = self.load_table_data(page_number)
        family_regions = self.load_family_regions(page_number)
        print(f"   Found {len(tables)} tables, {len(family_regions)} family regions")
        
        # If we have family regions, use them instead of regex-based headers
        if family_regions:
            # Extract family information from regions
            family_info_list = []
            for i, family_region in enumerate(family_regions):
                family_info = self.extract_family_info_from_region(family_region, page_data)
                family_info['region_id'] = i + 1
                family_info['table_id'] = family_region.get('table_id', i + 1)
                family_info_list.append(family_info)
                
                print(f"      Family {i+1}: code='{family_info['family_code']}', name='{family_info['family_name']}', group='{family_info['product_group']}'")
            
            # Match family info with tables directly by position/ID
            product_matches = {}
            for i, (family_info, table) in enumerate(zip(family_info_list, tables)):
                family_code = family_info['family_code'] or f"FAMILY_{i+1}"
                product_matches[family_code] = {
                    'family_info': family_info,
                    'table_data': table
                }
        else:
            # Fallback to regex-based matching
            product_matches = self.match_products_with_tables(product_headers, tables)
        
        # Create category
        category_id = self.save_category(
            name="PRESSKOPPLINGAR",
            chapter="4",
            description="Press couplings for hydraulic hoses"
        )
        
        # First, save all table data to extracted_tables for reference
        table_ids = {}
        for table in tables:
            table_id = self.save_extracted_table(table, page_number)
            if table_id:
                table_ids[id(table)] = table_id
        
        # Process each product family
        for product_code, match_data in product_matches.items():
            # Handle both new family_info structure and old product_info structure
            if 'family_info' in match_data:
                family_info = match_data['family_info']
                family_code = family_info['family_code'] or product_code
                family_name = family_info['family_name'] or 'Unknown Family'
                family_description = family_info['description']
                product_group = family_info['product_group']
                
                # Build construction details JSON
                construction_details = {
                    'product_group': product_group,
                    'raw_family_text': family_info['raw_text'],
                    'extraction_source': 'family_region'
                }
                
            else:
                # Fallback to old structure
                product_info = match_data['product_info']
                family_code = product_code
                family_name = product_info.get('description', product_code)
                family_description = product_info.get('description')
                product_group = product_info.get('product_group')
                
                construction_details = {
                    'product_group': product_group,
                    'extraction_source': 'regex_headers'
                }
            
            table_data = match_data['table_data']
            
            # Create family for this product series
            family_id = self.save_family(
                category_id=category_id,
                family_code=family_code,
                name=family_name,
                description=family_description,
                construction_details=json.dumps(construction_details, ensure_ascii=False),
                page_number=page_number
            )
            stats['families'] += 1
            
            # Extract products from table (or just header if no table)
            # Use family_info if available, otherwise fall back to product_info
            info_for_extraction = family_info if 'family_info' in match_data else match_data.get('product_info', {})
            products = self.extract_products_from_table(table_data, info_for_extraction, page_number)
            
            # Get table ID for linking
            table_id = table_ids.get(id(table_data)) if table_data else None
            
            # Save products with table references
            for product in products:
                # Add table reference to specifications if available
                if table_id and product.get('table_data'):
                    specs_dict = json.loads(product['specifications'])
                    specs_dict['extracted_table_id'] = table_id
                    specs_dict['table_reference'] = {
                        'table_id': table_id,
                        'row_index': product.get('table_row_index'),
                        'headers': product.get('table_headers', [])
                    }
                    product['specifications'] = json.dumps(specs_dict, ensure_ascii=False)
                
                success = self.save_product(
                    family_id,
                    product['product_code'],
                    product['product_name'],
                    product['specifications'],
                    product['page_number'],
                    product.get('bbox'),
                    product.get('table_data')
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
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use test database (harvested_test.db) instead of production"
    )
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    extractor = CouplingExtractor(use_test_db=args.test)
    
    # Determine page range
    if args.page:
        pages = [args.page]
    elif args.pages:
        start, end = map(int, args.pages.split('-'))
        pages = range(start, end + 1)
    else:
        print("❌ Specify --page or --pages")
        sys.exit(1)
    
    db_name = "harvested_test.db" if args.test else "harvested.db"
    print(f"\n🔧 Extracting couplings from {pdf_path.name}")
    print(f"🗄️  Database: {db_name}")
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
