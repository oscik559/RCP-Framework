# Layer Experiments — Baseline Evaluation

This folder contains baseline experiments used to generate quantitative metrics for the paper (Sections 5.2–5.4).

## Structure

| Folder | Description | Status |
|--------|-------------|--------|
| `Baseline_RAG/` | Standard RAG pipeline (retrieve top-k → generate) | ✅ Ready |
| `Baseline_Agentic_No_RCP/` | Agentic pipeline without RCP persistence/validation | 🔲 Planned |

## Shared Resources

- **Test questions:** `../questions/test_questions_categorized.txt` (79 questions, 4 categories)
- **Product database:** `../database/harvested.db`
- **LLM:** `llama3.2:latest` via Ollama
- **Embeddings:** `embeddinggemma:latest` via Ollama

## Running

```bash
# Activate the project venv
.\.venv\Scripts\Activate.ps1

# Run RAG baseline evaluation
python Layer_Experiments/Baseline_RAG/evaluate_rag.py

# Run on a subset (first N questions)
python Layer_Experiments/Baseline_RAG/evaluate_rag.py --limit 5
```

## Metrics Collected

- Answer Correctness
- Citation Accuracy
- Unit Fidelity
- Hallucination Rate
- Per-query latency (seconds)
- Per-query token count
