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
        self.db_path = Path("data/products.db")
        self.output_dir = Path("output")
        self.tables_dir = Path("data/tables")
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Verify database is initialized
        if not self._init_database():
            raise RuntimeError("Database not properly initialized")
    
    def _init_database(self):
        """Initialize SQLite database - uses external schema.sql file."""
        # Database should be initialized with schema.sql before running this script
        # This method just verifies the tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verify required tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('categories', 'product_families', 'products')
        """)
        tables = cursor.fetchall()
        
        if len(tables) < 3:
            print("⚠️  Warning: Database schema not initialized!")
            print("Please run: sqlite3 data/products.db < Layer_1/schema.sql")
            conn.close()
            return False
        
        conn.close()
        return True
    
    def render_pdf_page(self, pdf_path, page_number):
        """
        Render a PDF page to an image.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-based)
            
        Returns:
            PIL Image object
        """
        doc = fitz.open(pdf_path)
        
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
        
        page = doc.load_page(page_number - 1)  # Convert to 0-based
        
        # Render at high DPI for better text recognition
        zoom = 300 / 72.0  # 300 DPI
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
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
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

Image dimensions: {image.size[0]}x{image.size[1]} pixels
{table_context}

📋 TASK: Extract product data in a 3-level hierarchy

🔍 WHAT TO LOOK FOR:

**Level 1 - CATEGORY** (broad product group):
Find the main category this page belongs to. Look for large headings or chapter references.
Common categories: HÖGTRYCKSSLANG, OLJESLANG, KEMIKALIESLANGAR, etc.

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
    "chapter": "chapter reference or null",
    "families": [
        {{
            "family_code": "base code without size suffix",
            "name": "product line name",
            "subtitle": "subtitle if present or null",
            "description": "additional description or null",
            "construction_details": {{
                // Extract whatever construction info is present, common fields:
                // "inner_tube", "outer_cover", "reinforcement", "safety_factor",
                // "temperature": {{"min": num, "max": num, "unit": "°C"}},
                // "standards": [], "marking", "hylsa", "produktgrupp", etc.
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
                    "bounding_box": [x1, y1, x2, y2]
                }}
            ]
        }}
    ]
}}

💡 Be intelligent: Count how many distinct product sections exist on the page. Each section with its own name, code, konstruktion, and table is a separate family.'''
        
        response = self.call_ollama_vlm(image, prompt)
        
        if not response or 'message' not in response:
            print("No response from VLM")
            return None, []
        
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
                families = data.get('families', [])
                
                return category, families
            else:
                print("No JSON found in VLM response")
                return None, []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from VLM response: {e}")
            print(f"Response content: {content}")
            return None, []
    
    def draw_bounding_boxes(self, image, products, output_path):
        """
        Draw bounding boxes on the image for visualization.
        
        Args:
            image: PIL Image object
            products: List of product dictionaries with bounding_box data
            output_path: Path to save the annotated image
        """
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        for i, product in enumerate(products):
            if 'bounding_box' in product and product['bounding_box']:
                bbox = product['bounding_box']
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    # Draw red bounding box
                    draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                    
                    # Add product code label
                    product_code = product.get('product_code', f'Product {i+1}')
                    draw.text((x1, y1-20), product_code, fill="red")
        
        img_copy.save(output_path)
        print(f"Bounding box visualization saved: {output_path}")
    
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

    def save_to_database(self, category_name, family_data, products_list, page_number):
        """
        Save extracted products to hierarchical SQLite database.
        
        Args:
            category_name: Category name (e.g., "HÖGTRYCKSSLANG")
            family_data: Dictionary with family-level information
            products_list: List of product dictionaries with specifications
            page_number: PDF page number
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Insert or get category
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, page_number)
                VALUES (?, ?)
            ''', (category_name, page_number))
            
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
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
        
        # Try to load pre-extracted table data
        table_data = self.load_table_data(page_number)
        
        # Render PDF page to image
        image = self.render_pdf_page(pdf_path, page_number)
        print(f"✓ Rendered page {page_number} to image ({image.size[0]}x{image.size[1]})")
        
        # Extract products using VLM with hierarchical structure
        category, families_list = self.extract_products_from_image(
            image, page_number, table_data
        )
        
        if not category or not families_list:
            print("❌ No products extracted")
            return None, []
        
        print(f"\n✓ Extracted hierarchical data:")
        print(f"  Category: {category}")
        print(f"  Families found: {len(families_list)}")
        
        for i, family in enumerate(families_list, 1):
            print(f"    {i}. {family.get('family_code')} - {family.get('name')}")
            print(f"       Products: {len(family.get('products', []))} items")

        # Collect all products for visualization
        all_products = []
        for family in families_list:
            all_products.extend(family.get('products', []))
        
        # Save visualization with bounding boxes
        pdf_name = Path(pdf_path).stem
        viz_path = self.output_dir / f"{pdf_name}_page_{page_number:03d}_products.png"
        self.draw_bounding_boxes(image, all_products, viz_path)

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
            self.save_to_database(category, family_data, products_list, page_number)

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

        return category, families_list


def main():
    parser = argparse.ArgumentParser(description="Extract product data from PDF using VLM")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--page", type=int, default=31, help="Page number to process")
    parser.add_argument("--ollama-url", default="http://localhost:11434", 
                       help="Ollama API URL")
    parser.add_argument("--model", default="qwen3-vl:235b-cloud", help="VLM model name")
    
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
        category, families = extractor.extract_from_pdf_page(
            pdf_path, args.page
        )

        if families:
            total_products = sum(len(f.get('products', [])) for f in families)
            print(f"\n✅ Successfully extracted {len(families)} families with {total_products} total products from page {args.page}")
            print(f"📊 Data saved to: {extractor.db_path}")
        else:
            print(f"⚠️  No products extracted from page {args.page}")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()