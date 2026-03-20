# Layer 1 Extraction — Case II (Company B)

## Overview

This folder corresponds to the Layer 1 extraction pipeline for **Case II**, which operates over a corpus of aerospace connector and cable specification documents provided by **Company B**.

The extraction pipeline follows the same architecture as Case I (`Layer_1_Extraction/Case_I/`):

```
PDF Catalog(s)
    ↓
PDF → PNG (page rendering)
    ↓
VLM-based Table & Specification Extraction
    ↓
Hierarchical SQLite Database (harvested.db)
```

## Data Confidentiality

> **The source PDFs, extracted databases, and intermediate data for Case II are not included in this repository.**
>
> The Company B document corpus contains proprietary aerospace connector and cable specifications and is subject to a non-disclosure agreement. Access to the raw data must be arranged directly with Company B.

The evaluation questions and aggregated results that do not expose proprietary content are available in [`Experiments/Case_II/`](../../Experiments/Case_II/).

## Extraction Pipeline

The same scripts used in Case I apply here. To run extraction on the Company B corpus (requires access to the source PDFs and appropriate permissions):

```bash
# Initialize the database
python database/db_utils.py --init

# Run the production extraction pipeline
python Layer_1_Extraction/Case_I/Layer_1b/0_extract_knowledge.py
python Layer_1_Extraction/Case_I/Layer_1b/1_pdf_to_png.py
python Layer_1_Extraction/Case_I/Layer_1b/2b_extract_categories.py
python Layer_1_Extraction/Case_I/Layer_1b/3a_extract_families.py
python Layer_1_Extraction/Case_I/Layer_1b/3b_extract_products_vlm.py
```

Requires Ollama running locally with a vision model (e.g., `qwen2-vl`).

## Case II at a Glance

| Attribute | Value |
|-----------|-------|
| Domain | Aerospace connectors and cables |
| Source | Company B internal specification documents |
| Corpus size | 54 PDFs, 451 extracted tables |
| Database | `harvested.db` (not included — confidential) |
| Evaluation set | 100 annotated queries (`Experiments/Case_II/test_questions_company_b.json`) |
| LLM | `llama3.2:latest` via Ollama (temperature 0.0) |
| Embeddings | `qwen3-embedding:latest` via Ollama |

## Contact

For questions about Case II data access, contact the authors via the paper's corresponding author or open an issue on [GitHub](https://github.com/oscik559/RCP-Framework/issues).
