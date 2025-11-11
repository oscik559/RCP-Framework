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
        self.db_manager = DatabaseManager()
        
        # Create directories
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with full schema
        self.db_manager.init_database()
        
        # Enhanced Local VLM initialization - using qwen3-vl:32b locally
        self.local_vlm = OllamaVLM("qwen3-vl:32b")
        
        # VLM configuration - local only
        self.vlm_endpoints = [
            {"url": "http://localhost:11434/api/chat", "model": "qwen3-vl:32b"}
        ]
    
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
        """Merge a group of tables into a single table."""
        # Calculate merged bounding box
        min_x = min(table['bbox'][0] for table in table_group)
        min_y = min(table['bbox'][1] for table in table_group)
        max_x = max(table['bbox'][2] for table in table_group)
        max_y = max(table['bbox'][3] for table in table_group)
        
        # Combine all rows from all tables
        merged_rows = []
        for table in table_group:
            if 'rows' in table and table['rows']:
                merged_rows.extend(table['rows'])
        
        return {
            'bbox': (min_x, min_y, max_x, max_y),
            'rows': merged_rows,
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
        """Detect and extract tables from a specific page."""
        pdf_name = Path(pdf_path).stem
        
        # Open PDF
        pdf_doc = fitz.open(pdf_path)
        if page_number > pdf_doc.page_count:
            print(f"Page {page_number} not found in PDF")
            return []
        
        page = pdf_doc[page_number - 1]
        
        # Load corresponding PNG image
        png_path = self.pages_dir / f"{pdf_name}_page_{page_number:03d}.png"
        if not png_path.exists():
            print(f"PNG file not found: {png_path}")
            return []
        
        png_img = Image.open(png_path)
        
        # Get exclusion regions
        exclusion_regions = self.get_exclusion_regions(pdf_name, page_number)
        
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
            
            return final_tables
        
        return detected_tables
    
    def save_table_data(self, table_data, pdf_name, page_number, table_number):
        """Save table data to JSON file."""
        # Determine which data to save (prefer VLM if available)
        rows_to_save = table_data.get('vlm_rows', table_data.get('rows', []))
        
        if not rows_to_save:
            print(f"No data to save for table {table_number}")
            return None
        
        # Calculate table dimensions
        num_rows = len(rows_to_save)
        num_cols = max(len(row) for row in rows_to_save) if rows_to_save else 0
        
        # Create output filename
        output_file = self.tables_dir / f"{pdf_name}_page_{page_number:03d}_table_{table_number}_{num_rows}x{num_cols}.json"
        
        # Prepare data structure
        save_data = {
            'page_number': page_number,
            'table_number': table_number,
            'bbox': table_data['bbox'],
            'dimensions': f"{num_rows}x{num_cols}",
            'extraction_method': 'vlm' if table_data.get('vlm_rows') else 'pymupdf',
            'rows': rows_to_save,
            'merged_from': table_data.get('merged_from', 1)
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved table {table_number} to {output_file}")
        return output_file
    
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
        print(f"\n=== Processing page {page_num} ===")
        
        # Detect tables (now optimized to only send cropped table images to VLM)
        tables = detector.detect_tables_in_page(pdf_path, page_num, use_vlm=not args.no_vlm)
        
        if not tables:
            print(f"No tables found on page {page_num}")
            continue
        
        print(f"Found {len(tables)} tables on page {page_num}")
        total_tables += len(tables)
        
        # Save table data
        for table in tables:
            table_num = table.get('final_index', table.get('table_index', 1))
            saved_file = detector.save_table_data(table, Path(pdf_path).stem, page_num, table_num)
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