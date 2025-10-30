#!/usr/bin/env python3
"""
Test script for qwen3-vl:4b model with table image analysis
"""

import requests
import base64
from PIL import Image
import io
import json

def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def test_qwen_4b_with_table():
    """Test qwen3-vl:4b model with a sample table image"""
    
    # Create a simple table-like image for testing (since I can't access the attachment directly)
    # In practice, you would load your actual image here
    print("Creating test table image...")
    
    # For now, create a simple test image
    # You can replace this with: img = Image.open("your_table_image.png")
    img = Image.new('RGB', (600, 200), color='white')
    
    # Convert to base64
    img_base64 = image_to_base64(img)
    
    # Create the prompt for table analysis
    prompt = """Analyze this table image and extract the product information. 
    
Please identify:
1. Column headers
2. Product codes/article numbers
3. Technical specifications for each product
4. Any other relevant data

Return the information in a structured format."""

    payload = {
        'model': 'qwen3-vl:4b',
        'messages': [{
            'role': 'user',
            'content': prompt,
            'images': [img_base64]
        }],
        'stream': False
    }

    try:
        print("🤖 Calling qwen3-vl:4b model...")
        response = requests.post(
            'http://localhost:11434/api/chat', 
            json=payload, 
            timeout=180  # 3 minutes timeout
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['message']['content']
            print("✅ Model Response:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (3 minutes)")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing qwen3-vl:4b model with table analysis...")
    success = test_qwen_4b_with_table()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")