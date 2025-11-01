#!/usr/bin/env python3
"""
Product Data Extractor using Ollama VLM
=======================================

A comprehensive PDF product extraction system that combines Vision Language Models (VLM)
with traditional text processing to extract structured product information from Swedish
industrial hose/hydraulic catalogs.

ARCHITECTURE OVERVIEW:
---------------------
This script implements a hierarchical data extraction pipeline:

1. **Text-First Approach**: Prioritizes searchable PDF text extraction for better accuracy
2. **VLM Fallback**: Uses Vision Language Models when text extraction is insufficient
3. **Table Integration**: Leverages pre-extracted table data for precise specifications
4. **Hierarchical Storage**: Organizes data in 3-level database structure

DATA HIERARCHY:
--------------
- **Categories** (Level 1): Broad product groups (e.g., HÖGTRYCKSSLANG, OLJESLANG)
- **Product Families** (Level 2): Product lines sharing construction characteristics
- **Products** (Level 3): Individual SKUs with complete specifications

PROCESSING MODES:
----------------
- **Individual Pages**: Process single PDF pages or page-specific PDF files
- **Batch Processing**: Process entire PDFs or directories of page files
- **Hybrid Extraction**: Combines text analysis with image processing

INTEGRATION POINTS:
------------------
- Requires: detect_tables.py output (JSON table data)
- Outputs: SQLite database with hierarchical product structure
- Uses: Ollama VLM model (qwen3-vl:235b-instruct-cloud)

USAGE EXAMPLES:
--------------
Single page: python 4_extract_product.py --page 31
Batch mode:  python 4_extract_product.py --all-pages data/pdf_pages/
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
from PIL import Image
from db_utils import DatabaseManager


class ProductExtractor:
    """
    Advanced product data extraction system using VLM and text processing.
    
    This class orchestrates the extraction of hierarchical product information from
    Swedish industrial catalog PDFs. It implements a multi-modal approach combining:
    
    - Text-first extraction from searchable PDFs
    - Vision Language Model processing for complex layouts
    - Table data integration for precise specifications
    - Hierarchical database storage (categories → families → products)
    
    KEY FEATURES:
    - Intelligent PDF analysis (text vs image processing)
    - Multi-page batch processing capabilities
    - Robust error handling and fallback mechanisms
    - Swedish text preservation (no translation)
    - Precise bounding box calculations for UI integration
    
    PROCESSING PIPELINE:
    1. PDF searchability analysis
    2. Text extraction with layout preservation
    3. VLM processing when needed
    4. Table data correlation
    5. Hierarchical data structuring
    6. SQLite database storage
    """
    
    def __init__(self, ollama_url="http://localhost:11434", model_name="qwen3-vl:235b-instruct-cloud"):
        """
        Initialize the ProductExtractor with VLM configuration.
        
        Args:
            ollama_url (str): Base URL for Ollama API server
            model_name (str): VLM model identifier (default: qwen3-vl:235b-instruct-cloud)
            
        Raises:
            RuntimeError: If database initialization fails
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
    
    def is_page_searchable(self, pdf_path, page_number, min_chars=100):
        """
        Determine if a PDF page contains sufficient searchable text for text-first extraction.
        
        This method is crucial for choosing the optimal extraction strategy. Pages with
        sufficient text content can be processed more accurately using text-based analysis,
        while image-heavy or scanned pages require VLM processing.
        
        Args:
            pdf_path (str|Path): Path to PDF file (full PDF or individual page)
            page_number (int): Page number to analyze (1-based indexing)
            min_chars (int, optional): Minimum character threshold for searchability. 
                                     Defaults to 100 characters.
            
        Returns:
            bool: True if page contains >= min_chars of extractable text,
                  False if page requires image-based processing
                  
        Note:
            For single-page PDF files, always analyzes page 0 regardless of page_number.
            Handles both multi-page PDFs and individual page files transparently.
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)  # Convert to 0-based
            text = page.get_text("text").strip()
            doc.close()
            
            # Check if we have meaningful text content
            return len(text) >= min_chars and not text.isspace()
        except Exception as e:
            print(f"⚠️  Error checking page searchability: {e}")
            return False
    
    def extract_structured_text(self, pdf_path, page_number):
        """
        Extract structured text with complete layout preservation from PDF page.
        
        Uses PyMuPDF's dictionary format to maintain precise positioning information
        for each text element. This data is essential for understanding document
        structure and correlating text with table positions.
        
        Args:
            pdf_path (str|Path): Path to PDF file (full PDF or individual page)
            page_number (int): Page number to extract (1-based indexing)
            
        Returns:
            dict: Hierarchical text structure containing:
                - 'blocks': List of text blocks with positioning
                - Each block contains 'lines' with font and style information  
                - Each line contains 'spans' with individual text fragments
                - Bounding boxes for all elements (x0, y0, x1, y1)
                - Font metadata: size, family, flags (bold, italic)
                
        Note:
            Returns None on extraction failure. For single-page PDFs,
            automatically uses page 0 regardless of page_number parameter.
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)  # Convert to 0-based
            text_dict = page.get_text("dict")
            doc.close()
            return text_dict
        except Exception as e:
            print(f"❌ Error extracting structured text: {e}")
            return None
    
    def build_text_prompt(self, text_dict, page_number, table_data=None):
        """
        Build a text-based prompt from structured PDF text data.
        
        Args:
            text_dict: Structured text dictionary from PyMuPDF
            page_number: Page number being processed
            table_data: Pre-extracted table data (optional)
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Build context from pre-extracted table data if available
        table_context = ""
        if table_data:
            table_context = "\n\n📊 PRE-EXTRACTED TABLE DATA:\n"
            for i, table in enumerate(table_data, 1):
                table_context += f"\nTable {i} ({table.get('rows')}x{table.get('columns')}):\n"
                table_context += json.dumps(table.get('content', []), indent=2, ensure_ascii=False) + "\n"
        
        # Extract and organize text blocks by position
        blocks = []
        if text_dict and 'blocks' in text_dict:
            for block in text_dict['blocks']:
                if 'lines' not in block:
                    continue
                
                bbox = block.get('bbox', [0, 0, 0, 0])
                block_text = ""
                font_info = []
                
                for line in block['lines']:
                    line_text = ""
                    for span in line.get('spans', []):
                        span_text = span.get('text', '').strip()
                        if span_text:
                            line_text += span_text + " "
                            # Collect font information for styling cues
                            font_info.append({
                                'text': span_text,
                                'font': span.get('font', ''),
                                'size': span.get('size', 0),
                                'flags': span.get('flags', 0)  # Bold, italic, etc.
                            })
                    if line_text.strip():
                        block_text += line_text.strip() + "\n"
                
                if block_text.strip():
                    blocks.append({
                        'text': block_text.strip(),
                        'bbox': bbox,
                        'fonts': font_info
                    })
        
        # Sort blocks by position (top-to-bottom, left-to-right)
        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))  # Sort by y, then x
        
        # Build structured text representation
        structured_text = ""
        for i, block in enumerate(blocks):
            bbox = block['bbox']
            text = block['text']
            
            # Identify potential headings based on font size/style
            fonts = block['fonts']
            avg_font_size = sum(f['size'] for f in fonts) / len(fonts) if fonts else 0
            has_bold = any(f['flags'] & 2**4 for f in fonts)  # Bold flag
            
            # Format block with position and styling hints
            block_type = "HEADING" if (avg_font_size > 12 or has_bold) and len(text) < 100 else "TEXT"
            structured_text += f"\n[{block_type}] Position: ({bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f})\n"
            structured_text += f"{text}\n"
        
        prompt = f'''You are analyzing a Swedish industrial hose/hydraulic product catalog page using structured text content.

🚨 CRITICAL LANGUAGE REQUIREMENT: 
- Extract ALL text EXACTLY as written - DO NOT translate anything!
- Only extract, never translate or modify the original text

Page number: {page_number}
{table_context}

📋 STRUCTURED TEXT CONTENT:
{structured_text}

📋 TASK: Extract product data in a 3-level hierarchy

🔍 WHAT TO LOOK FOR:

**Level 1 - CATEGORY & CHAPTER** (broad product group):
Find the main category this page belongs to. Look for large headings or chapter references.
Common categories: HÖGTRYCKSSLANG, OLJESLANG, KEMIKALIESLANGAR, etc.

Look for CHAPTER information in the header region:
- Look for "KAPITEL" followed by a number and title
- Or chapter references like "1:1", "2:1", etc. with descriptive text

**Level 2 - PRODUCT FAMILIES** (product lines with shared characteristics):
⚠️ IMPORTANT: A page may contain MULTIPLE product families (1, 2, or more).
Each family typically has:
- A prominent product name/model (often in HEADING blocks)
- A base article/product code that products share (the prefix before size variants)
- Its own "Konstruktion" section describing materials, temperature range, standards  
- Its own "Användning och egenskaper" (usage/application) text

The family code is the common prefix in article numbers (e.g., if you see "1059-01-04", "1059-01-06", the family is "1059-01").

**Level 3 - INDIVIDUAL PRODUCTS** (specific SKUs):
Each family has multiple products from its specifications table. Use the pre-extracted table data for accurate product specifications.

🎯 EXTRACTION STRATEGY:
1. Scan all text blocks to identify product families (look for product names and base codes)
2. For each family, extract its name, base code, construction details, and applications
3. Match table data to families based on article number prefixes
4. Extract each table row as an individual product with full article number
5. Use text block positions to determine bounding boxes for products

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
                // Use original field names and keep values in Swedish
            }},
            "applications": "usage/application text or null",
            "products": [
                {{
                    "product_code": "complete article number",
                    "configuration_type": "STANDARD|REEL|SPECIAL|etc",
                    "configuration_name": "descriptive name or null",
                    "specifications": {{
                        // Use table data for accurate specifications
                    }},
                    "bounding_box": [x1, y1, x2, y2]  // Text block position containing this product info
                }}
            ]
        }}
    ]
}}

💡 Use the structured text blocks and their positions to understand the page layout and extract accurate information.'''
        
        return prompt
    
    def call_ollama_text(self, prompt):
        """
        Execute text-only processing through Ollama LLM API.
        
        Handles structured text extraction without image processing, ideal for
        searchable PDFs where text content is sufficient for accurate extraction.
        This approach is faster and more reliable than VLM for text-rich pages.
        
        Args:
            prompt (str): Formatted prompt containing structured text data and
                         extraction instructions
            
        Returns:
            dict: JSON response from Ollama API containing:
                - 'message': LLM response with extracted product data
                - 'model': Model identifier used for processing
                - Error information if request fails
                
        Note:
            Uses the same model as VLM processing but without image input.
            Automatically handles API timeouts and connection errors.
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        }
        
        try:
            print("🤖 Calling Ollama API with text prompt...")
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=300  # 5 minutes
            )
            response.raise_for_status()
            print("✓ Received response from text-based LLM")
            return response.json()
        except requests.exceptions.Timeout:
            print("❌ Ollama API timeout (5 minutes)")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling Ollama API: {e}")
            return None

    def call_ollama_vlm(self, image, prompt):
        """
        Execute Vision Language Model processing through Ollama API.
        
        Processes PDF page images using multimodal VLM for complex layouts where
        text extraction is insufficient. Handles product identification, hierarchy
        understanding, and bounding box detection from visual elements.
        
        Args:
            image (PIL.Image): Rendered PDF page image for visual processing
            prompt (str): Detailed prompt with extraction instructions and context
            
        Returns:
            dict: JSON response from Ollama VLM API containing:
                - 'message': Structured product data in JSON format
                - 'model': VLM model identifier  
                - Processing metadata and timing information
                - Error details if processing fails
                
        Note:
            Automatically converts image to base64 for API transmission.
            Uses extended timeout (10 minutes) for complex visual processing.
            Model: qwen3-vl:235b-instruct-cloud optimized for technical documents.
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
    

    def extract_products_from_text(self, text_dict, page_number, table_data=None):
        """
        Extract product information from structured text using LLM.
        
        Args:
            text_dict: Structured text dictionary from PyMuPDF
            page_number: Page number being processed
            table_data: Pre-extracted table data (optional)
            
        Returns:
            Tuple of (category_name, chapter, families_list)
        """
        prompt = self.build_text_prompt(text_dict, page_number, table_data)
        response = self.call_ollama_text(prompt)
        
        if not response or 'message' not in response:
            print("No response from text-based LLM")
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
                print("No JSON found in text-based LLM response")
                return None, None, []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from text-based LLM response: {e}")
            print(f"Response content: {content}")
            return None, None, []

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
        Can work with either full PDF + page number or individual PDF page file.
        
        Args:
            pdf_path: Path to PDF file (full PDF or individual page PDF)
            page_number: Page number to process (ignored if pdf_path is single page)
            
        Returns:
            Tuple of (category, families_list)
        """
        print(f"\n{'='*60}")
        print(f"Processing PDF: {pdf_path}, Page: {page_number}")
        print(f"{'='*60}")
        
        # Get PDF page dimensions for coordinate scaling
        doc = fitz.open(pdf_path)
        
        # Check if this is a single-page PDF (individual page file) or multi-page PDF
        if len(doc) == 1:
            # Single page PDF - use page 0
            page = doc.load_page(0)
            actual_page_num = page_number  # Keep original page number for table data lookup
            print(f"📄 Processing individual PDF page file")
        else:
            # Multi-page PDF - use specified page number
            if page_number < 1 or page_number > len(doc):
                doc.close()
                raise ValueError(f"Page {page_number} not found. PDF has {len(doc)} pages.")
            page = doc.load_page(page_number - 1)  # Convert to 0-based
            actual_page_num = page_number
        
        pdf_page_size = (page.rect.width, page.rect.height)
        doc.close()
        print(f"📄 PDF page size: {pdf_page_size[0]:.1f} x {pdf_page_size[1]:.1f} points")
        
        # Try to load pre-extracted table data using the actual page number
        table_data = self.load_table_data(actual_page_num)
        
        # EXTRACTION STRATEGY DECISION:
        # When pre-extracted table data exists, we can skip VLM processing and construct
        # product families directly from table structure. This preserves original text
        # and is more accurate than re-processing through vision models.
        if table_data:
            print("📊 Using table-first extraction approach")
            products_from_tables = self.parse_tables_to_products(table_data)
            category = None
            families_list = []

            # GROUP PRODUCTS INTO FAMILIES BASED ON CODE PATTERNS
            # Products with shared prefixes (e.g., "1059-01-04", "1059-01-06") belong to same family
            for prod in products_from_tables:
                pcode = prod.get('product_code')
                assigned = False

                # Try to assign product to existing family
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

                # Create new family if product doesn't match existing ones
                if not assigned:
                    # Extract family code by removing variant suffix (last segment after hyphen)
                    if pcode and '-' in pcode:
                        family_code = '-'.join(pcode.split('-')[:-1])  # e.g., "1059-01-04" → "1059-01"
                    else:
                        family_code = pcode

                    # Try to find descriptive heading near this table for family name
                    heading = None
                    table_bbox = prod.get('table_bbox')
                    if table_bbox:
                        # Use actual page number for table heading lookup
                        table_page_num = 1 if len(fitz.open(pdf_path)) == 1 else actual_page_num
                        heading = self._get_nearest_heading_for_table(pdf_path, table_page_num, table_bbox)

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

            # Render page to image for visualization - use correct page number for single-page PDFs
            render_page_num = 1 if len(fitz.open(pdf_path)) == 1 else page_number
            image = self.render_pdf_page(pdf_path, render_page_num, dpi=300)
            print(f"✓ Rendered page {actual_page_num} to image ({image.size[0]}x{image.size[1]})")

        else:
            # NO PRE-EXTRACTED TABLES: Use intelligent text-first → VLM fallback strategy
            # This approach maximizes accuracy while minimizing processing time
            
            # For single-page PDFs, always check page 1 for text content
            search_page_num = 1 if len(fitz.open(pdf_path)) == 1 else actual_page_num
            
            if self.is_page_searchable(pdf_path, search_page_num):
                # TEXT-FIRST EXTRACTION: Faster and more accurate for searchable PDFs
                print(f"✓ Page {actual_page_num} has searchable text - using text-first extraction")
                text_dict = self.extract_structured_text(pdf_path, search_page_num)
                
                if text_dict:
                    category, chapter, families_list = self.extract_products_from_text(
                        text_dict, actual_page_num, table_data
                    )
                    
                    # Check extraction success - avoid unnecessary image processing
                    if category and families_list:
                        image = None  # Skip image rendering to save processing time
                        print("✅ Text-first extraction successful")
                    else:
                        # TEXT EXTRACTION FAILED: Fall back to VLM processing
                        print("⚠️  Text extraction insufficient, falling back to VLM processing...")
                        image = self.render_pdf_page(pdf_path, search_page_num, dpi=200)
                        category, chapter, families_list = self.extract_products_from_image(
                            image, actual_page_num, table_data
                        )
                else:
                    # STRUCTURED TEXT UNAVAILABLE: Use VLM as only option
                    print("⚠️  Cannot extract structured text, using VLM processing...")
                    image = self.render_pdf_page(pdf_path, search_page_num, dpi=200)
                    category, chapter, families_list = self.extract_products_from_image(
                        image, actual_page_num, table_data
                    )
            else:
                # PAGE NOT SEARCHABLE: Must use VLM processing (scanned pages, image-heavy layouts)
                print(f"⚠️  Page {actual_page_num} has no searchable text - using VLM processing")
                
                # Render PDF page with conservative DPI to balance quality vs processing speed
                image = self.render_pdf_page(pdf_path, search_page_num, dpi=200)
                print(f"✓ Rendered page {actual_page_num} to image ({image.size[0]}x{image.size[1]})")
                
                # VLM IMAGE OPTIMIZATION: Ensure image size is within VLM processing limits
                # Large images cause VLM timeouts and memory issues - optimize proactively
                max_pixels = 1500000  # 1.5 megapixels - tested optimal for qwen3-vl:235b-instruct-cloud
                current_pixels = image.size[0] * image.size[1]
                
                if current_pixels > max_pixels:
                    print(f"⚠️  Image ({image.size[0]}x{image.size[1]}) = {current_pixels:,} pixels, optimizing for VLM...")
                    # Calculate proportional resize to stay under pixel limit
                    resize_factor = (max_pixels / current_pixels) ** 0.5
                    new_width = int(image.size[0] * resize_factor)
                    new_height = int(image.size[1] * resize_factor)
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                    print(f"✓ Optimized to {image.size[0]}x{image.size[1]} = {image.size[0] * image.size[1]:,} pixels")
                
                # Execute VLM processing with hierarchical product extraction
                category, chapter, families_list = self.extract_products_from_image(
                    image, actual_page_num, table_data
                )

        # FINAL FALLBACK: If all extraction methods failed, try ultra-conservative VLM processing
        # Sometimes lower resolution helps with VLM focus on key elements vs overwhelming detail
        if not category or not families_list:
            print("⚠️  All extraction methods failed, attempting final fallback with lower resolution...")
            # Use correct page number for rendering (1 for single-page PDFs)
            final_render_page = 1 if len(fitz.open(pdf_path)) == 1 else actual_page_num
            image = self.render_pdf_page(pdf_path, final_render_page, dpi=150)  # Very conservative DPI
            print(f"✓ Rendered page {actual_page_num} to lower-res image ({image.size[0]}x{image.size[1]})")

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
                image, actual_page_num, table_data
            )
            
        # If VLM completely failed but we have table data, create basic family structure
        if (not category or not families_list) and table_data:
            print("⚠️  VLM extraction failed, falling back to table-only extraction...")
            
            # Extract products directly from table data
            table_products = self.extract_products_from_table_data(table_data, actual_page_num)
            
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

        # Bounding box visualization removed - using text-first extraction

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
            self.save_to_database(category, family_data, products_list, actual_page_num, chapter)

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

    def process_all_pages(self, pdf_path_or_dir, start_page=1, end_page=None):
        """
        Process pages in a PDF file or individual PDF pages in a directory.
        
        Args:
            pdf_path_or_dir: Path to PDF file or directory containing individual PDF pages
            start_page: Starting page number (1-based, default: 1)
            end_page: Ending page number (1-based, default: None for all pages)
            
        Returns:
            Dictionary with processing results
        """
        path = Path(pdf_path_or_dir)
        
        if path.is_file():
            # Process all pages in a single PDF file
            doc = fitz.open(path)
            total_pages = len(doc)
            doc.close()
            
            print(f"📄 Processing pages {start_page}-{end_page or total_pages} from PDF: {path.name}")
            all_pages = [(path, i) for i in range(1, total_pages + 1)]
            # Filter by start_page and end_page
            pages_to_process = [(pdf_path, page_num) for pdf_path, page_num in all_pages 
                              if page_num >= start_page and (end_page is None or page_num <= end_page)]
            
        elif path.is_dir():
            # Process all individual PDF page files in directory
            pdf_files = sorted(path.glob("*.pdf"))
            if not pdf_files:
                print(f"❌ No PDF files found in directory: {path}")
                return {}
            
            print(f"📁 Processing individual PDF pages from directory: {path.name}")
            # Extract page numbers from filenames like "Produktbok_page_031.pdf"
            all_pages = []
            for pdf_file in pdf_files:
                # Try to extract page number from filename
                import re
                match = re.search(r'page_(\d+)', pdf_file.stem)
                if match:
                    page_num = int(match.group(1))
                    all_pages.append((pdf_file, page_num))
                else:
                    # If no page number found, use 1 as default
                    all_pages.append((pdf_file, 1))
            
            # Filter by start_page and end_page
            pages_to_process = [(pdf_path, page_num) for pdf_path, page_num in all_pages 
                              if page_num >= start_page and (end_page is None or page_num <= end_page)]
            
            print(f"📊 Found {len(all_pages)} total pages, processing {len(pages_to_process)} pages (from {start_page} to {end_page or 'end'})")
            
        else:
            print(f"❌ Path not found: {path}")
            return {}
        
        # Process all pages
        results = {
            'total_pages': len(pages_to_process),
            'successful_pages': 0,
            'failed_pages': 0,
            'total_families': 0,
            'total_products': 0,
            'page_results': []
        }
        
        for i, (pdf_path, page_num) in enumerate(pages_to_process, 1):
            try:
                print(f"\n{'='*80}")
                print(f"📄 Processing page {i}/{len(pages_to_process)}: {pdf_path.name} (Page {page_num})")
                print(f"{'='*80}")
                
                category, chapter, families = self.extract_from_pdf_page(pdf_path, page_num)
                
                if families:
                    page_products = sum(len(f.get('products', [])) for f in families)
                    results['successful_pages'] += 1
                    results['total_families'] += len(families)
                    results['total_products'] += page_products
                    
                    results['page_results'].append({
                        'page': page_num,
                        'pdf_file': pdf_path.name,
                        'category': category,
                        'chapter': chapter,
                        'families': len(families),
                        'products': page_products,
                        'status': 'success'
                    })
                    
                    print(f"✅ Page {page_num}: {len(families)} families, {page_products} products")
                else:
                    results['failed_pages'] += 1
                    results['page_results'].append({
                        'page': page_num,
                        'pdf_file': pdf_path.name,
                        'status': 'failed',
                        'reason': 'No products extracted'
                    })
                    print(f"⚠️  Page {page_num}: No products extracted")
                    
            except Exception as e:
                results['failed_pages'] += 1
                results['page_results'].append({
                    'page': page_num,
                    'pdf_file': pdf_path.name,
                    'status': 'error',
                    'reason': str(e)
                })
                print(f"❌ Page {page_num}: Error - {e}")
        
        # Print summary
        print(f"\n{'='*80}")
        print("📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*80}")
        print(f"Total pages processed: {results['total_pages']}")
        print(f"Successful: {results['successful_pages']}")
        print(f"Failed: {results['failed_pages']}")
        print(f"Total families extracted: {results['total_families']}")
        print(f"Total products extracted: {results['total_products']}")
        print(f"📊 Data saved to database: {self.db_manager.db_path}")
        
        # Show successful pages
        if results['successful_pages'] > 0:
            print(f"\n✅ Successful pages:")
            for result in results['page_results']:
                if result['status'] == 'success':
                    print(f"  Page {result['page']} ({result['pdf_file']}): {result['families']} families, {result['products']} products")
        
        # Show failed pages
        if results['failed_pages'] > 0:
            print(f"\n⚠️  Failed pages:")
            for result in results['page_results']:
                if result['status'] in ['failed', 'error']:
                    print(f"  Page {result['page']} ({result['pdf_file']}): {result.get('reason', 'Unknown error')}")
        
        return results


