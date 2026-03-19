# SQL Retrieval Baseline (B2)

This baseline implements a structured SQL retrieval pipeline that queries `harvested.db` directly, without agentic reasoning or vector search.

## Pipeline Details

1. **Query parsing**: Extracts keywords and numeric filters from the natural-language query.
2. **SQL retrieval**: Executes structured queries against the `products` and `product_families` tables using exact and fuzzy matching.
3. **Generation**: Formats the retrieved rows into a prompt and generates an answer using `llama3.2:latest`.

## Evaluation

Run via the unified runner:
```bash
python Experiments/Case_I/run_evaluation.py --baseline b2
```

Or with the standalone script:
```bash
python Experiments/Case_I/Baseline_SQL_Retrieval/evaluate_sql_retrieval.py
```

Results are saved to `Experiments/Case_I/results/`.
