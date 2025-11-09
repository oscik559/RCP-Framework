#!/usr/bin/env python3
"""
Product Knowledge Extractor
============================

Extracts general product knowledge, descriptions, assembly instructions,
standards, and documentation from catalog intro pages and reference sections.

This script focuses on capturing non-hierarchical product information that
doesn't fit the standard category → family → product structure.

USAGE:
-----
python 1_extract_knowledge.py --pdf Produktbok_2020_Coupling.pdf --pages 167-169
python 1_extract_knowledge.py --pdf Produktbok_2020_Coupling.pdf --all
"""

import os
import sys
import json
import sqlite3
import argparse
import re
from pathlib import Path
import fitz  # PyMuPDF

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "Layer_1-Extraction"))
from db_utils import DatabaseManager


class KnowledgeExtractor:
    """
    Extracts product knowledge from catalog pages.
    
    Captures:
    - Product descriptions and overviews
    - Assembly instructions
    - Standards and specifications
    - Table of contents
    - Technical information
    - Safety guidelines
    """
    
    def __init__(self, pdf_path, use_test_db=False):
        """
        Initialize knowledge extractor.
        
        Args:
            pdf_path (str): Path to PDF file
            use_test_db (bool): If True, use harvested_test.db instead of harvested.db
        """
        self.pdf_path = Path(pdf_path)
        self.pdf_name = self.pdf_path.name
        
        # Use test database if requested
        db_path = "data/database/harvested_test.db" if use_test_db else "data/database/harvested.db"
        self.db_manager = DatabaseManager(db_path)
        
        if not self.db_manager.init_database():
            raise RuntimeError("Database initialization failed")
    
    def extract_page_text(self, page_number):
        """
        Extract structured text from a single page.
        
        Args:
            page_number (int): Page number (1-based)
            
        Returns:
            dict: Dictionary containing page text and metadata
        """
        try:
            doc = fitz.open(self.pdf_path)
            page = doc.load_page(page_number - 1)
            
            # Extract text with layout information
            text_dict = page.get_text("dict")
            plain_text = page.get_text("text")
            
            # Get page dimensions
            rect = page.rect
            page_info = {
                'page_number': page_number,
                'width': rect.width,
                'height': rect.height,
                'text_dict': text_dict,
                'plain_text': plain_text
            }
            
            doc.close()
            return page_info
            
        except Exception as e:
            print(f"❌ Error extracting page {page_number}: {e}")
            return None
    
    def identify_sections(self, page_info):
        """
        Identify different sections on the page based on text formatting.
        
        Args:
            page_info (dict): Page information from extract_page_text
            
        Returns:
            list: List of sections with metadata
        """
        sections = []
        text_dict = page_info.get('text_dict', {})
        
        if 'blocks' not in text_dict:
            return sections
        
        current_section = None
        
        for block in text_dict['blocks']:
            if 'lines' not in block:
                continue
            
            bbox = block.get('bbox', [0, 0, 0, 0])
            block_text = []
            fonts = []
            
            for line in block['lines']:
                line_text = []
                for span in line.get('spans', []):
                    span_text = span.get('text', '').strip()
                    if span_text:
                        line_text.append(span_text)
                        fonts.append({
                            'size': span.get('size', 0),
                            'flags': span.get('flags', 0),
                            'font': span.get('font', '')
                        })
                
                if line_text:
                    block_text.append(' '.join(line_text))
            
            if not block_text:
                continue
            
            full_text = '\n'.join(block_text)
            
            # Determine if this is a heading based on font size
            avg_font_size = sum(f['size'] for f in fonts) / len(fonts) if fonts else 0
            is_bold = any(f['flags'] & 16 for f in fonts)  # Bold flag is bit 4
            
            # Detect section type
            section_type = self._classify_section_type(full_text, avg_font_size, is_bold)
            
            # If it's a heading, start a new section
            if (avg_font_size > 12 or is_bold) and len(full_text) < 150:
                if current_section and current_section['content'].strip():
                    sections.append(current_section)
                
                current_section = {
                    'title': full_text,
                    'content': '',
                    'bbox': bbox,
                    'section_type': section_type,
                    'page_number': page_info['page_number']
                }
            else:
                # Add to current section
                if current_section:
                    current_section['content'] += full_text + '\n\n'
                else:
                    # Start a section without a title
                    current_section = {
                        'title': '',
                        'content': full_text + '\n\n',
                        'bbox': bbox,
                        'section_type': section_type,
                        'page_number': page_info['page_number']
                    }
        
        # Add the last section
        if current_section and current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _classify_section_type(self, text, font_size, is_bold):
        """
        Classify section type based on content.
        
        Args:
            text (str): Section text
            font_size (float): Average font size
            is_bold (bool): Whether text is bold
            
        Returns:
            str: Section type classification
        """
        text_upper = text.upper()
        
        # Classification rules
        if any(keyword in text_upper for keyword in ['INNEHÅLL', 'CONTENTS', 'INDEX']):
            return 'TOC'
        elif any(keyword in text_upper for keyword in ['MONTERINGSANVISNING', 'ASSEMBLY', 'INSTALLATION']):
            return 'ASSEMBLY'
        elif any(keyword in text_upper for keyword in ['STANDARD', 'SPECIFIKATION', 'SPECIFICATION']):
            return 'STANDARDS'
        elif any(keyword in text_upper for keyword in ['PRODUKTGRUPP', 'PRODUCT GROUP', 'BESKRIVNING', 'DESCRIPTION']):
            return 'DESCRIPTION'
        elif any(keyword in text_upper for keyword in ['SÄKERHET', 'SAFETY', 'VARNING', 'WARNING']):
            return 'SAFETY'
        elif any(keyword in text_upper for keyword in ['TEKNISK', 'TECHNICAL', 'DATA']):
            return 'TECHNICAL'
        elif 'KAPITEL' in text_upper or 'CHAPTER' in text_upper:
            return 'INTRO'
        else:
            return 'OTHER'
    
    def save_knowledge(self, sections, category='UNKNOWN'):
        """
        Save extracted knowledge sections to database.
        
        Args:
            sections (list): List of section dictionaries
            category (str): Product category (e.g., 'PRESSKOPPLINGAR')
            
        Returns:
            int: Number of sections saved
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        saved_count = 0
        
        for section in sections:
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
                    self.pdf_name,
                    section['page_number'],
                    category,
                    section['section_type'],
                    section['title'],
                    section['content'].strip(),
                    'sv'  # Swedish
                ))
                saved_count += 1
            except Exception as e:
                print(f"⚠️  Warning: Could not save section: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def process_page(self, page_number, category='UNKNOWN'):
        """
        Process a single page and extract knowledge.
        
        Args:
            page_number (int): Page number to process
            category (str): Product category
            
        Returns:
            int: Number of sections extracted
        """
        print(f"\n📄 Processing page {page_number}...")
        
        # Extract page content
        page_info = self.extract_page_text(page_number)
        if not page_info:
            return 0
        
        # Identify sections
        sections = self.identify_sections(page_info)
        print(f"   Found {len(sections)} sections")
        
        # Save to database
        saved_count = self.save_knowledge(sections, category)
        print(f"   ✅ Saved {saved_count} sections")
        
        return saved_count
    
    def process_page_range(self, start_page, end_page, category='UNKNOWN'):
        """
        Process a range of pages.
        
        Args:
            start_page (int): Starting page number
            end_page (int): Ending page number
            category (str): Product category
            
        Returns:
            int: Total sections extracted
        """
        total_sections = 0
        
        for page_num in range(start_page, end_page + 1):
            count = self.process_page(page_num, category)
            total_sections += count
        
        return total_sections


def main():
    parser = argparse.ArgumentParser(
        description="Extract product knowledge from catalog pages"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF file"
    )
    parser.add_argument(
        "--pages",
        help="Page range (e.g., '167-169' or '5' or 'all')"
    )
    parser.add_argument(
        "--category",
        default="PRESSKOPPLINGAR",
        help="Product category (default: PRESSKOPPLINGAR)"
    )
    
    args = parser.parse_args()
    
    # Validate PDF exists
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Initialize extractor
    extractor = KnowledgeExtractor(pdf_path)
    
    # Determine page range
    if not args.pages or args.pages.lower() == 'all':
        # Process all pages
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()
        start_page, end_page = 1, total_pages
    elif '-' in args.pages:
        # Range: "167-169"
        start, end = args.pages.split('-')
        start_page, end_page = int(start), int(end)
    else:
        # Single page
        start_page = end_page = int(args.pages)
    
    print(f"\n🔍 Extracting knowledge from {pdf_path.name}")
    print(f"📖 Pages: {start_page} to {end_page}")
    print(f"📂 Category: {args.category}")
    
    # Process pages
    total_sections = extractor.process_page_range(start_page, end_page, args.category)
    
    print(f"\n✅ Extraction complete!")
    print(f"   Total sections extracted: {total_sections}")


if __name__ == "__main__":
    main()