def main():
    """
    Main entry point for the product extraction system.
    
    Provides a comprehensive CLI interface for both single-page and batch processing
    modes. Handles initialization, error management, and results reporting.
    """
    # CLI CONFIGURATION with comprehensive help text
    parser = argparse.ArgumentParser(
        description="Advanced Product Data Extractor using Vision Language Models",
        epilog="""
EXAMPLES:
  Single page:  python 4_extract_product.py data/pdf_pages/Produktbok_page_031.pdf --page 31
  Batch mode:   python 4_extract_product.py data/pdf_pages/ --all-pages
  Page range:   python 4_extract_product.py data/pdf_pages/ --all-pages --start-page 28 --end-page 40
  Full PDF:     python 4_extract_product.py Produktbok.pdf --all-pages

PROCESSING MODES:
  - Text-first extraction for searchable PDFs (fastest, most accurate)
  - VLM processing for scanned pages and complex layouts
  - Table data integration for precise specifications
  - Automatic fallback strategies for maximum reliability
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("pdf_path", 
                       help="Path to PDF file or directory containing PDF pages")
    parser.add_argument("--page", type=int, default=31, 
                       help="Page number to process (ignored when --all-pages is used)")
    parser.add_argument("--all-pages", action="store_true", 
                       help="Process all pages in directory or entire PDF file")
    parser.add_argument("--start-page", type=int, default=1,
                       help="Starting page number for batch processing (default: 1)")
    parser.add_argument("--end-page", type=int, default=None,
                       help="Ending page number for batch processing (default: process all)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", 
                       help="Ollama API server URL (default: http://localhost:11434)")
    parser.add_argument("--model", default="qwen3-vl:235b-instruct-cloud", 
                       help="VLM model identifier (default: qwen3-vl:235b-instruct-cloud)")
    
    args = parser.parse_args()
    
    # INPUT VALIDATION with descriptive error messages
    path = Path(args.pdf_path)
    if not path.exists():
        print(f"❌ Error: Specified path does not exist: {path}")
        print(f"   Please check the file path and try again.")
        sys.exit(1)
    
    if not args.all_pages and path.is_dir():
        print(f"❌ Error: Directory specified but --all-pages flag not set")
        print(f"   Use --all-pages to process all files in directory: {path}")
        sys.exit(1)
    
    # SYSTEM INITIALIZATION with error handling
    print(f"🚀 Initializing Product Extraction System")
    print(f"   Model: {args.model}")
    print(f"   Ollama URL: {args.ollama_url}")
    print(f"   Input: {path}")
    
    try:
        extractor = ProductExtractor(
            ollama_url=args.ollama_url,
            model_name=args.model
        )
        print(f"✅ System initialized successfully")
    except RuntimeError as e:
        print(f"❌ System initialization failed: {e}")
        print(f"   Please check database configuration and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected initialization error: {e}")
        sys.exit(1)
    
    # PROCESSING EXECUTION with comprehensive error handling
    try:
        if args.all_pages:
            # BATCH PROCESSING MODE: Process entire directories or multi-page PDFs
            print(f"\n📂 Starting batch processing mode...")
            print(f"   Range: Page {args.start_page} to {args.end_page or 'end'}")
            results = extractor.process_all_pages(path, args.start_page, args.end_page)
            
            # BATCH RESULTS SUMMARY
            if results['successful_pages'] > 0:
                success_rate = 100 * results['successful_pages'] / results['total_pages']
                print(f"\n🎉 Batch processing completed successfully!")
                print(f"📈 Success rate: {results['successful_pages']}/{results['total_pages']} pages ({success_rate:.1f}%)")
                print(f"📊 Total extracted: {results['total_families']} families, {results['total_products']} products")
            else:
                print(f"\n❌ Batch processing failed - no pages processed successfully")
                print(f"   Check input files and Ollama service availability")
                sys.exit(1)
                
        else:
            # SINGLE PAGE PROCESSING MODE: Process one specific page
            if path.is_dir():
                print(f"❌ Error: Directory provided but --all-pages flag not set")
                print(f"   Use --all-pages to process directory: {path}")
                sys.exit(1)
            
            print(f"\n📄 Starting single page processing...")
            print(f"   File: {path.name}")
            print(f"   Page: {args.page}")
            
            category, chapter, families = extractor.extract_from_pdf_page(
                path, args.page
            )

            # SINGLE PAGE RESULTS VALIDATION AND REPORTING
            if families:
                total_products = sum(len(f.get('products', [])) for f in families)
                print(f"\n✅ Single page processing completed successfully!")
                print(f"📊 Results: {len(families)} families, {total_products} products extracted from page {args.page}")
                print(f"� Data saved to database: {extractor.db_manager.db_path}")
                
                # Show brief summary of extracted families
                for i, family in enumerate(families, 1):
                    family_name = family.get('name', 'Unknown')
                    product_count = len(family.get('products', []))
                    print(f"   {i}. {family_name}: {product_count} products")
            else:
                print(f"⚠️  No products extracted from page {args.page}")
                print(f"   This may indicate:")
                print(f"   - Page contains no product tables")
                print(f"   - Page quality issues preventing extraction")
                print(f"   - VLM processing limitations")

    except KeyboardInterrupt:
        print(f"\n⚠️  Processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error during processing: {e}")
        print(f"   Please check:")
        print(f"   - Input file format and accessibility")  
        print(f"   - Ollama service availability at {args.ollama_url}")
        print(f"   - Model availability: {args.model}")
        print(f"   - Sufficient disk space for processing")
        
        # Show traceback for debugging in verbose mode
        import traceback
        print(f"\n🔍 Detailed error information:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()