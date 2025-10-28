#!/usr/bin/env python3
"""
Product Data Extractor using Ollama VLM

Extracts product information from PDF pages using a Vision Language Model
and stores the results in a SQLite database.
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
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with product tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT UNIQUE,
                name TEXT,
                category TEXT,
                page_number INTEGER,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create specifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS specs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                spec_key TEXT,
                spec_value TEXT,
                unit TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
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
    
    def extract_products_from_image(self, image, strict_table=False):
        """
        Extract product information from an image using VLM.

        Args:
            image: PIL Image object
            strict_table: if True, use a stricter prompt that forces one product per table row

        Returns:
            List of extracted products with their information
        """
        if strict_table:
            # Stronger prompt to force extraction of every table row as an individual product
            prompt = f'''
            You are given an image of a product-specification page (dimensions: {image.size[0]}x{image.size[1]} pixels) that contains a table listing multiple product rows.

            Your task: Extract every table row as a separate product object. For each table row include the exact product code as printed (e.g., "1059-01-04"), the exact measurements from the row (ID mm, ID tum, YD mm, Arb.tr MPa, Böjradie mm, Vikt kg/m), and attach the page-level metadata (product name/category and construction text) to each product.

            CRITICAL - Bounding Box Requirements:
            - The image is {image.size[0]} pixels wide and {image.size[1]} pixels tall
            - For each product, provide a bounding_box that encompasses the ENTIRE product section including:
              * The product image (hose illustration on the left)
              * The construction details (Konstruktion section)
              * The specifications table row
              * Any usage/application text (Användning och egenskaper)
            - Bounding box format: [x1, y1, x2, y2] where:
              * x1, y1 = top-left corner coordinates
              * x2, y2 = bottom-right corner coordinates
              * All coordinates must be within 0-{image.size[0]} (width) and 0-{image.size[1]} (height)
            - Make bounding boxes generous - better to include too much than too little

            Requirements:
            - Return a JSON array where each element is an object with keys: product_code, name, category, specifications (with keys id_mm, id_tum, yd_mm, working_pressure_mpa, bend_radius_mm, weight_kg_per_m), construction (string), bounding_box (array of 4 numbers).
            - Do NOT include summary or explanatory text—only return valid JSON.
            - Ensure that table header rows are not returned as products; only return actual product rows with full codes (including trailing segments like "-04").
            - If a value is missing, set it to null.

            Example output:
            [
              {{"product_code":"1059-01-04", "name":"...", "category":"...", "specifications":{{"id_mm":6.5,...}}, "construction":"...", "bounding_box":[50, 100, 1200, 400]}},
              ...
            ]
            '''
        else:
            prompt = f'''
            Analyze this product specification page (dimensions: {image.size[0]}x{image.size[1]} pixels) and extract all product information.

            For each product, identify and extract:
            1. Product code (like 1105-43-04, 1105-43-06, etc.)
            2. Technical specifications from tables (ID mm, ID tum, YD mm, Arb.tr MPa, Böjradie mm, Vikt kg/m)
            3. Product name/category (like "KAPPAFLEX 2K PO")
            4. Construction details (Konstruktion section with materials, temperature, etc.)

            CRITICAL - Bounding Box Requirements:
            - The image is {image.size[0]} pixels wide and {image.size[1]} pixels tall
            - For each product, provide a bounding_box that encompasses the ENTIRE product section
            - Bounding box format: [x1, y1, x2, y2] where all coordinates are within image bounds
            - Make bounding boxes generous to include all related content

            Return the data as a JSON array where each product is an object with:
            {{
                "product_code": "string",
                "name": "string", 
                "category": "string",
                "specifications": {{
                    "id_mm": "number",
                    "id_tum": "string", 
                    "yd_mm": "number",
                    "working_pressure_mpa": "number",
                    "bend_radius_mm": "number",
                    "weight_kg_per_m": "number"
                }},
                "construction": "string (full construction text)",
                "bounding_box": [x1, y1, x2, y2] (coordinates within 0-{image.size[0]}, 0-{image.size[1]})
            }}

            Only return valid JSON, no other text.
            '''
        
        response = self.call_ollama_vlm(image, prompt)
        
        if not response or 'message' not in response:
            print("No response from VLM")
            return []
        
        try:
            # Extract JSON from the response
            content = response['message']['content']
            
            # Try to find JSON in the response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                # Try for single object
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                products = json.loads(json_str)
                
                # Ensure it's a list
                if isinstance(products, dict):
                    products = [products]
                
                return products
            else:
                print("No JSON found in VLM response")
                return []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from VLM response: {e}")
            print(f"Response content: {content}")
            return []
    
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
    
    def save_to_database(self, products, page_number):
        """
        Save extracted products to SQLite database.
        
        Args:
            products: List of product dictionaries
            page_number: PDF page number
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for product in products:
            try:
                # Insert product
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (product_code, name, category, page_number, raw_text)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    product.get('product_code'),
                    product.get('name'),
                    product.get('category'),
                    page_number,
                    product.get('construction', '')
                ))
                
                product_id = cursor.lastrowid
                
                # Insert specifications
                specs = product.get('specifications', {})
                for key, value in specs.items():
                    if value is not None:
                        cursor.execute('''
                            INSERT INTO specs (product_id, spec_key, spec_value, unit)
                            VALUES (?, ?, ?, ?)
                        ''', (product_id, key, str(value), ''))
                
                print(f"Saved product: {product.get('product_code', 'Unknown')}")
                
            except sqlite3.Error as e:
                print(f"Database error for product {product.get('product_code', 'Unknown')}: {e}")
        
        conn.commit()
        conn.close()
    
    def extract_from_pdf_page(self, pdf_path, page_number, strict_table=False):
        """
        Main method to extract products from a PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to process
            
        Returns:
            List of extracted products
        """
        print(f"Processing PDF: {pdf_path}, Page: {page_number}")
        
        # Render PDF page to image
        image = self.render_pdf_page(pdf_path, page_number)
        print(f"Rendered page {page_number} to image ({image.size[0]}x{image.size[1]})")
        # Extract products using VLM
        products = self.extract_products_from_image(image, strict_table=strict_table)
        print(f"Extracted {len(products)} products")

        if products:
            # Save visualization with bounding boxes
            pdf_name = Path(pdf_path).stem
            viz_path = self.output_dir / f"{pdf_name}_page_{page_number:03d}_boxes.png"
            self.draw_bounding_boxes(image, products, viz_path)

            # Save to database
            self.save_to_database(products, page_number)

            # Print extracted data
            print("\nExtracted Products:")
            print(json.dumps(products, indent=2, ensure_ascii=False))

        return products


def main():
    parser = argparse.ArgumentParser(description="Extract product data from PDF using VLM")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--page", type=int, default=31, help="Page number to process")
    parser.add_argument("--ollama-url", default="http://localhost:11434", 
                       help="Ollama API URL")
    parser.add_argument("--model", default="qwen3-vl:235b-cloud", help="VLM model name")
    parser.add_argument("--strict-table", action="store_true", help="Use strict table-row extraction prompt to force one product per table row")
    
    args = parser.parse_args()
    
    # Check if PDF exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Initialize extractor
    extractor = ProductExtractor(
        ollama_url=args.ollama_url,
        model_name=args.model
    )
    
    try:
        # Extract products (pass strict_table flag)
        products = extractor.extract_from_pdf_page(pdf_path, args.page, strict_table=args.strict_table)

        if products:
            print(f"\nSuccessfully extracted {len(products)} products from page {args.page}")
            print(f"Data saved to: {extractor.db_path}")
        else:
            print(f"No products extracted from page {args.page}")

    except Exception as e:
        print(f"Error during extraction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()