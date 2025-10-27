#!/usr/bin/env python3
"""
PDF to PNG Converter using PyMuPDF

This script converts PDF pages to PNG images and saves them in the data/pages directory.
PDFs are read from the PDF folder.
Uses PyMuPDF (fitz) which doesn't require external dependencies like Poppler.
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
import argparse


def create_output_directory():
    """Create the output directory if it doesn't exist."""
    output_dir = Path("data/pages")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_pdf_files():
    """Get all PDF files from the PDF directory."""
    pdf_dir = Path("PDF")
    if not pdf_dir.exists():
        print("Error: PDF directory not found!")
        return []
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    return pdf_files


def convert_pdf_to_png(pdf_path, output_dir, dpi=300):
    """
    Convert a PDF file to PNG images using PyMuPDF.
    
    Args:
        pdf_path (Path): Path to the PDF file
        output_dir (Path): Directory to save PNG images
        dpi (int): DPI for the output images (default: 300)
    """
    try:
        print(f"Converting {pdf_path.name}...")
        
        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Convert each page to PNG
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
            output_filename = f"{pdf_name}_page_{page_num + 1:03d}.png"
            output_path = output_dir / output_filename
            
            pix.save(str(output_path))
            print(f"  Saved: {output_filename}")
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
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG images")
    parser.add_argument("--dpi", type=int, default=300, 
                       help="DPI for output images (default: 300)")
    parser.add_argument("--pdf", type=str, 
                       help="Convert specific PDF file (optional)")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = create_output_directory()
    print(f"Output directory: {output_dir.absolute()}")
    
    # Get PDF files to process
    if args.pdf:
        pdf_path = Path("PDF") / args.pdf
        if not pdf_path.exists():
            print(f"Error: PDF file '{args.pdf}' not found in PDF directory!")
            sys.exit(1)
        pdf_files = [pdf_path]
    else:
        pdf_files = get_pdf_files()
    
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
        pages_converted = convert_pdf_to_png(pdf_file, output_dir, args.dpi)
        if pages_converted > 0:
            successful_conversions += 1
            total_pages += pages_converted
    
    # Summary
    print(f"\nConversion complete!")
    print(f"Successfully converted {successful_conversions}/{len(pdf_files)} PDF files")
    print(f"Total pages converted: {total_pages}")
    print(f"Images saved in: {output_dir.absolute()}")


if __name__ == "__main__":
    main()