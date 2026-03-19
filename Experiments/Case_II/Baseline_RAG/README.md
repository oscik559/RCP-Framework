# RAG Baseline (B1) — Case II (Saab)

This baseline implements a standard Retrieval-Augmented Generation (RAG) pipeline over the Saab document corpus (451 tables from 54 PDFs extracted into `harvested.db`).

## Pipeline Details

1. **Data Loading**: Ingests extracted table data from `harvested.db`.
2. **Indexing**: Chunks text and generates embeddings using `qwen3-embedding:latest` via Ollama.
3. **Retrieval**: Performs dense vector search using ChromaDB to retrieve the top-k relevant chunks.
4. **Generation**: Augments the prompt with retrieved context and generates an answer using `llama3.2:latest`.

> **Note:** Building the embedding index takes ~18 min on first run. The index is cached for subsequent questions in the same run.

## Evaluation

Run via the unified runner:
```bash
python Experiments/Case_II/run_evaluation_saab.py --baseline b1
```

Results are saved to `Experiments/Case_II/results/`.
