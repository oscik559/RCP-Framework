#!/usr/bin/env python3
"""
Test VLM independently to diagnose issues
"""
import fitz  # PyMuPDF
import requests
import base64
import json
from io import BytesIO
from PIL import Image
from pathlib import Path


def test_vlm_simple():
    """Test VLM with a simple table crop from page 5"""
    
    print("=== Testing VLM Independently ===\n")
    
    # Open PDF
    pdf_path = Path("Layer_1-Extraction_b/Press_Couplings.pdf")
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"✅ Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    page = doc.load_page(4)  # Page 5 (0-indexed)
    
    print(f"✅ Loaded page 5")
    print(f"   Page size: {page.rect.width} x {page.rect.height}")
    
    # Use the first detected table bbox from earlier output
    # "Detected Table 1 at (71.20154370759663, 132.88548278808594, 289.4734353824538, 189.49542236328125)"
    table_bbox = (71.20, 132.89, 289.47, 189.50)
    
    print(f"✅ Table bbox: {table_bbox}")
    
    # Render table area to image
    zoom = 300 / 72.0  # 300 DPI
    mat = fitz.Matrix(zoom, zoom)
    
    padding = 10
    table_rect = fitz.Rect(
        max(0, table_bbox[0] - padding),
        max(0, table_bbox[1] - padding),
        min(page.rect.width, table_bbox[2] + padding),
        min(page.rect.height, table_bbox[3] + padding)
    )
    
    print(f"✅ Rendering table area...")
    pix = page.get_pixmap(matrix=mat, clip=table_rect)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    table_image = Image.open(BytesIO(img_data))
    
    print(f"✅ Image created: {table_image.size}")
    
    # Save test image for inspection
    test_img_path = Path("test_table_crop.png")
    table_image.save(test_img_path)
    print(f"✅ Saved test image: {test_img_path}")
    
    # Convert to base64
    buffer = BytesIO()
    table_image.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    print(f"✅ Base64 encoded: {len(img_base64)} chars")
    
    # Test Ollama connection
    print("\n=== Testing Ollama Connection ===")
    
    # Test chat API
    api_url = "http://localhost:11434/api/chat"
    
    prompt = """Look at this table and extract the text. Return as JSON array of arrays.
Example: [["Header1", "Header2"], ["Row1Col1", "Row1Col2"]]"""
    
    payload = {
        "model": "qwen3-vl:235b-cloud",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [img_base64]
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2000
        }
    }
    
    print(f"\n📡 Sending request to {api_url}...")
    print(f"   Model: qwen3-vl:235b-cloud")
    print(f"   Prompt: {prompt[:100]}...")
    
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"\nResponse keys: {result.keys()}")
            
            if 'message' in result:
                content = result['message'].get('content', '')
                print(f"\n📝 Content length: {len(content)} chars")
                print(f"\n📝 Content preview:")
                print("-" * 80)
                print(content[:500])
                print("-" * 80)
                
                # Try to parse as JSON
                try:
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    content = content.strip()
                    
                    table_data = json.loads(content)
                    print(f"\n✅ JSON parsed successfully!")
                    print(f"   Rows: {len(table_data)}")
                    print(f"   Columns: {len(table_data[0]) if table_data else 0}")
                    print(f"\n📊 Table data:")
                    for i, row in enumerate(table_data[:3]):
                        print(f"   Row {i}: {row}")
                    
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON parse error: {e}")
                    print(f"   Content: {content[:200]}")
            else:
                print(f"❌ No 'message' in response")
                print(f"Full response: {result}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - is Ollama running?")
        print(f"   Try: ollama serve")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        doc.close()
        print(f"\n✅ Closed PDF")


if __name__ == "__main__":
    test_vlm_simple()
