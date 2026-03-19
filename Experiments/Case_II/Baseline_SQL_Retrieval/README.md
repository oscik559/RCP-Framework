# SQL Retrieval Baseline (B2) — Case II (Saab)

This baseline implements structured SQL retrieval over the `extracted_tables` in `harvested.db`, without agentic reasoning or vector search.

## Pipeline Details

1. **Query parsing**: Extracts product codes, keywords, and numeric filters from the natural-language query.
2. **SQL retrieval**: Executes structured queries against the extracted table rows using exact and fuzzy matching.
3. **Generation**: Formats the retrieved rows into a prompt and generates an answer using `llama3.2:latest`.

## Evaluation

Run via the unified runner:
```bash
python Experiments/Case_II/run_evaluation_saab.py --baseline b2
```

Results are saved to `Experiments/Case_II/results/`.
