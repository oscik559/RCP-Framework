#!/usr/bin/env python3
"""
Test VLM with generate API instead of chat API
"""
import fitz
import requests
import base64
import json
from io import BytesIO
from PIL import Image
from pathlib import Path


def test_generate_api():
    """Test with generate API"""
    
    print("=== Testing VLM with Generate API ===\n")
    
    # Open PDF and get table crop
    pdf_path = Path("Layer_1-Extraction_b/Press_Couplings.pdf")
    doc = fitz.open(pdf_path)
    page = doc.load_page(4)  # Page 5
    
    table_bbox = (71.20, 132.89, 289.47, 189.50)
    
    # Render table
    zoom = 300 / 72.0
    mat = fitz.Matrix(zoom, zoom)
    padding = 10
    table_rect = fitz.Rect(
        max(0, table_bbox[0] - padding),
        max(0, table_bbox[1] - padding),
        min(page.rect.width, table_bbox[2] + padding),
        min(page.rect.height, table_bbox[3] + padding)
    )
    
    pix = page.get_pixmap(matrix=mat, clip=table_rect)
    img_data = pix.tobytes("png")
    table_image = Image.open(BytesIO(img_data))
    
    # Convert to base64
    buffer = BytesIO()
    table_image.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    print(f"✅ Image ready: {table_image.size}")
    
    # Test generate API
    api_url = "http://localhost:11434/api/generate"
    
    prompt = """Extract the table text and return as JSON array."""
    
    payload = {
        "model": "qwen3-vl:235b-cloud",
        "prompt": prompt,
        "images": [img_base64],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    
    print(f"\n📡 Trying generate API: {api_url}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        
        print(f"📥 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response keys: {result.keys()}")
            
            content = result.get('response', '')
            print(f"\n📝 Content ({len(content)} chars):")
            print("-" * 80)
            print(content)
            print("-" * 80)
            
        else:
            print(f"❌ Failed: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        doc.close()


if __name__ == "__main__":
    test_generate_api()
