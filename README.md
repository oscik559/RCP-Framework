# Project_Hydroscand-Hoses

Extract product information from PDF specification sheets using Vision Language Models.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running with a vision model:
```bash
# Install Ollama if not already installed
# Download and run a vision model
ollama pull qwen2-vl
ollama serve
```

## Usage

Extract products from a specific PDF page:
```bash
python extract_product.py PDF/Produktbok.pdf --page 31
```

Options:
- `--page N`: Extract from page N (default: 31)
- `--ollama-url URL`: Ollama API URL (default: http://localhost:11434)
- `--model NAME`: VLM model name (default: qwen2-vl)

## Output

- **Database**: `data/products.db` - SQLite database with extracted product data
- **Visualization**: `output/Produktbok_page_031_boxes.png` - Image with bounding boxes
- **Console**: JSON output of extracted products

## Database Schema

### products table
- id (PRIMARY KEY)
- product_code (UNIQUE)
- name
- category  
- page_number
- raw_text
- created_at

### specs table
- id (PRIMARY KEY)
- product_id (FOREIGN KEY)
- spec_key
- spec_value
- unit

## Troubleshooting

**Connection refused**: Make sure Ollama is running (`ollama serve`)
**No model**: Pull a vision model first (`ollama pull qwen2-vl`)
**No products extracted**: Check that the page contains product specification tables