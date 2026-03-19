# Experiments — Case I: Hydroscand Hydraulic Products Catalogue

This folder contains all baseline experiments used to generate the quantitative metrics reported in the paper (Case I, $n = 100$ queries).

## Structure

```
Experiments/Case_I/
├── run_evaluation.py               # Unified runner: B1, B2, B3 (main entry point)
├── deterministic_judge.py          # Scoring logic (answer correctness, hallucination, etc.)
├── summarize_results.py            # Prints summary tables from saved JSON results
├── extract_costs.py                # Token/latency cost extraction helper
├── compute_mcnemar.py              # McNemar's test for statistical significance
├── test_questions.json             # 100 annotated evaluation questions with strategy hints
│
├── Baseline_RAG/                   # B1: Naive RAG baseline
│   ├── rag_baseline.py             #   Pipeline implementation
│   └── evaluate_rag.py             #   Standalone runner (legacy)
│
├── Baseline_SQL_Retrieval/         # B2: SQL-backed Retrieval baseline
│   ├── sql_retrieval_baseline.py   #   Pipeline implementation
│   └── evaluate_sql_retrieval.py   #   Standalone runner (legacy)
│
├── RCP_Framework/                  # B3: RCP framework
│   └── evaluate_rcp.py             #   Standalone runner (legacy)
│
└── results/                        # Saved evaluation outputs (JSON per run)
    ├── b1_rag_latest.json
    ├── b2_sql_latest.json
    └── b3_rcp_latest.json
```

## Quick Start

```bash
# Run all three baselines (100 questions)
python Experiments/Case_I/run_evaluation.py --baseline all

# Run individual baselines
python Experiments/Case_I/run_evaluation.py --baseline b1   # Naive RAG
python Experiments/Case_I/run_evaluation.py --baseline b2   # SQL Retrieval
python Experiments/Case_I/run_evaluation.py --baseline b3   # RCP (with forced strategies)

# Limit to first N questions (for quick testing)
python Experiments/Case_I/run_evaluation.py --baseline b3 --limit 5
```

## Test Questions (`test_questions.json`)

100 human-annotated queries covering:

| Range | Type | Strategy |
|-------|------|----------|
| Q1–Q70 | Direct specification lookups and pairwise comparisons | `DIRECT SPECIFICATION LOOKUP` / `MULTI-PRODUCT COMPARISON` |
| Q71–Q100 | Contextual search, family-level queries, cross-series comparison | `CONTEXTUAL PRODUCT SEARCH` / `MULTI-PRODUCT COMPARISON` |

Each question includes a `"strategy"` field that tells B3 which RCP strategy to use directly, bypassing LLM strategy selection. This improves reproducibility and eliminates strategy-selection errors from the score.

## Evaluation Results (Final — $n = 100$ queries)

| Metric | B1: Naive RAG | B2: SQL Retrieval | B3: RCP (Proposed) |
|--------|:---:|:---:|:---:|
| Answer Correctness (%) | 45.0 | 73.0 | **85.0** |
| Citation Accuracy (%) | **99.0** | 93.0 | 90.0 |
| Unit Fidelity (%) | 67.0 | **93.0** | 92.0 |
| Hallucination Rate (%) ↓ | 55.0 | 26.0 | **5.0** |
| Avg. Latency (s) | 12.24 | 0.48 | 13.65 |

B1→B3 correctness improvement: +40 pp ($\chi^2 = 34.57$, $p < 0.001$, McNemar's test).
B2→B3 correctness improvement: +12 pp ($\chi^2 = 4.65$, $p = 0.031$).
B2→B3 hallucination reduction: −21 pp ($p < 0.001$).

## Deterministic Judge (`deterministic_judge.py`)

Scores answers without an LLM judge by:
- Extracting numeric values from both the ground truth and the answer
- Handling Swedish fraction notation: `3,8"` = `3/8"` = `0.375`
- Checking article number citation from the question
- Verifying unit usage (MPa, mm, kg/m, inches)
- Flagging hallucination when the answer contains numbers not present in ground truth

## Shared Resources

| Resource | Path |
|----------|------|
| Product database | `database/harvested.db` (1,628 products, 168 families) |
| Orchestration DB | `database/agentic.db` |
| LLM | `llama3.2:latest` (8B) via Ollama, temperature 0.0 |
| Embeddings | `qwen3-embedding:latest` via Ollama |
