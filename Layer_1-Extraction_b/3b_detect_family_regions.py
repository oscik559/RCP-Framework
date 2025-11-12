#!/usr/bin/env python3
"""
Product Family Information Extractor
=====================================

Detects and extracts product family information from regions above product tables using PyMuPDF.
Extracts structured family details like:
- Product codes (4207, 4200, etc.)  
- Product names (G-gängad, M-gängad, etc.)
- Descriptions (90° Smidd inv., etc.)
- Product groups (PRODUKTGRUPP 300, etc.)
- Technical specifications (Hylsa types, DIN standards)

STRATEGY:
---------
1. Load existing table bboxes from table detection results
2. For each table, detect family region above it
3. Extract text content from family region using PyMuPDF
4. Parse and structure the extracted family information
5. Save structured family data to JSON files

USAGE:
------
python 3b_detect_family_regions.py --page 5
python 3b_detect_family_regions.py --pages 5-10
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import numpy as np
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  Matplotlib not available - visualizations will be skipped")

# Add current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))


class FamilyRegionDetector:
    """
    Detects product family regions above product specification tables.
    """
    
    def __init__(self):
        """Initialize family information extractor."""
        script_dir = Path(__file__).parent
        
        # Use main project data directory (one level up)
        main_data_dir = script_dir.parent / "data"
        
        self.png_pages_dir = main_data_dir / "png_pages"
        self.tables_dir = main_data_dir / "tables"
        
        # Local data directories
        local_data_dir = script_dir / "data"
        self.family_dir = local_data_dir / "family"        # For structured family information
        
        # Create directories
        self.family_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 PNG pages: {self.png_pages_dir}")
        print(f"📁 Tables: {self.tables_dir}")
        print(f"📁 Family data: {self.family_dir}")
    
    def load_table_regions(self, page_number: int) -> List[Dict]:
        """
        Load existing table regions from table detection results.
        
        Args:
            page_number (int): Page number
            
        Returns:
            List[Dict]: List of table region dictionaries
        """
        # Look for table JSON files from table detection
        table_files = sorted(self.tables_dir.glob(f"page_{page_number:03d}_table_*.json"))
        
        table_regions = []
        for table_file in table_files:
            try:
                with open(table_file, 'r', encoding='utf-8') as f:
                    table_data = json.load(f)
                    
                    # Handle different bbox field names
                    bbox = None
                    if 'bbox' in table_data:
                        bbox = table_data['bbox']
                    elif 'table_bbox' in table_data:
                        bbox = table_data['table_bbox']
                    
                    if bbox and len(bbox) >= 4:
                        table_regions.append({
                            'bbox': bbox,
                            'table_file': str(table_file),
                            'table_data': table_data
                        })
                        print(f"      Loaded table: {table_file.name}, bbox={bbox}")
                        
            except Exception as e:
                print(f"⚠️  Could not load {table_file}: {e}")
        
        return table_regions

        
        # Process individual lines for more specific information
        for line_data in lines:
            line_text = line_data["text"].strip()
            
            # Skip very short or non-informative lines
            if len(line_text) < 3 or line_text in ["S&", "Artikelnr.", "Används med", "Slang ID"]:
                continue
                
            # Extract angle descriptions
            angles = re.findall(patterns["angle_description"], line_text)
            family_info["descriptions"].extend(angles)
            
            # Extract thread types
            threads = re.findall(patterns["thread_type"], line_text)
            family_info["product_names"].extend(threads)
            
            # Look for product names/descriptions (lines with meaningful content)
            if any(term in line_text.lower() for term in ["hydraulisk", "koppling", "coupling", "adapter", "nippel", "hylsa", "smidd"]):
                if line_text not in family_info["descriptions"]:
                    family_info["descriptions"].append(line_text)
            
            # Look for special notations
            if "skalas" in line_text.lower():
                family_info["descriptions"].append(line_text)
        
        # Clean up and remove duplicates
        for key in ["product_codes", "product_names", "descriptions", "product_groups", "sleeve_types"]:
            family_info[key] = list(dict.fromkeys(family_info[key]))
            
        return family_info
    
    def detect_family_region_for_table(self, table_bbox: List[float], page_width: float, page_height: float) -> Dict:
        """
        Detect family region above a specific table.
        
        Args:
            table_bbox (List[float]): Table bounding box [x0, y0, x1, y1]
            page_width (float): Page width
            page_height (float): Page height
            
        Returns:
            Dict: Family region information
        """
        x0, y0, x1, y1 = table_bbox
        
        # Calculate family region above table - be more conservative
        # Look for family information in a smaller, more targeted region
        
        family_height = 80   # Smaller height to avoid table overlap
        margin = 20          # Larger margin from table to avoid header contamination
        
        # Family region coordinates - more conservative bounds
        family_x0 = x0 - 10   # Slightly extend left to catch product codes
        family_x1 = x1 + 10   # Slightly extend right
        family_y1 = y0 - margin  # Well above table
        family_y0 = max(0, family_y1 - family_height)  # Family region top
        
        # Detect column (left/right) for better positioning
        table_center_x = (x0 + x1) / 2
        column = 'left' if table_center_x < page_width / 2 else 'right'
        
        # Adjust family region based on column
        if column == 'left':
            # Left column - extend to left margin
            family_x0 = max(0, min(family_x0, 50))
        else:
            # Right column - extend to right margin  
            family_x1 = min(page_width, max(family_x1, page_width - 50))
        
        return {
            'bbox': [family_x0, family_y0, family_x1, family_y1],
            'column': column,
            'table_bbox': table_bbox,
            'estimated_height': family_height,
            'margin_from_table': margin
        }
    
    def extract_page_dimensions(self, pdf_path: Path, page_number: int) -> Tuple[float, float]:
        """
        Extract page dimensions from PDF.
        
        Args:
            pdf_path (Path): PDF file path
            page_number (int): Page number (1-based)
            
        Returns:
            Tuple[float, float]: (width, height)
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)
            
            width = page.rect.width
            height = page.rect.height
            
            doc.close()
            return width, height
            
        except Exception as e:
            print(f"❌ Error getting page dimensions: {e}")
            # Default A4 dimensions in points
            return 595.0, 842.0
    
    def clean_extracted_text(self, raw_text: str) -> str:
        """
        Clean extracted text by removing corrupted characters and noise.
        
        Args:
            raw_text (str): Raw extracted text
            
        Returns:
            str: Cleaned text
        """
        import re
        
        if not raw_text:
            return ""
        
        # Remove common PDF extraction artifacts and control characters
        text = raw_text.replace('\u0015', '').replace('\u0012', '').replace('\u0005', '')
        text = text.replace('\u0018', '').replace('\u0019', '').replace('\u0016', '')
        
        # Remove other control characters and non-printable characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
        
        # Remove common PDF extraction noise patterns
        text = re.sub(r'\(\d+S\d+', '', text)  # Remove patterns like (1S1
        text = re.sub(r'[A-Z]&\d*', '', text)  # Remove patterns like S&1, S&
        text = re.sub(r'\d+/\d+"', '', text)   # Remove fraction measurements like 3/8"
        
        # Clean up whitespace and split into lines for better processing
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Try to identify meaningful content using regex patterns
        meaningful_parts = []
        
        # Extract product codes (priority content)
        product_codes = re.findall(r'\b\d{4}-\d{2}\b', text)
        meaningful_parts.extend(product_codes)
        
        # Extract product group information
        product_groups = re.findall(r'PRODUKTGRUPP\s+\d+', text)
        meaningful_parts.extend(product_groups)
        
        # Extract technical specifications
        tech_specs = re.findall(r'Hylsa\s+[A-Z0-9/\s]+', text)
        meaningful_parts.extend(tech_specs)
        
        # Extract hose information
        hose_info = re.findall(r'Slangen?\s+\w+', text)
        meaningful_parts.extend(hose_info)
        
        # Extract DIN standards
        din_standards = re.findall(r'DIN\s+[A-Z0-9]+', text)
        meaningful_parts.extend(din_standards)
        
        # If we found meaningful parts, use them; otherwise return cleaned original
        if meaningful_parts:
            return '\n'.join(meaningful_parts)
        else:
            # Fallback: return original text but heavily cleaned
            cleaned = re.sub(r'[^\w\s\-°/]', ' ', text)  # Keep only word chars, whitespace, hyphens, degrees, slashes
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned if len(cleaned) > 5 else ""
    
    def extract_text_from_region(self, pdf_path: Path, page_number: int, bbox: List[float]) -> Dict:
        """
        Extract text content from a specific region using PyMuPDF.
        
        Args:
            pdf_path (Path): PDF file path
            page_number (int): Page number (1-based)
            bbox (List[float]): Bounding box [x0, y0, x1, y1]
            
        Returns:
            Dict: Extracted text information
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number - 1)
            
            # Create rectangle from bbox
            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Extract text from the region
            raw_text = page.get_text("text", clip=rect)
            text = self.clean_extracted_text(str(raw_text) if raw_text else "")
            
            # Extract text with detailed information (blocks, lines, spans)
            text_dict_result = page.get_text("dict", clip=rect)
            text_dict = text_dict_result if isinstance(text_dict_result, dict) else {}
            
            doc.close()
            
            # Parse the extracted text
            parsed_info = self.parse_family_text(text, text_dict)
            
            return {
                'raw_text': text,
                'text_dict': text_dict,
                'parsed_info': parsed_info,
                'extraction_success': True
            }
            
        except Exception as e:
            print(f"❌ Error extracting text from region: {e}")
            return {
                'raw_text': '',
                'text_dict': None,
                'parsed_info': {},
                'extraction_success': False,
                'error': str(e)
            }
    
    def parse_family_text(self, raw_text: str, text_dict: Dict) -> Dict:
        """
        Parse family region text to extract structured family-level information.
        Focus on family characteristics, not individual product codes.
        
        Args:
            raw_text (str): Raw extracted text
            text_dict (Dict): Detailed text dictionary from PyMuPDF
            
        Returns:
            Dict: Structured family information
        """
        import re
        
        parsed = {
            'product_group': '',           # e.g., "PRODUKTGRUPP 300"
            'family_type': '',            # e.g., "G-gängad", "M-gängad"
            'connection_type': '',        # e.g., "90° Smidd inv."
            'technical_specs': [],        # Sleeve types, standards
            'hose_compatibility': [],     # Hose type information
            'descriptions': []            # Other descriptive information
        }
        
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Skip individual product codes - these belong to table data
            if re.match(r'^\d{4}-\d{2}$', line.strip()):
                continue
                
            # Extract product group (e.g., PRODUKTGRUPP 300)
            if 'PRODUKTGRUPP' in line.upper():
                parsed['product_group'] = line.strip()
                continue
            
            # Extract family type (connection thread types)
            if any(pattern in line.upper() for pattern in ['G-GÄNGAD', 'M-GÄNGAD', 'GÄNGAD']):
                parsed['family_type'] = line.strip()
                continue
            
            # Extract connection type (angle descriptions)
            if any(pattern in line for pattern in ['°', 'Smidd', 'inv.', 'utv.']):
                parsed['connection_type'] = line.strip()
                continue
            
            # Extract technical specifications (sleeve types, standards, etc.)
            if any(keyword in line.upper() for keyword in ['HYLSA', 'DIN', 'EN']):
                if line not in parsed['technical_specs']:  # Avoid duplicates
                    parsed['technical_specs'].append(line.strip())
                continue
            
            # Extract hose compatibility information
            if any(keyword in line.upper() for keyword in ['SLANG', 'SKALAS', '1SN', '2SN', '2SC']):
                if line not in parsed['hose_compatibility']:
                    parsed['hose_compatibility'].append(line.strip())
                continue
            
            # Extract other meaningful family descriptions
            if (len(line) > 3 and 
                not line.startswith(('S&', '1 1', '3/8', '5/8')) and  # Skip table artifacts
                not re.match(r'^[0-9\s\-/]+$', line) and  # Skip pure numbers/measurements
                not re.match(r'^\d{4}-\d{2}', line) and   # Skip product codes
                line not in parsed['technical_specs'] and 
                line not in parsed['hose_compatibility'] and
                'PRODUKTGRUPP' not in line):
                parsed['descriptions'].append(line.strip())
        
        # Remove duplicates while preserving order
        for key in ['technical_specs', 'hose_compatibility', 'descriptions']:
            parsed[key] = list(dict.fromkeys(parsed[key]))
        
        return parsed
    

    
    def save_family_information(self, page_number: int, family_data: List[Dict]) -> bool:
        """
        Save structured family information to JSON file.
        
        Args:
            page_number (int): Page number
            family_data (List[Dict]): List of structured family information
            
        Returns:
            bool: Success status
        """
        output_file = self.family_dir / f"page_{page_number:03d}_family_info.json"
        
        try:
            # Create summary statistics
            has_product_groups = sum(1 for family in family_data if family.get('product_group'))
            has_family_types = sum(1 for family in family_data if family.get('family_type'))
            has_connection_types = sum(1 for family in family_data if family.get('connection_type'))
            
            structured_data = {
                'page_number': page_number,
                'extraction_timestamp': str(Path().cwd() / 'timestamp'),  # Simple timestamp
                'summary': {
                    'total_families': len(family_data),
                    'families_with_groups': has_product_groups,
                    'families_with_types': has_family_types,
                    'families_with_connections': has_connection_types
                },
                'families': family_data
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            
            print(f"   📋 Saved structured family information to {output_file.name}")
            print(f"      📊 {len(family_data)} families with family-level characteristics")
            return True
            
        except Exception as e:
            print(f"   ❌ Error saving family information: {e}")
            return False
    
    def _unused_visualize_family_regions(self, page_number: int, family_regions: List[Dict], 
                                table_regions: List[Dict]) -> bool:
        """
        Add family regions to existing table visualization images.
        
        Args:
            page_number (int): Page number
            family_regions (List[Dict]): List of family regions
            table_regions (List[Dict]): List of table regions
            
        Returns:
            bool: Success status
        """
        # Look for existing table visualization in Layer_1-Extraction_b/data/tables first
        local_table_viz = self.regions_dir.parent / "tables" / f"Press_Couplings_page_{page_number:03d}_tables_visualization.png"
        main_table_viz = self.tables_dir / f"page_{page_number:03d}_tables_visualization.png"
        
        if local_table_viz.exists():
            print(f"   📊 Adding family regions to existing local table visualization...")
            base_image_path = local_table_viz
            title = f'Tables + Family Regions - Page {page_number}'
        elif main_table_viz.exists():
            print(f"   📊 Adding family regions to main table visualization...")
            base_image_path = main_table_viz
            title = f'Tables + Family Regions - Page {page_number}'
        else:
            # Fall back to original PNG
            base_image_path = self.png_pages_dir / f"Produktbok_page_{page_number:03d}.png"
            title = f'Family Regions Detection - Page {page_number}'
            
        if not base_image_path.exists():
            print(f"   ⚠️  Base image not found: {base_image_path}")
            return False
        
        if not MATPLOTLIB_AVAILABLE:
            print(f"   ⚠️  Skipping visualization - matplotlib not available")
            return False
            
        try:
            # Load and setup image
            img = Image.open(base_image_path)
            img_array = np.array(img)
            fig, ax = plt.subplots(1, 1, figsize=(12, 16))
            ax.imshow(img_array)
            ax.set_title(title, fontsize=14, fontweight='bold')
            
            # If we're using the original PNG (no existing table viz), draw tables first
            using_table_viz = local_table_viz.exists() or main_table_viz.exists()
            if not using_table_viz:
                # Draw table regions (blue)
                for i, table_region in enumerate(table_regions):
                    bbox = table_region['bbox']
                    rect = patches.Rectangle(
                        (bbox[0], bbox[1]), 
                        bbox[2] - bbox[0], 
                        bbox[3] - bbox[1],
                        linewidth=2, 
                        edgecolor='blue', 
                        facecolor='blue', 
                        alpha=0.2,
                        label='Table' if i == 0 else ""
                    )
                    ax.add_patch(rect)
                    
                    # Add table label
                    ax.text(bbox[0] + 5, bbox[1] + 15, f'Table {i+1}', 
                           fontsize=10, color='blue', fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            # Draw family regions (red) - these will overlay on existing table visualization
            for i, family_region in enumerate(family_regions):
                bbox = family_region['bbox']
                column = family_region.get('column', 'unknown')
                
                rect = patches.Rectangle(
                    (bbox[0], bbox[1]), 
                    bbox[2] - bbox[0], 
                    bbox[3] - bbox[1],
                    linewidth=3,  # Thicker line to stand out
                    edgecolor='red', 
                    facecolor='red', 
                    alpha=0.15,  # More transparent to show underlying table marks
                    label='Family Region' if i == 0 else ""
                )
                ax.add_patch(rect)
                
                # Add family region label with distinct styling
                ax.text(bbox[0] + 5, bbox[1] + 15, f'FAMILY {i+1}\n({column})', 
                       fontsize=9, color='darkred', fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.9, edgecolor='red'))
                
                # Add connecting line from family region to its table
                if i < len(table_regions):
                    table_bbox = table_regions[i]['bbox']
                    # Draw dashed line from center of family region to top of table
                    family_center_x = (bbox[0] + bbox[2]) / 2
                    family_bottom = bbox[3]
                    table_center_x = (table_bbox[0] + table_bbox[2]) / 2
                    table_top = table_bbox[1]
                    
                    ax.plot([family_center_x, table_center_x], [family_bottom, table_top], 
                           'r--', linewidth=2, alpha=0.7, label='Family-Table Link' if i == 0 else "")
            
            # Setup plot
            ax.set_xlim(0, img.width)
            ax.set_ylim(img.height, 0)  # Invert y-axis
            ax.legend(loc='upper right')
            ax.axis('off')
            
            # Save enhanced visualization
            if local_table_viz.exists():
                # Replace the local table visualization with enhanced version
                output_file = local_table_viz.parent / f"Press_Couplings_page_{page_number:03d}_tables_with_families_visualization.png"
                
                # Backup original if not already done
                backup_file = local_table_viz.parent / f"Press_Couplings_page_{page_number:03d}_tables_only_visualization.png"
                if not backup_file.exists():
                    import shutil
                    shutil.copy2(local_table_viz, backup_file)
                    print(f"   � Original table visualization backed up as: {backup_file.name}")
                    
            elif main_table_viz.exists():
                # Save enhanced version in main tables directory
                output_file = self.tables_dir / f"page_{page_number:03d}_tables_with_families_visualization.png"
            else:
                # Create new visualization in regions directory
                output_file = self.regions_dir / f"page_{page_number:03d}_family_regions_visualization.png"
                
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"   � Enhanced visualization saved: {output_file.name}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error creating visualization: {e}")
            return False
    
    def process_page(self, pdf_path: Path, page_number: int) -> Dict:
        """
        Process a single page to detect family regions.
        
        Args:
            pdf_path (Path): PDF file path
            page_number (int): Page number
            
        Returns:
            Dict: Processing statistics
        """
        print(f"\n📄 Processing page {page_number} for family regions...")
        
        stats = {
            'tables_found': 0,
            'family_regions_created': 0,
            'success': False
        }
        
        # Load existing table regions
        table_regions = self.load_table_regions(page_number)
        stats['tables_found'] = len(table_regions)
        
        if not table_regions:
            print(f"   ⚠️  No table regions found for page {page_number}")
            return stats
        
        print(f"   Found {len(table_regions)} table regions")
        
        # Get page dimensions
        page_width, page_height = self.extract_page_dimensions(pdf_path, page_number)
        print(f"   Page dimensions: {page_width:.1f} x {page_height:.1f}")
        
        # Create family regions for each table
        family_regions = []
        for i, table_region in enumerate(table_regions):
            table_bbox = table_region['bbox']
            
            family_region = self.detect_family_region_for_table(
                table_bbox, page_width, page_height
            )
            
            # Extract text content from the family region using PyMuPDF
            print(f"      📖 Extracting text from family region {i+1}...")
            text_extraction = self.extract_text_from_region(pdf_path, page_number, family_region['bbox'])
            
            # Add extracted text data to family region
            family_region.update(text_extraction)
            
            # Add metadata
            family_region['family_id'] = i + 1
            family_region['table_id'] = i + 1
            family_region['page_number'] = page_number
            
            family_regions.append(family_region)
            
            # Display extraction results
            if text_extraction['extraction_success']:
                family_info = text_extraction['parsed_info']
                print(f"      Family {i+1}: bbox={family_region['bbox'][:4]}, column={family_region['column']}")
                print(f"         📝 Raw text: '{text_extraction['raw_text'][:100]}{'...' if len(text_extraction['raw_text']) > 100 else ''}'")
                
                if family_info['product_group']:
                    print(f"         � Product group: {family_info['product_group']}")
                if family_info['family_type']:
                    print(f"         🏷️  Family type: {family_info['family_type']}")
                if family_info['connection_type']:
                    print(f"         � Connection type: {family_info['connection_type']}")
                if family_info['technical_specs']:
                    print(f"         🔧 Technical specs: {family_info['technical_specs']}")
                if family_info['hose_compatibility']:
                    print(f"         🚰 Hose compatibility: {family_info['hose_compatibility']}")
                if family_info['descriptions']:
                    print(f"         📝 Descriptions: {family_info['descriptions']}")
            else:
                print(f"      Family {i+1}: bbox={family_region['bbox'][:4]}, column={family_region['column']} (no text extracted)")
        
        stats['family_regions_created'] = len(family_regions)
        
        # Extract and save structured family information
        structured_families = []
        for i, family_region in enumerate(family_regions):
            if family_region.get('extraction_success', False):
                family_info = family_region.get('parsed_info', {})
                
                # Create structured family entry (no bbox needed)
                structured_family = {
                    'family_id': i + 1,
                    'table_id': i + 1,
                    'product_group': family_info.get('product_group', ''),
                    'family_type': family_info.get('family_type', ''),
                    'connection_type': family_info.get('connection_type', ''),
                    'technical_specs': family_info.get('technical_specs', []),
                    'hose_compatibility': family_info.get('hose_compatibility', []),
                    'descriptions': family_info.get('descriptions', []),
                    'raw_text_sample': family_region.get('raw_text', '')[:200]  # First 200 chars for reference
                }
                structured_families.append(structured_family)
        
        # Save structured family information
        if self.save_family_information(page_number, structured_families):
            stats['success'] = True
        
        print(f"   ✅ Extracted {len(structured_families)} structured family records")
        
        return stats


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Detect product family regions above tables"
    )
    parser.add_argument(
        "--pdf",
        default="Press_Couplings.pdf",
        help="Path to PDF file (default: Press_Couplings.pdf)"
    )
    parser.add_argument(
        "--page",
        type=int,
        help="Single page to process"
    )
    parser.add_argument(
        "--pages",
        help="Page range (e.g., '5-10')"
    )
    
    args = parser.parse_args()
    
    # Find PDF file
    script_dir = Path(__file__).parent
    pdf_path = script_dir / args.pdf
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    detector = FamilyRegionDetector()
    
    # Determine page range
    if args.page:
        pages = [args.page]
    elif args.pages:
        start, end = map(int, args.pages.split('-'))
        pages = range(start, end + 1)
    else:
        print("❌ Specify --page or --pages")
        sys.exit(1)
    
    print(f"\n🔧 Detecting family regions from {pdf_path.name}")
    print(f"📖 Pages: {list(pages)}")
    
    total_stats = {
        'pages_processed': 0,
        'total_tables': 0,
        'total_family_regions': 0
    }
    
    for page_num in pages:
        stats = detector.process_page(pdf_path, page_num)
        
        total_stats['pages_processed'] += 1
        total_stats['total_tables'] += stats['tables_found']
        total_stats['total_family_regions'] += stats['family_regions_created']
    
    print(f"\n✅ Family region detection complete!")
    print(f"   Pages processed: {total_stats['pages_processed']}")
    print(f"   Total tables: {total_stats['total_tables']}")
    print(f"   Total family regions: {total_stats['total_family_regions']}")


if __name__ == "__main__":
    main()