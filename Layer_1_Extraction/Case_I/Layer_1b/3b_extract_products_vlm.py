#!/usr/bin/env python3
"""
VLM-Enhanced Table Detection and Extraction

This script detects tables in PDF documents using PyMuPDF and enhances
content extraction using Vision Language Models (VLMs) for better accuracy.
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
import time
from typing import Optional, List, Dict, Any
sys.path.append(str(Path(__file__).parent.parent / "data" / "database"))
from db_utils import DatabaseManager


class OllamaVLM:
    """VLM implementation using local Ollama models."""

    def __init__(self, model_name: str = "llama3.2-vision:latest", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"
        
    def extract_table_data(self, table_image: Image.Image) -> Optional[List[List[str]]]:
        """
        Extract table data from a CROPPED table image (not full page).
        
        Args:
            table_image: PIL Image of the cropped table region only
            
        Returns:
            List of lists representing table rows and columns, or None if failed
        """
        try:
            # Convert PIL image to base64
            image_b64 = self._encode_image_to_base64(table_image)
            
            # Optimized prompt for cropped table images (Qwen3-VL optimized)
            prompt = (
                "Extract all text from this table image and return it as a JSON array. "
                "Each row should be an array of cell values. Include headers. "
                "Format: [[\"Header1\", \"Header2\"], [\"Cell1\", \"Cell2\"]]. "
                "IMPORTANT: Return ONLY the JSON array with no other text, explanations, or formatting. "
                "Start with [ and end with ]."
            )
            
            # Optimize parameters based on model type
            if "cloud" in self.model_name:
                # Cloud model settings
                options = {
                    "temperature": 0.0,
                    "num_predict": 1000
                }
            else:
                # Local model settings (more conservative for better reliability)
                options = {
                    "temperature": 0.0,
                    "num_predict": 1500,  # Increased for local models
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt,
                        "images": [image_b64]
                    }
                ],
                "stream": False,
                "options": options
            }
            
            print(f"🔍 Sending cropped table image ({table_image.size}) to {self.model_name}...")
            start_time = time.time()
            
            response = requests.post(self.api_url, json=payload, timeout=6000)
            response.raise_for_status()
            
            elapsed = time.time() - start_time
            result = response.json()
            
            # Extract response content from chat format
            content = result.get('message', {}).get('content', '')
            
            print(f"✅ VLM response received in {elapsed:.2f}s")
            print(f"📊 Response length: {len(content)} characters")
            
            # Parse JSON from response
            table_data = self._parse_json_from_response(content)
            
            if table_data:
                print(f"✅ Successfully extracted {len(table_data)} rows x {len(table_data[0]) if table_data else 0} columns")
                return table_data
            else:
                print("⚠️ Failed to parse table data from VLM response")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ VLM request timed out after 600s")
            return None
        except Exception as e:
            print(f"❌ VLM extraction failed: {e}")
            return None
    
    def _encode_image_to_base64(self, pil_image: Image.Image) -> str:
        """Convert PIL image to base64 string."""
        buffer = BytesIO()
        pil_image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _parse_json_from_response(self, content: str) -> Optional[List[List[str]]]:
        """Extract and parse JSON array from VLM response (improved for multiple models)."""
        try:
            # Method 1: Find JSON array in response (standard approach)
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate it's a list of lists
                if isinstance(parsed, list) and all(isinstance(row, list) for row in parsed):
                    return parsed
                    
        except json.JSONDecodeError as e:
            print(f"⚠️ Primary JSON parsing failed: {e}")
            
            # Method 2: Try to find JSON in code blocks (some models wrap in ```json)
            try:
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end != -1:
                        json_str = content[start:end].strip()
                        parsed = json.loads(json_str)
                        if isinstance(parsed, list) and all(isinstance(row, list) for row in parsed):
                            print("✅ Recovered JSON from code block")
                            return parsed
                            
                # Method 3: Try to clean up common response patterns
                cleaned = content.strip()
                # Remove common prefixes
                prefixes_to_remove = [
                    "Here is the extracted table data:",
                    "The table contains:",
                    "Extracted data:",
                    "Table data:",
                    "Here's the table:",
                ]
                
                for prefix in prefixes_to_remove:
                    if cleaned.startswith(prefix):
                        cleaned = cleaned[len(prefix):].strip()
                
                # Try parsing the cleaned content
                json_start = cleaned.find('[')
                json_end = cleaned.rfind(']') + 1
                if json_start != -1 and json_end != 0:
                    json_str = cleaned[json_start:json_end]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list) and all(isinstance(row, list) for row in parsed):
                        print("✅ Recovered JSON after cleaning")
                        return parsed
                        
            except Exception as e2:
                print(f"⚠️ Secondary JSON parsing also failed: {e2}")
        
        print(f"❌ Could not parse JSON from response: {content[:200]}...")
        return None




class VLMTableDetector:
    def __init__(self):
        """Initialize the VLM Table Detector."""
        # Get script directory for relative paths
        self.script_dir = Path(__file__).parent
        self.pages_dir = self.script_dir / "data/png_pages"
        self.tables_dir = self.script_dir / "data/tables"
        self.products_dir = self.script_dir / "data/products"
        self.family_dir = self.script_dir / "data/family"
        self.db_manager = DatabaseManager()
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        self.products_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        self.db_manager.init_database()
        
        # Enhanced Local VLM initialization - using qwen3-vl:235b-instruct-cloud
        self.local_vlm = OllamaVLM("qwen3-vl:235b-instruct-cloud")
        
        # VLM configuration - using cloud model
        self.vlm_endpoints = [
            {"url": "http://localhost:11434/api/chat", "model": "qwen3-vl:235b-instruct-cloud"}
        ]
    
    def extract_page_number_from_footer(self, page, footer_region):
        """Extract the actual page number from the footer region of the PDF."""
        if not footer_region:
            return None
        
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
            return page_numbers[-1]
        
        return None
    
    def get_exclusion_regions(self, pdf_name, page_number):
        """Get header/footer regions from database to exclude from table detection."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT header_x0, header_y0, header_x1, header_y1,
                   footer_x0, footer_y0, footer_x1, footer_y1
            FROM page_regions 
            WHERE pdf_name = ? AND page_number = ?
        ''', (pdf_name, page_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            header_bbox = None
            footer_bbox = None
            
            # Check if header coordinates are valid
            if all(coord is not None for coord in result[0:4]):
                header_bbox = [result[0], result[1], result[2], result[3]]
                
            # Check if footer coordinates are valid  
            if all(coord is not None for coord in result[4:8]):
                footer_bbox = [result[4], result[5], result[6], result[7]]
                
            return {
                'header': header_bbox,
                'footer': footer_bbox
            }
        return {'header': None, 'footer': None}
    
    def bbox_intersects(self, bbox1, bbox2, tolerance=10):
        """Check if two bounding boxes intersect with tolerance."""
        x1, y1, x2, y2 = bbox1
        x3, y3, x4, y4 = bbox2
        
        # Expand bbox2 by tolerance
        x3 -= tolerance
        y3 -= tolerance
        x4 += tolerance
        y4 += tolerance
        
        return not (x2 < x3 or x1 > x4 or y2 < y3 or y1 > y4)
    
    def separate_columns(self, tables, page_width):
        """Separate tables into left and right columns."""
        mid_point = page_width / 2
        left_tables = []
        right_tables = []
        
        for table in tables:
            bbox = table['bbox']
            table_center_x = (bbox[0] + bbox[2]) / 2
            
            if table_center_x < mid_point:
                left_tables.append(table)
            else:
                right_tables.append(table)
        
        # Sort by vertical position (top to bottom)
        left_tables.sort(key=lambda t: t['bbox'][1])
        right_tables.sort(key=lambda t: t['bbox'][1])
        
        return left_tables, right_tables
    
    def merge_column_tables(self, column_tables, max_gap=50, width_similarity=0.8):
        """Merge vertically adjacent tables in a column."""
        if len(column_tables) <= 1:
            return column_tables
        
        merged = []
        current_group = [column_tables[0]]
        
        for i in range(1, len(column_tables)):
            current_table = column_tables[i]
            prev_table = current_group[-1]
            
            # Calculate gap and width similarity
            gap = current_table['bbox'][1] - prev_table['bbox'][3]
            prev_width = prev_table['bbox'][2] - prev_table['bbox'][0]
            curr_width = current_table['bbox'][2] - current_table['bbox'][0]
            width_ratio = min(prev_width, curr_width) / max(prev_width, curr_width)
            
            # Check if tables should be merged
            if gap <= max_gap and width_ratio >= width_similarity:
                current_group.append(current_table)
            else:
                # Merge current group and start new group
                if len(current_group) > 1:
                    merged_table = self.merge_table_group(current_group)
                    merged.append(merged_table)
                else:
                    merged.extend(current_group)
                current_group = [current_table]
        
        # Handle last group
        if len(current_group) > 1:
            merged_table = self.merge_table_group(current_group)
            merged.append(merged_table)
        else:
            merged.extend(current_group)
        
        return merged
    
    def merge_table_group(self, table_group):
        """Merge a group of tables into a single table, preserving both PyMuPDF and VLM data."""
        # Calculate merged bounding box
        min_x = min(table['bbox'][0] for table in table_group)
        min_y = min(table['bbox'][1] for table in table_group)
        max_x = max(table['bbox'][2] for table in table_group)
        max_y = max(table['bbox'][3] for table in table_group)
        
        # Combine all rows from all tables (PyMuPDF data)
        merged_rows = []
        for table in table_group:
            if 'rows' in table and table['rows']:
                merged_rows.extend(table['rows'])
        
        # Combine all VLM rows from all tables
        merged_vlm_rows = []
        for table in table_group:
            if 'vlm_rows' in table and table['vlm_rows']:
                merged_vlm_rows.extend(table['vlm_rows'])
        
        return {
            'bbox': (min_x, min_y, max_x, max_y),
            'rows': merged_rows,
            'vlm_rows': merged_vlm_rows,
            'merged_from': len(table_group)
        }
    
    def extract_table_with_vlm(self, table_image, table_bbox):
        """
        Extract table content using Vision Language Model.
        ONLY processes the cropped table image, not the full page.
        
        Args:
            table_image: PIL Image of the CROPPED table region only
            table_bbox: Bounding box coordinates (for debugging/logging)
        """
        print(f"🎯 VLM processing cropped table: {table_image.size} pixels")
        print(f"📦 Table bbox: {[int(x) for x in table_bbox]}")
        
        # Try local VLM first (recommended - uses optimized cropped processing)
        if self.local_vlm:
            try:
                local_result = self.local_vlm.extract_table_data(table_image)
                if local_result:
                    print("✅ Local VLM extraction successful")
                    return local_result
                else:
                    print("⚠️ Local VLM extraction returned no data")
            except Exception as e:
                print(f"❌ Local VLM extraction failed: {e}")
        
        # Fallback to remote VLM endpoints (also processes only the cropped image)
        print("Trying remote VLM endpoints as fallback...")
        
        # Convert PIL image to base64 (CROPPED image only, not full page)
        buffered = BytesIO()
        table_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        print(f"📄 Base64 image size: {len(img_base64)} characters (cropped table only)")
        
        prompt = """Extract all visible text from this table image. 
        Return as JSON array where each row is an array of cell values.
        Include headers. Example: [["Header1", "Header2"], ["Cell1", "Cell2"]].
        Return only the JSON array, no additional text."""
        
        # Try each VLM endpoint with the cropped image
        for endpoint in self.vlm_endpoints:
            try:
                print(f"🔄 Trying {endpoint['model']} with cropped table image...")
                extracted_data = self.query_vlm(endpoint, prompt, img_base64)
                if extracted_data:
                    print(f"✅ Success with {endpoint['model']}")
                    return extracted_data
            except Exception as e:
                print(f"❌ VLM endpoint {endpoint['model']} failed: {e}")
                continue
        
        return None
    
    def query_vlm(self, endpoint, prompt, img_base64):
        """Query a specific VLM endpoint."""
        if "localhost:11434" in endpoint["url"]:  # Ollama
            payload = {
                "model": endpoint["model"],
                "prompt": prompt,
                "images": [img_base64],
                "stream": False
            }
        else:  # OpenAI-compatible
            payload = {
                "model": endpoint["model"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 2000
            }
        
        response = requests.post(endpoint["url"], json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if "localhost:11434" in endpoint["url"]:
                content = data.get("response", "")
            else:
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Try to parse JSON from response
            try:
                # Extract JSON from response
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                if json_start != -1 and json_end != 0:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return None
    
    def extract_table_image(self, pdf_doc, page_num, table_bbox, png_img):
        """
        Extract ONLY the table region from PNG image, not the full page.
        
        Args:
            pdf_doc: PyMuPDF document
            page_num: Page number 
            table_bbox: Table bounding box in PDF coordinates
            png_img: Full page PNG image
            
        Returns:
            PIL Image of CROPPED table region only
        """
        # Convert PDF coordinates to PNG coordinates
        page = pdf_doc[page_num - 1]
        page_rect = page.rect
        
        # Calculate scaling factors
        png_width, png_height = png_img.size
        pdf_width = page_rect.width
        pdf_height = page_rect.height
        
        scale_x = png_width / pdf_width
        scale_y = png_height / pdf_height
        
        # Convert coordinates
        x1 = int(table_bbox[0] * scale_x)
        y1 = int(table_bbox[1] * scale_y)
        x2 = int(table_bbox[2] * scale_x)
        y2 = int(table_bbox[3] * scale_y)
        
        # Add padding but ensure we stay within image bounds
        padding = 10
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(png_width, x2 + padding)
        y2 = min(png_height, y2 + padding)
        
        # Crop ONLY the table region (full table, no small crop)
        cropped_table = png_img.crop((x1, y1, x2, y2))
        
        print(f"📏 Cropped table image: {cropped_table.size} (from full page {png_img.size})")
        print(f"🎯 VLM processes full cropped table region")
        
        return cropped_table
    
    def detect_tables_in_page(self, pdf_path, page_number, use_vlm=True):
        """Detect and extract tables from a specific page.
        
        Returns:
            tuple: (tables_list, footer_page_number) where footer_page_number is the actual page number from the document footer
        """
        pdf_name = Path(pdf_path).stem
        
        # Open PDF
        pdf_doc = fitz.open(pdf_path)
        if page_number > pdf_doc.page_count:
            print(f"Page {page_number} not found in PDF")
            return [], None
        
        page = pdf_doc[page_number - 1]
        
        # Load corresponding PNG image
        png_path = self.pages_dir / f"{pdf_name}_page_{page_number:03d}.png"
        if not png_path.exists():
            print(f"PNG file not found: {png_path}")
            return [], None
        
        png_img = Image.open(png_path)
        
        # Get exclusion regions
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
        # Extract actual page number from footer
        footer_page_number = None
        if exclusion_regions.get('footer'):
            footer_page_number = self.extract_page_number_from_footer(page, exclusion_regions['footer'])
            if footer_page_number:
                print(f"📄 Footer page number: {footer_page_number} (PDF page index: {page_number})")
            else:
                print(f"⚠️  Could not extract page number from footer, using PDF index: {page_number}")
                footer_page_number = page_number
        else:
            print(f"⚠️  No footer region found, using PDF index: {page_number}")
            footer_page_number = page_number
        
        # Detect tables using PyMuPDF
        tables = page.find_tables()
        
        detected_tables = []
        for i, table in enumerate(tables):
            table_bbox = table.bbox
            
            # Check if table intersects with exclusion regions
            skip_table = False
            for region_name, region_bbox in exclusion_regions.items():
                if region_bbox and self.bbox_intersects(table_bbox, region_bbox):
                    print(f"Table {i+1} intersects with {region_name}, skipping")
                    skip_table = True
                    break
            
            if skip_table:
                continue
            
            # Extract table content using PyMuPDF
            try:
                table_data = table.extract()
                
                # Extract ONLY the table region (not full page) - no small crop
                table_image = self.extract_table_image(pdf_doc, page_number, table_bbox, png_img)
                
                # Try VLM extraction if enabled (processes only the cropped table)
                vlm_data = None
                if use_vlm:
                    try:
                        vlm_data = self.extract_table_with_vlm(table_image, table_bbox)
                            
                    except Exception as e:
                        print(f"❌ VLM extraction failed for table {i+1}: {e}")
                else:
                    print(f"⏭️ Skipping VLM extraction for table {i+1} (--no-vlm flag set)")
                
                detected_tables.append({
                    'bbox': table_bbox,
                    'rows': table_data if table_data else [],
                    'vlm_rows': vlm_data if vlm_data else [],
                    'table_index': i
                })
                
            except Exception as e:
                print(f"Error extracting table {i+1}: {e}")
                continue
        
        # Get page width before closing document
        page_width = page.rect.width
        pdf_doc.close()
        
        # Apply column-aware merging
        if detected_tables:
            left_tables, right_tables = self.separate_columns(detected_tables, page_width)
            
            # Merge tables in each column
            merged_left = self.merge_column_tables(left_tables)
            merged_right = self.merge_column_tables(right_tables)
            
            # Combine and renumber
            final_tables = merged_left + merged_right
            for i, table in enumerate(final_tables):
                table['final_index'] = i + 1
            
            return final_tables, footer_page_number
        
        return detected_tables, footer_page_number
    
    def get_family_for_table(self, footer_page_number, table_number):
        """
        Get the family_id for a table based on the family info JSON file.
        Uses the table_id from the family JSON to match with the current table.
        
        Args:
            footer_page_number: The actual page number from the document footer (stored in database)
            table_number: The table index on the page
            
        Returns:
            int: Database ID of the family, or None if not found
        """
        # Load family info JSON for this page (uses footer page number for filename)
        family_json_path = self.family_dir / f"page_{footer_page_number:03d}_family_info.json"
        
        if not family_json_path.exists():
            print(f"⚠️  No family info JSON found: {family_json_path}")
            return None
        
        try:
            with open(family_json_path, 'r', encoding='utf-8') as f:
                family_data = json.load(f)
            
            # Find the family with matching table_id
            for family in family_data.get('families', []):
                if family.get('table_id') == table_number:
                    family_code = family.get('family_code')
                    family_name = family.get('name')
                    
                    # Get the database ID for this family
                    # IMPORTANT: Query by page_number which stores the FOOTER page number
                    conn = self.db_manager.get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT id FROM product_families 
                        WHERE family_code = ? AND page_number = ?
                    ''', (family_code, footer_page_number))
                    
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        family_db_id = result[0]
                        print(f"📎 Linking table {table_number} to family: {family_code} - {family_name} (DB ID: {family_db_id}, Page: {footer_page_number})")
                        return family_db_id
                    else:
                        print(f"⚠️  Family {family_code} not found in database for footer page {footer_page_number}")
                        return None
            
            print(f"⚠️  No family found for table {table_number} on footer page {footer_page_number}")
            return None
            
        except Exception as e:
            print(f"❌ Error reading family info JSON: {e}")
            return None
    
    def parse_specifications_from_table(self, rows, family_id):
        """
        Parse table rows into product specifications.
        Returns list of product dictionaries ready for database insertion.
        Handles Unicode properly to avoid control characters.
        """
        if not rows or len(rows) < 2:
            return []
        
        # First row is typically headers
        headers = [str(cell).strip() for cell in rows[0]]
        
        products = []
        
        # Process each data row
        for row_idx, row in enumerate(rows[1:], start=1):
            if not row or all(not cell or str(cell).strip() == '' for cell in row):
                continue  # Skip empty rows
            
            # Build specifications dictionary from row data
            specs = {}
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers) and headers[col_idx]:
                    header = headers[col_idx]
                    # Clean the value - remove control characters and ensure proper Unicode
                    value = str(cell).strip() if cell else ""
                    
                    # Remove common control characters that PyMuPDF might insert
                    value = value.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                    value = value.replace('\x03', '').replace('\x04', '').replace('\x05', '')
                    value = value.replace('\x15', '').replace('\x12', '').replace('\u0010', '')
                    
                    if value:  # Only add non-empty values
                        specs[header] = value
            
            if not specs:
                continue
            
            # Try to extract product code (usually first column)
            product_code = str(row[0]).strip() if row else ""
            
            # Clean product code from control characters
            product_code = product_code.replace('\x00', '').replace('\x01', '').replace('\x02', '')
            product_code = product_code.replace('\x03', '').replace('\x04', '').replace('\x05', '')
            product_code = product_code.replace('\x15', '').replace('\x12', '').replace('\u0010', '')
            
            if not product_code:
                print(f"⚠️  Row {row_idx} has no product code, skipping")
                continue
            
            # Create product dictionary
            product = {
                'family_id': family_id,
                'product_code': product_code,
                'specifications': json.dumps(specs, ensure_ascii=False),
                'configuration_type': 'STANDARD',
                'page_number': None  # Will be set by caller
            }
            
            products.append(product)
        
        return products
    
    def save_products_to_database(self, products, page_number):
        """Save extracted products to the database."""
        if not products:
            return 0
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        inserted_count = 0
        
        for product in products:
            try:
                # Set page number
                product['page_number'] = page_number
                
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (family_id, product_code, configuration_type, specifications, page_number)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    product['family_id'],
                    product['product_code'],
                    product.get('configuration_type', 'STANDARD'),
                    product['specifications'],
                    product['page_number']
                ))
                
                product_db_id = cursor.lastrowid
                print(f"      ✅ Inserted product {product['product_code']} (ID: {product_db_id})")
                inserted_count += 1
                
            except Exception as e:
                print(f"      ⚠️  Error inserting product {product.get('product_code')}: {e}")
        
        conn.commit()
        conn.close()
        
        return inserted_count
    
    def save_table_data(self, table_data, pdf_name, pdf_page_number, footer_page_number, table_number):
        """Save table data to JSON file and extract products to database.
        
        Args:
            table_data: Dictionary containing table extraction data
            pdf_name: Name of the PDF file
            pdf_page_number: Sequential page index in the PDF (for filenames)
            footer_page_number: Actual page number from document footer (for database queries)
            table_number: Table index on the page
        """
        # Determine which data to save (prefer VLM if available)
        vlm_rows = table_data.get('vlm_rows', [])
        pymupdf_rows = table_data.get('rows', [])
        
        # Use VLM data if it has content, otherwise fall back to PyMuPDF
        if vlm_rows:
            rows_to_save = vlm_rows
            extraction_method = 'vlm'
        else:
            rows_to_save = pymupdf_rows
            extraction_method = 'pymupdf'
        
        if not rows_to_save:
            print(f"No data to save for table {table_number}")
            return None
        
        # Calculate table dimensions
        num_rows = len(rows_to_save)
        num_cols = max(len(row) for row in rows_to_save) if rows_to_save else 0
        
        # Create output filename for tables directory (uses PDF page index for file naming)
        table_output_file = self.tables_dir / f"{pdf_name}_page_{pdf_page_number:03d}_table_{table_number}_{num_rows}x{num_cols}.json"
        
        # Prepare table data structure (store both page numbers for reference)
        table_save_data = {
            'pdf_page_number': pdf_page_number,
            'footer_page_number': footer_page_number,
            'table_number': table_number,
            'bbox': table_data['bbox'],
            'dimensions': f"{num_rows}x{num_cols}",
            'extraction_method': extraction_method,
            'rows': rows_to_save,
            'merged_from': table_data.get('merged_from', 1)
        }
        
        # Save to tables directory
        with open(table_output_file, 'w', encoding='utf-8') as f:
            json.dump(table_save_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved table {table_number} to {table_output_file}")
        
        # === Extract products to database ===
        print(f"🔄 Extracting products from table {table_number}...")
        
        # Get family for this table using the footer page number (which matches database page_number)
        family_id = self.get_family_for_table(footer_page_number, table_number)
        
        if family_id:
            # Parse products from table (using VLM data)
            products = self.parse_specifications_from_table(rows_to_save, family_id)
            
            if products:
                print(f"📦 Found {len(products)} products in table")
                
                # Save products JSON to products directory (use footer page number for consistency)
                products_output_file = self.products_dir / f"{pdf_name}_page_{footer_page_number:03d}_table_{table_number}_products.json"
                
                products_save_data = {
                    'pdf_page_number': pdf_page_number,
                    'footer_page_number': footer_page_number,
                    'table_number': table_number,
                    'family_id': family_id,
                    'extraction_method': extraction_method,
                    'product_count': len(products),
                    'products': products
                }
                
                with open(products_output_file, 'w', encoding='utf-8') as f:
                    json.dump(products_save_data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Saved products JSON to {products_output_file}")
                
                # Save to database (use footer page number which matches database page_number column)
                inserted = self.save_products_to_database(products, footer_page_number)
                print(f"✅ Inserted {inserted}/{len(products)} products to database")
            else:
                print(f"⚠️  No valid products extracted from table")
        else:
            print(f"⚠️  Could not determine family for table, skipping product extraction")
        
        return table_output_file
    
    def create_visualization(self, pdf_path, page_number, tables):
        """Create annotated PNG with table bounding boxes."""
        pdf_name = Path(pdf_path).stem
        png_path = self.pages_dir / f"{pdf_name}_page_{page_number:03d}.png"
        
        if not png_path.exists():
            return None
        
        # Load and copy image
        img = Image.open(png_path).copy()
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Convert PDF coordinates to PNG coordinates
        pdf_doc = fitz.open(pdf_path)
        page = pdf_doc[page_number - 1]
        page_rect = page.rect
        pdf_doc.close()
        
        png_width, png_height = img.size
        scale_x = png_width / page_rect.width
        scale_y = png_height / page_rect.height
        
        # Colors for different tables
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, table in enumerate(tables):
            color = colors[i % len(colors)]
            bbox = table['bbox']
            
            # Convert coordinates
            x1 = int(bbox[0] * scale_x)
            y1 = int(bbox[1] * scale_y)
            x2 = int(bbox[2] * scale_x)
            y2 = int(bbox[3] * scale_y)
            
            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw table number
            table_num = table.get('final_index', i + 1)
            text = f"Table {table_num}"
            if table.get('merged_from', 1) > 1:
                text += f" (merged from {table['merged_from']})"
            
            draw.text((x1, y1 - 30), text, fill=color, font=font)
        
        # Save annotated image
        output_path = self.tables_dir / f"{pdf_name}_page_{page_number:03d}_tables_annotated.png"
        img.save(output_path)
        print(f"Saved annotated image to {output_path}")
        
        return output_path

def main():
    parser = argparse.ArgumentParser(description='VLM-Enhanced Table Detection and Extraction - OPTIMIZED FOR CROPPED TABLES ONLY')
    parser.add_argument('--page', type=int, help='Specific page number to process')
    parser.add_argument('--pdf', type=str, default='Press_Couplings.pdf', help='PDF filename')
    parser.add_argument('--start', type=int, default=5, help='Start page (default: 5)')
    parser.add_argument('--end', type=int, default=26, help='End page (default: 26)')
    parser.add_argument('--no-vlm', action='store_true', help='Disable VLM extraction, use only PyMuPDF')
    
    args = parser.parse_args()
    
    detector = VLMTableDetector()
    
    # Determine PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        # Try looking in current directory
        pdf_path = Path(".") / args.pdf
        if not pdf_path.exists():
            print(f"PDF file not found: {args.pdf}")
            return
    
    # Process pages
    if args.page:
        pages = [args.page]
    else:
        pages = range(args.start, args.end + 1)
    
    total_tables = 0
    successful_extractions = 0
    
    for page_num in pages:
        print(f"\n=== Processing PDF page {page_num} ===")
        
        # Detect tables (returns tuple: tables_list, footer_page_number)
        result = detector.detect_tables_in_page(pdf_path, page_num, use_vlm=not args.no_vlm)
        
        if not result or not result[0]:
            print(f"No tables found on page {page_num}")
            continue
        
        tables, footer_page_num = result
        print(f"Found {len(tables)} tables on PDF page {page_num} (Footer page: {footer_page_num})")
        total_tables += len(tables)
        
        # Save table data
        for table in tables:
            table_num = table.get('final_index', table.get('table_index', 1))
            saved_file = detector.save_table_data(table, Path(pdf_path).stem, page_num, footer_page_num, table_num)
            if saved_file:
                successful_extractions += 1
        
        # Create visualization
        detector.create_visualization(pdf_path, page_num, tables)
    
    print(f"\n=== Summary ===")
    print(f"Total tables detected: {total_tables}")
    print(f"Successful extractions: {successful_extractions}")
    print(f"Success rate: {successful_extractions/total_tables*100:.1f}%" if total_tables > 0 else "No tables processed")

if __name__ == "__main__":
    main()