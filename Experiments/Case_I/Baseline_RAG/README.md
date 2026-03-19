# RAG Baseline Experiment

This baseline implements a standard Retrieval-Augmented Generation (RAG) pipeline for evaluating the performance of document retrieval and answer generation without agentic reasoning or persistent state.

## Pipeline Details

1.  **Data Loading**: Ingests product families, descriptions, and knowledge assets from `harvested.db`.
2.  **Indexing**: Chunks text and generates embeddings using `embeddinggemma:latest`.
3.  **Retrieval**: Performs dense vector search using ChromaDB to retrieve the top-k relevant chunks.
4.  **Generation**: Augments the prompt with retrieved context and generates an answer using `llama3.2:latest`.

## Evaluation

Run the evaluation using:
```bash
python evaluate_rag.py
```

Results are stored in the `results/` directory as JSON (per-query details) and CSV (summary metrics).
