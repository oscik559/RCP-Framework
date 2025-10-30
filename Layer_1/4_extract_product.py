#!/usr/bin/env python3
"""
Product Data Extractor using Ollama VLM

Extracts product information from PDF pages using a Vision Language Model
and stores the results in a hierarchical SQLite database structure:
- Categories (top level: product groups)
- Product Families (middle level: product lines with shared construction)
- Products (bottom level: individual SKUs with specifications)

Can leverage pre-extracted table data from the detect_tables stage for accuracy.
"""

import os
import sys
import json
import base64
import sqlite3
import argparse
from pathlib import Path
from io import BytesIO
import requests
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from db_utils import DatabaseManager


class ProductExtractor:
    def __init__(self, ollama_url="http://localhost:11434", model_name="qwen3-vl:235b-cloud"):
        """
        Initialize the ProductExtractor.
        
        Args:
            ollama_url: Base URL for Ollama API
            model_name: Name of the VLM model to use
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.db_manager = DatabaseManager()
        self.tables_dir = Path("data/tables")
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        if not self.db_manager.init_database():
            raise RuntimeError("Database not properly initialized")
    

    
    def render_pdf_page(self, pdf_path, page_number, dpi=300):
        """
        Render a PDF page to an image.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-based)
            dpi: DPI for rendering (default: 300)
            
        Returns:
            PIL Image object
        """
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
        
        page = doc.load_page(page_number - 1)  # Convert to 0-based
        
        # Render at specified DPI
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        image = Image.open(BytesIO(img_data))
        
        doc.close()
        return image
    
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string."""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def call_ollama_vlm(self, image, prompt):
        """
        Call Ollama VLM API to analyze the image.
        
        Args:
            image: PIL Image object
            prompt: Text prompt for the VLM
            
        Returns:
            Response from the VLM
        """
        img_base64 = self.image_to_base64(image)
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_base64]
                }
            ],
            "stream": False
        }
        
        try:
            print("🤖 Calling Ollama VLM API (this may take a few minutes)...")
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=300  # 5 minutes - longer timeout for qwen3-vl:latest
            )
            response.raise_for_status()
            print("✓ Received response from VLM")
            return response.json()
        except requests.exceptions.Timeout:
            print("❌ Ollama API timeout (5 minutes) - image may be too large or model is busy")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling Ollama API: {e}")
            return None
    
    def extract_products_from_image(self, image, page_number, table_data=None):
        """
        Extract product information from an image using VLM.
        
        Uses hierarchical structure: category -> families -> individual products
        A page can contain multiple product families.

        Args:
            image: PIL Image object
            page_number: Page number being processed
            table_data: Pre-extracted table data from detect_tables stage (optional)

        Returns:
            Tuple of (category_name, families_list)
            where families_list is a list of family dicts, each containing their products
        """
        
        # Build context from pre-extracted table data if available
        table_context = ""
        if table_data:
            table_context = "\n\n📊 PRE-EXTRACTED TABLE DATA:\n"
            for i, table in enumerate(table_data, 1):
                table_context += f"\nTable {i} ({table.get('rows')}x{table.get('columns')}):\n"
                table_context += json.dumps(table.get('content', []), indent=2, ensure_ascii=False) + "\n"
        
        prompt = f'''You are analyzing a Swedish industrial hose/hydraulic product catalog page. Your task is to understand and extract the hierarchical product information naturally presented on the page.

🚨 CRITICAL LANGUAGE REQUIREMENT: 
- Extract ALL text EXACTLY as written - DO NOT translate anything!
- Only extract, never translate or modify the original text

Image dimensions: {image.size[0]}x{image.size[1]} pixels
{table_context}

📋 TASK: Extract product data in a 3-level hierarchy

🔍 WHAT TO LOOK FOR:

**Level 1 - CATEGORY & CHAPTER** (broad product group):
Find the main category this page belongs to. Look for large headings or chapter references.
Common categories: HÖGTRYCKSSLANG, OLJESLANG, KEMIKALIESLANGAR, etc.

Also look for CHAPTER information in the header region (top of page):
- Look for "KAPITEL" followed by a number and title
- Or chapter references like "1:1", "2:1", etc. with descriptive text
- This appears in the header/top margin area of the page

**Level 2 - PRODUCT FAMILIES** (product lines with shared characteristics):
⚠️ IMPORTANT: A page may contain MULTIPLE product families (1, 2, or more).
Each family typically has:
- A prominent product name/model (often bold or large text)
- A base article/product code that products share (the prefix before size variants)
- Its own "Konstruktion" section describing materials, temperature range, standards
- Its own "Användning och egenskaper" (usage/application) text
- Its own product hose image

The family code is the common prefix in article numbers (e.g., if you see "1059-01-04", "1059-01-06", the family is "1059-01").

**Level 3 - INDIVIDUAL PRODUCTS** (specific SKUs):
Each family has multiple products from its specifications table. Each table row = one product with:
- Complete article number (including size suffix like "-04", "-06", "-12")
- Technical specifications (inner diameter, outer diameter, pressure, bend radius, weight)
- Physical location on page (bounding box)

Some products may have special configurations (like "PÅ BOBIN" for reel products).

🎯 EXTRACTION STRATEGY:
1. Scan the entire page to identify ALL product families (look for distinct product names and base codes)
2. For each family, extract its name, base code, construction details, and applications
3. Match each table to its corresponding family based on article number prefixes
4. Extract each table row as an individual product with full article number
5. Use pre-extracted table data when available for accuracy

📤 OUTPUT: Return ONLY valid JSON (no markdown, no explanations):

{{
    "category": "category name or null",
    "chapter": "chapter reference from header (e.g. 'KAPITEL 1:1 HÖGTRYCKSSLANG' or '1:1' or null)",
    "families": [
        {{
            "family_code": "base code without size suffix",
            "name": "product line name",
            "subtitle": "subtitle if present or null",
            "description": "additional description or null",
            "construction_details": {{
                // ⚠️ CRITICAL: Preserve original text exactly as written - DO NOT translate!
                // Use original field names: "Innertub", "Yttertub", "Armering", "Säkerhetsfaktor", 
                // "Temperatur", "Utförande", "Hylsa", "Produktgrupp", etc.
                // Keep values in Swedish: "Orange hölje, ej ledande", "Ett flätat aramidinlägg (Kevlar®)", etc.
                // Only convert obvious numbers/temperatures to structured format when needed
                // Include whatever fields exist, omit what doesn't
            }},
            "applications": "usage/application text or null",
            "products": [
                {{
                    "product_code": "complete article number",
                    "configuration_type": "STANDARD|REEL|SPECIAL|etc",
                    "configuration_name": "descriptive name or null",
                    "specifications": {{
                        // "id_mm", "id_tum", "yd_mm", 
                        // "working_pressure_mpa", "bend_radius_mm", "weight_kg_per_m"
                    }},
                    "bounding_box": [x1, y1, x2, y2]  // 🎯 ONLY the specific table ROW containing this product, NOT the whole construction section!
                }}
            ]
        }}
    ]
}}

💡 Be intelligent: Count how many distinct product sections exist on the page. Each section with its own name, code, konstruktion, and table is a separate family.'''
        
        response = self.call_ollama_vlm(image, prompt)
        
        if not response or 'message' not in response:
            print("No response from VLM")
            return None, None, []
        
        try:
            # Extract JSON from the response
            content = response['message']['content']
            
            # Try to find JSON object
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Extract hierarchical structure
                category = data.get('category', 'Unknown')
                chapter = data.get('chapter')
                families = data.get('families', [])
                
                return category, chapter, families
            else:
                print("No JSON found in VLM response")
                return None, None, []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from VLM response: {e}")
            print(f"Response content: {content}")
            return None, None, []
    
    def draw_bounding_boxes(self, image, products, output_path, pdf_page_size=None):
        """
        Draw bounding boxes on the image for visualization.
        
        Args:
            image: PIL Image object
            products: List of product dictionaries with bounding_box data
            output_path: Path to save the annotated image
            pdf_page_size: Tuple of (width, height) of PDF page in points for scaling
        """
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Calculate scale factor if PDF page size is provided
        scale_factor = 1.0
        if pdf_page_size:
            # Scale from PDF points to image pixels
            pdf_width, pdf_height = pdf_page_size
            img_width, img_height = image.size
            
            # Use the actual scaling factor based on how the image was rendered
            scale_x = img_width / pdf_width
            scale_y = img_height / pdf_height
            
            print(f"🔍 Scaling factors: X={scale_x:.2f}, Y={scale_y:.2f}")
        
        # Try to load a smaller font for cleaner labels
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 12)  # Reduced from 20 to 12
        except:
            font = None
        
        for i, product in enumerate(products):
            if 'bounding_box' in product and product['bounding_box']:
                bbox = product['bounding_box']
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    
                    # Scale coordinates if PDF page size is provided
                    if pdf_page_size:
                        x1 *= scale_x
                        y1 *= scale_y
                        x2 *= scale_x
                        y2 *= scale_y
                    
                    # Draw red bounding box with thinner lines
                    draw.rectangle([x1, y1, x2, y2], outline="red", width=2)  # Reduced from 5 to 2
                    
                    # Add product code label with background
                    product_code = product.get('product_code', f'Product {i+1}')
                    
                    # Calculate text size and position
                    if font:
                        bbox_text = draw.textbbox((0, 0), product_code, font=font)
                        text_width = bbox_text[2] - bbox_text[0]
                        text_height = bbox_text[3] - bbox_text[1]
                    else:
                        text_width = len(product_code) * 10
                        text_height = 15
                    
                    # Position label above the box, or inside if no space above
                    label_y = max(5, y1 - text_height - 5)
                    label_x = x1
                    
                    # Draw label background with thinner border
                    draw.rectangle([label_x-1, label_y-1, label_x + text_width + 1, label_y + text_height + 1], 
                                 fill="white", outline="red", width=1)  # Reduced from 2 to 1
                    
                    # Draw label text
                    if font:
                        draw.text((label_x, label_y), product_code, fill="red", font=font)
                    else:
                        draw.text((label_x, label_y), product_code, fill="red")
                    
                    print(f"📍 Drew box for {product_code}: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
        
        img_copy.save(output_path)
        print(f"🖼️  Bounding box visualization saved: {output_path}")
    
    def load_table_data(self, page_number):
        """
        Load previously extracted table data for a page.
        
        Args:
            page_number: PDF page number
            
        Returns:
            List of table data dictionaries, or None if not found
        """
        # Look for table JSON files for this page
        pattern = f"page_{page_number:03d}_table_*.json"
        table_files = list(self.tables_dir.glob(pattern))
        
        if not table_files:
            print(f"ℹ️  No pre-extracted table data found for page {page_number}")
            return None
        
        tables_data = []
        for table_file in sorted(table_files):
            try:
                with open(table_file, 'r', encoding='utf-8') as f:
                    table_data = json.load(f)
                    tables_data.append(table_data)
                    print(f"✓ Loaded table data: {table_file.name}")
            except Exception as e:
                print(f"⚠️  Error loading {table_file.name}: {e}")
        
        return tables_data if tables_data else None

    def extract_products_from_table_data(self, table_data, page_number):
        """
        Extract basic product information from table data when VLM fails.
        
        Args:
            table_data: List of table data dictionaries
            page_number: Page number for reference
            
        Returns:
            List of product dictionaries
        """
        print("🔧 Extracting products from table data...")
        products = []
        
        for table in table_data:
            try:
                table_bbox = table.get('table_bbox')
                content = table.get('content', [])
                
                if not content or len(content) < 2:  # Need at least header + 1 data row
                    continue
                    
                # First row is usually headers
                headers = content[0]
                data_rows = content[1:]
                
                for row_idx, row in enumerate(data_rows):
                    if not row or len(row) == 0:
                        continue
                        
                    # First cell often contains product code
                    first_cell = str(row[0]).strip()
                    if not first_cell or len(first_cell) < 3:
                        continue
                        
                    # Simple heuristic: if first cell looks like a product code
                    if any(char.isdigit() for char in first_cell) and any(char.isalpha() for char in first_cell):
                        # Build specifications from remaining cells using headers as keys
                        specs = {}
                        for col_idx, cell_value in enumerate(row[1:], 1):
                            if col_idx < len(headers):
                                header_name = str(headers[col_idx]).strip()
                                cell_text = str(cell_value).strip()
                                if cell_text and header_name:
                                    specs[header_name] = cell_text
                            else:
                                specs[f'col_{col_idx}'] = str(cell_value).strip()
                        
                        product = {
                            'product_code': first_cell,
                            'configuration_type': 'STANDARD',
                            'specifications': specs,
                            'table_bbox': table_bbox  # Use table bbox since we don't have row-specific
                        }
                        products.append(product)
                        
            except Exception as e:
                print(f"⚠️  Error processing table: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"✓ Extracted {len(products)} products from table data")
        return products

    def parse_tables_to_products(self, table_data):
        """
        Convert raw table JSON (from detect_tables) into product dicts.

        We preserve the raw cell text as-is (no language or number conversions).

        Args:
            table_data: list of table JSON dicts loaded from files

        Returns:
            List of product dicts with keys: product_code, specifications (dict), source_table
        """
        products = []

        for table in table_data:
            content = table.get('content', [])
            if not content or len(content) < 2:
                continue

            header = content[0]
            # Normalize header strings (keep original text)
            for row in content[1:]:
                # skip rows that are shorter/longer than header by padding
                specs = {}
                for i, col_name in enumerate(header):
                    try:
                        cell = row[i]
                    except IndexError:
                        cell = ""
                    specs[col_name] = cell

                # Assume first column is article number / product code
                product_code = row[0] if len(row) > 0 else None
                
                # Calculate individual row bounding box from table bbox
                row_bbox = None
                table_bbox = table.get('table_bbox')
                if table_bbox and len(table_bbox) == 4:
                    table_x1, table_y1, table_x2, table_y2 = table_bbox
                    
                    # Calculate based on data rows only (exclude header)
                    data_rows = content[1:]  # Skip header row
                    num_data_rows = len(data_rows)
                    
                    if num_data_rows > 0:
                        # Divide table height equally among data rows only
                        # Assume header takes approximately the same height as one data row
                        total_table_rows = len(content)  # header + data rows
                        single_row_height = (table_y2 - table_y1) / total_table_rows
                        
                        # Find the current row's position in the data rows
                        data_row_index = data_rows.index(row)  # Position within data rows only
                        
                        # Calculate row bounds - data area starts after header row
                        data_area_start_y = table_y1 + single_row_height  # Skip header row
                        row_start_y = data_area_start_y + (data_row_index * single_row_height)
                        row_end_y = data_area_start_y + ((data_row_index + 1) * single_row_height)
                        
                        # Apply small vertical adjustment to better align with actual table rows
                        # This compensates for any systematic offset in table detection
                        vertical_offset = single_row_height * 0.15  # 15% of row height adjustment
                        row_start_y += vertical_offset
                        row_end_y += vertical_offset
                        
                        row_bbox = [table_x1, row_start_y, table_x2, row_end_y]

                products.append({
                    'product_code': product_code,
                    'specifications': specs,
                    'source_table': table.get('table_id'),
                    'source_table_file': table.get('table_filename') if table.get('table_filename') else None,
                    'table_bbox': table.get('table_bbox'),
                    'bounding_box': row_bbox  # Individual row bounding box
                })

        return products

    def _get_nearest_heading_for_table(self, pdf_path, page_number, table_bbox):
        """
        Try to find a text block (heading) immediately above the table bbox on the PDF page.
        Returns the text string if found, otherwise None.
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)
            blocks = page.get_text("dict").get('blocks', [])

            # Convert table_bbox to fitz.Rect if list
            if isinstance(table_bbox, list):
                tbl_rect = fitz.Rect(table_bbox)
            else:
                tbl_rect = fitz.Rect(table_bbox)

            candidates = []
            for block in blocks:
                if 'lines' not in block:
                    continue
                bbox = block.get('bbox')
                if not bbox:
                    continue
                blk_rect = fitz.Rect(bbox)

                # Candidate must be vertically above the table and horizontally overlapping
                if blk_rect.y1 <= tbl_rect.y0 and blk_rect.x0 < tbl_rect.x1 and blk_rect.x1 > tbl_rect.x0:
                    # distance from table
                    dist = tbl_rect.y0 - blk_rect.y1
                    text = "".join(span.get('text', '') for line in block.get('lines', []) for span in line.get('spans', []))
                    candidates.append((dist, text.strip()))

            doc.close()

            if not candidates:
                return None

            # Pick the nearest candidate (smallest distance)
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1] if candidates[0][1] else None

        except Exception:
            return None

    def save_to_database(self, category_name, family_data, products_list, page_number, chapter=None):
        """
        Save extracted products to hierarchical SQLite database.
        
        Args:
            category_name: Category name (e.g., "HÖGTRYCKSSLANG")
            family_data: Dictionary with family-level information
            products_list: List of product dictionaries with specifications
            page_number: PDF page number
            chapter: Chapter reference (e.g., "KAPITEL 1:1 HÖGTRYCKSSLANG")
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Insert or get category with chapter information
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, chapter, page_number)
                VALUES (?, ?, ?)
            ''', (category_name, chapter, page_number))
            
            # Get category by name and chapter (or just name if chapter is None)
            if chapter:
                cursor.execute('SELECT id FROM categories WHERE name = ? AND chapter = ?', (category_name, chapter))
            else:
                cursor.execute('SELECT id FROM categories WHERE name = ? AND chapter IS NULL', (category_name,))
            category_id = cursor.fetchone()[0]
            
            # 2. Insert or update product family
            family_code = family_data.get('family_code')
            family_name = family_data.get('name')
            
            cursor.execute('''
                INSERT OR REPLACE INTO product_families 
                (category_id, family_code, name, subtitle, description, 
                 construction_details, applications, page_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                category_id,
                family_code,
                family_name,
                family_data.get('subtitle'),
                family_data.get('description'),
                json.dumps(family_data.get('construction_details', {}), ensure_ascii=False),
                family_data.get('applications'),
                page_number
            ))
            
            cursor.execute('''
                SELECT id FROM product_families 
                WHERE family_code = ? AND name = ?
            ''', (family_code, family_name))
            family_id = cursor.fetchone()[0]
            
            print(f"✓ Saved family: {family_code} - {family_name}")
            
            # 3. Insert individual products
            for product in products_list:
                product_code = product.get('product_code')
                
                # Extract variant suffix (e.g., "-04" from "1059-01-04")
                if family_code and product_code and product_code.startswith(family_code):
                    variant_suffix = product_code[len(family_code):]
                else:
                    variant_suffix = None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO products
                    (family_id, product_code, variant_suffix, configuration_type,
                     configuration_name, specifications, bounding_box, page_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    family_id,
                    product_code,
                    variant_suffix,
                    product.get('configuration_type', 'STANDARD'),
                    product.get('configuration_name'),
                    json.dumps(product.get('specifications', {}), ensure_ascii=False),
                    json.dumps(product.get('bounding_box', [])) if product.get('bounding_box') else None,
                    page_number
                ))
                
                print(f"  ✓ Saved product: {product_code}")
            
            conn.commit()
            print(f"✅ Saved {len(products_list)} products to database")
            
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def extract_from_pdf_page(self, pdf_path, page_number):
        """
        Main method to extract products from a PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to process
            
        Returns:
            Tuple of (category, families_list)
        """
        print(f"\n{'='*60}")
        print(f"Processing PDF: {pdf_path}, Page: {page_number}")
        print(f"{'='*60}")
        
        # Get PDF page dimensions for coordinate scaling
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number - 1)  # Convert to 0-based
        pdf_page_size = (page.rect.width, page.rect.height)
        doc.close()
        print(f"📄 PDF page size: {pdf_page_size[0]:.1f} x {pdf_page_size[1]:.1f} points")
        
        # Try to load pre-extracted table data
        table_data = self.load_table_data(page_number)
        
        # If we have pre-extracted table data, prefer constructing products
        # directly from the table JSON (preserve original text) and derive
        # families from product codes / nearby headings. Otherwise render
        # the image and use VLM to extract hierarchical data.
        if table_data:
            products_from_tables = self.parse_tables_to_products(table_data)
            category = None
            families_list = []

            for prod in products_from_tables:
                pcode = prod.get('product_code')
                assigned = False

                for family in families_list:
                    fc = family.get('family_code')
                    if fc and pcode and pcode.startswith(fc):
                        family.setdefault('products', []).append({
                            'product_code': pcode,
                            'specifications': prod.get('specifications', {}),
                            'bounding_box': prod.get('table_bbox')
                        })
                        assigned = True
                        break

                if not assigned:
                    if pcode and '-' in pcode:
                        family_code = '-'.join(pcode.split('-')[:-1])
                    else:
                        family_code = pcode

                    heading = None
                    table_bbox = prod.get('table_bbox')
                    if table_bbox:
                        heading = self._get_nearest_heading_for_table(pdf_path, page_number, table_bbox)

                    new_family = {
                        'family_code': family_code,
                        'name': heading or family_code,
                        'subtitle': None,
                        'description': None,
                        'construction_details': {},
                        'applications': None,
                        'products': [{
                            'product_code': pcode,
                            'specifications': prod.get('specifications', {}),
                            'bounding_box': prod.get('table_bbox')
                        }]
                    }
                    families_list.append(new_family)

            # Render page to image for visualization
            image = self.render_pdf_page(pdf_path, page_number, dpi=300)
            print(f"✓ Rendered page {page_number} to image ({image.size[0]}x{image.size[1]})")

        else:
            # Render PDF page with conservative DPI for reliable VLM processing
            image = self.render_pdf_page(pdf_path, page_number, dpi=200)  # Reduced to 200 DPI
            print(f"✓ Rendered page {page_number} to image ({image.size[0]}x{image.size[1]})")
            
            # Always check and optimize image size for VLM reliability
            max_pixels = 1500000  # 1.5 megapixels - even more conservative for qwen3-vl:latest
            current_pixels = image.size[0] * image.size[1]
            
            if current_pixels > max_pixels:
                print(f"⚠️  Image ({image.size[0]}x{image.size[1]}) = {current_pixels:,} pixels, optimizing for VLM...")
                # Calculate resize factor to stay under max_pixels
                resize_factor = (max_pixels / current_pixels) ** 0.5
                new_width = int(image.size[0] * resize_factor)
                new_height = int(image.size[1] * resize_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
                print(f"✓ Optimized to {image.size[0]}x{image.size[1]} = {image.size[0] * image.size[1]:,} pixels")
            
            # Extract products using VLM with hierarchical structure
            category, chapter, families_list = self.extract_products_from_image(
                image, page_number, table_data
            )

        # If extraction failed, try lower resolution as final fallback
        if not category or not families_list:
            print("⚠️  Initial extraction failed, trying lower resolution...")
            image = self.render_pdf_page(pdf_path, page_number, dpi=150)
            print(f"✓ Rendered page {page_number} to lower-res image ({image.size[0]}x{image.size[1]})")

            # Also optimize the lower resolution image for VLM
            max_pixels = 1500000  # 1.5 megapixels
            current_pixels = image.size[0] * image.size[1]
            
            if current_pixels > max_pixels:
                print(f"⚠️  Lower-res image ({image.size[0]}x{image.size[1]}) = {current_pixels:,} pixels, optimizing further...")
                # Calculate resize factor to stay under max_pixels
                resize_factor = (max_pixels / current_pixels) ** 0.5
                new_width = int(image.size[0] * resize_factor)
                new_height = int(image.size[1] * resize_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
                print(f"✓ Final optimization to {image.size[0]}x{image.size[1]} = {image.size[0] * image.size[1]:,} pixels")

            category, chapter, families_list = self.extract_products_from_image(
                image, page_number, table_data
            )
            
        # If VLM completely failed but we have table data, create basic family structure
        if (not category or not families_list) and table_data:
            print("⚠️  VLM extraction failed, falling back to table-only extraction...")
            
            # Extract products directly from table data
            table_products = self.extract_products_from_table_data(table_data, page_number)
            
            if table_products:
                category = "EXTRACTED_FROM_TABLES"
                families_list = [{
                    'family_code': 'TABLE_PRODUCTS',
                    'name': 'Products from Table Data',
                    'subtitle': None,
                    'description': 'Products extracted directly from table data when VLM failed',
                    'construction_details': {},
                    'applications': None,
                    'products': table_products
                }]
                print(f"✓ Created fallback family with {len(table_products)} products")
            else:
                print("❌ Table-only extraction also failed")
                families_list = []

        # Enhance VLM results with accurate table row coordinates from table detection
        if table_data and families_list:
            products_from_tables = self.parse_tables_to_products(table_data)
            
            if products_from_tables:
                print("🔗 Merging VLM product families with accurate table coordinates...")
                
                for family in families_list:
                    family_code = family.get('family_code')
                    vlm_products = family.get('products', [])
                    enhanced_products = []
                    
                    # For each VLM product, try to find matching table product with accurate coordinates
                    for vlm_product in vlm_products:
                        vlm_pcode = vlm_product.get('product_code')
                        
                        # Find matching table product
                        table_match = None
                        for table_product in products_from_tables:
                            table_pcode = table_product.get('product_code')
                            if table_pcode == vlm_pcode:
                                table_match = table_product
                                break
                        
                        if table_match:
                            # Use VLM data but with accurate table row coordinates
                            enhanced_product = {
                                'product_code': vlm_pcode,
                                'configuration_type': vlm_product.get('configuration_type', 'STANDARD'),
                                'configuration_name': vlm_product.get('configuration_name'),
                                'specifications': table_match.get('specifications', {}),  # Use table specs
                                'bounding_box': table_match.get('bounding_box')  # Use calculated row coordinates
                            }
                            enhanced_products.append(enhanced_product)
                        else:
                            # Keep VLM product as-is if no table match
                            enhanced_products.append(vlm_product)
                    
                    # Add any table products not found in VLM
                    for table_product in products_from_tables:
                        table_pcode = table_product.get('product_code')
                        if family_code and table_pcode and table_pcode.startswith(family_code):
                            # Check if already added
                            found = any(p.get('product_code') == table_pcode for p in enhanced_products)
                            if not found:
                                enhanced_products.append({
                                    'product_code': table_pcode,
                                    'configuration_type': 'STANDARD',
                                    'configuration_name': None,
                                    'specifications': table_product.get('specifications', {}),
                                    'bounding_box': table_product.get('bounding_box')  # Use calculated row coordinates
                                })
                    
                    family['products'] = enhanced_products
                    print(f"✓ Enhanced family {family_code} with {len(enhanced_products)} products using table coordinates")

        if not category or not families_list:
            print("❌ No products extracted")
            return None, None, []
        
        print(f"\n✓ Extracted hierarchical data:")
        print(f"  Category: {category}")
        print(f"  Families found: {len(families_list)}")
        
        for i, family in enumerate(families_list, 1):
            print(f"    {i}. {family.get('family_code')} - {family.get('name')}")
            print(f"       Products: {len(family.get('products', []))} items")

        # Skip bounding box visualization - removed per user request
        print("📊 Bounding box visualization disabled")

        # Save each family to database
        for family in families_list:
            family_data = {
                'family_code': family.get('family_code'),
                'name': family.get('name'),
                'subtitle': family.get('subtitle'),
                'description': family.get('description'),
                'construction_details': family.get('construction_details', {}),
                'applications': family.get('applications')
            }
            products_list = family.get('products', [])
            self.save_to_database(category, family_data, products_list, page_number, chapter)

        # Print extracted data summary
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Category: {category}")
        print(f"\nProduct Families: {len(families_list)}")
        
        total_products = 0
        for i, family in enumerate(families_list, 1):
            print(f"\n{i}. Family Code: {family.get('family_code')}")
            print(f"   Family Name: {family.get('name')}")
            products = family.get('products', [])
            print(f"   Products: {len(products)}")
            for j, p in enumerate(products, 1):
                print(f"     {j}. {p.get('product_code')} - {p.get('configuration_type', 'STANDARD')}")
            total_products += len(products)
        
        print(f"\nTotal products extracted: {total_products}")

        return category, chapter, families_list


def main():
    parser = argparse.ArgumentParser(description="Extract product data from PDF using VLM")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--page", type=int, default=31, help="Page number to process")
    parser.add_argument("--ollama-url", default="http://localhost:11434", 
                       help="Ollama API URL")
    parser.add_argument("--model", default="qwen3-vl:235b-instruct-cloud", help="VLM model name")
    
    args = parser.parse_args()
    
    # Check if PDF exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Initialize extractor
    try:
        extractor = ProductExtractor(
            ollama_url=args.ollama_url,
            model_name=args.model
        )
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    try:
        # Extract products with hierarchical structure
        category, chapter, families = extractor.extract_from_pdf_page(
            pdf_path, args.page
        )

        if families:
            total_products = sum(len(f.get('products', [])) for f in families)
            print(f"\n✅ Successfully extracted {len(families)} families with {total_products} total products from page {args.page}")
            print(f"📊 Data saved to database: {extractor.db_manager.db_path}")
            print(f"📊 Visualization saved to: data/tables/")
        else:
            print(f"⚠️  No products extracted from page {args.page}")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()