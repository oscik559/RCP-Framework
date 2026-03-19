#!/usr/bin/env python3
"""
PDF to PNG Converter and Page Extractor using PyMuPDF

This script converts PDF pages to PNG images and extracts individual PDF pages.
- PNG images are saved in data/png_pages directory
- Individual PDF pages are saved in data/pdf_pages directory
PDFs are read from the PDF folder.
Uses PyMuPDF (fitz) which doesn't require external dependencies like Poppler.
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
import argparse


def get_script_dir():
    """Get the directory where this script is located."""
    return Path(__file__).parent


def create_output_directories():
    """Create the output directories if they don't exist."""
    script_dir = get_script_dir()
    png_output_dir = script_dir / "data/png_pages"
    pdf_output_dir = script_dir / "data/pdf_pages"
    
    png_output_dir.mkdir(parents=True, exist_ok=True)
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    return png_output_dir, pdf_output_dir


def get_pdf_files():
    """Get all PDF files from the PDF directory."""
    pdf_dir = Path("PDF")
    if not pdf_dir.exists():
        print("Error: PDF directory not found!")
        return []
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    return pdf_files


def convert_pdf_to_png_and_pages(pdf_path, png_output_dir, pdf_output_dir, dpi=300):
    """
    Convert a PDF file to PNG images and extract individual PDF pages using PyMuPDF.
    
    Args:
        pdf_path (Path): Path to the PDF file
        png_output_dir (Path): Directory to save PNG images
        pdf_output_dir (Path): Directory to save individual PDF pages
        dpi (int): DPI for the output images (default: 300)
    """
    try:
        print(f"Converting {pdf_path.name}...")
        
        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Convert each page to PNG and extract as individual PDF
        pdf_name = pdf_path.stem  # filename without extension
        pages_converted = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Calculate zoom factor based on desired DPI
            # Default DPI in PyMuPDF is 72, so zoom = desired_dpi / 72
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Save as PNG
            png_filename = f"{pdf_name}_page_{page_num + 1:03d}.png"
            png_path = png_output_dir / png_filename
            
            pix.save(str(png_path))
            print(f"  Saved PNG: {png_filename}")
            
            # Extract individual PDF page
            pdf_filename = f"{pdf_name}_page_{page_num + 1:03d}.pdf"
            pdf_page_path = pdf_output_dir / pdf_filename
            
            # Create a new PDF document with just this page
            new_doc = fitz.open()  # Create empty document
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            new_doc.save(str(pdf_page_path))
            new_doc.close()
            
            print(f"  Saved PDF: {pdf_filename}")
            pages_converted += 1
        
        # Close the document
        doc.close()
        
        print(f"Successfully converted {pages_converted} pages from {pdf_path.name}")
        return pages_converted
        
    except Exception as e:
        print(f"Error converting {pdf_path.name}: {str(e)}")
        return 0


def main():
    """Main function to convert all PDFs to PNG images."""
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG images and extract individual PDF pages")
    parser.add_argument("--dpi", type=int, default=300, 
                       help="DPI for output images (default: 300)")
    parser.add_argument("--pdf", type=str, default="Press_Couplings.pdf",
                       help="PDF file to convert (default: Press_Couplings.pdf)")
    
    args = parser.parse_args()
    
    # Create output directories
    png_output_dir, pdf_output_dir = create_output_directories()
    print(f"PNG output directory: {png_output_dir.absolute()}")
    print(f"PDF output directory: {pdf_output_dir.absolute()}")
    
    # Get script directory for finding PDF files
    script_dir = get_script_dir()
    
    # Get PDF file path - look in multiple locations
    pdf_path = None
    search_paths = [
        script_dir / args.pdf,                    # Layer_1_Extraction/Layer_1b/Press_Couplings.pdf
        script_dir / "PDF" / args.pdf,            # Layer_1_Extraction/Layer_1b/PDF/Press_Couplings.pdf
        script_dir.parent / "PDF" / args.pdf,     # Project_Hydroscand-Hoses/PDF/Press_Couplings.pdf
        Path(args.pdf),                           # Current working directory
    ]
    
    for path in search_paths:
        if path.exists():
            pdf_path = path
            break
    
    if pdf_path is None:
        print(f"Error: PDF file '{args.pdf}' not found!")
        print("Searched in:")
        for path in search_paths:
            print(f"  - {path.absolute()}")
        sys.exit(1)
    
    pdf_files = [pdf_path]
    
    if not pdf_files:
        print("No PDF files found in the PDF directory!")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s) to convert:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    # Convert each PDF
    total_pages = 0
    successful_conversions = 0
    
    for pdf_file in pdf_files:
        pages_converted = convert_pdf_to_png_and_pages(pdf_file, png_output_dir, pdf_output_dir, args.dpi)
        if pages_converted > 0:
            successful_conversions += 1
            total_pages += pages_converted
    
    # Summary
    print(f"\nConversion complete!")
    print(f"Successfully converted {successful_conversions}/{len(pdf_files)} PDF files")
    print(f"Total pages converted: {total_pages}")
    print(f"PNG images saved in: {png_output_dir.absolute()}")
    print(f"PDF pages saved in: {pdf_output_dir.absolute()}")


if __name__ == "__main__":
    main()