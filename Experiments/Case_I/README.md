# Layer Experiments — Baseline Evaluation (Appendix B)

This folder contains all baseline experiments used to generate the quantitative metrics reported in Sections 5.2–5.4 of the paper.

## Structure

```
Experiments/Case_I/
├── run_evaluation.py               # Unified runner: B1, B2, B3 (main entry point)
├── deterministic_judge.py          # Scoring logic (answer correctness, hallucination, etc.)
├── summarize_results.py            # Prints summary tables from saved JSON results
├── extract_costs.py                # Token/latency cost extraction helper
├── test_questions_appendix_b.json  # 65 annotated evaluation questions with strategy hints
│
├── Baseline_RAG/                   # B1: Naive RAG baseline
│   ├── rag_baseline.py             #   Pipeline implementation
│   └── evaluate_rag.py             #   Standalone runner (legacy)
│
├── Baseline_SQL_Retrieval/         # B2: SQL-backed Retrieval baseline
│   ├── sql_retrieval_baseline.py   #   Pipeline implementation
│   └── evaluate_sql_retrieval.py   #   Standalone runner (legacy)
│
├── Baseline_Agentic_No_RCP/        # Deprecated: replaced by B2 in final evaluation
│   └── ...
│
├── RCP_Framework/                  # B3 standalone runner (legacy)
│   └── evaluate_rcp.py
│
└── results_appendix_b/             # Saved evaluation outputs (JSON per run)
    ├── b1_rag_latest.json          #   Most recent B1 result
    ├── b2_sql_latest.json          #   Most recent B2 result
    └── b3_rcp_latest.json          #   Most recent B3 result (with forced strategies)
```

## Quick Start

```bash
# Activate project venv
.\.venv\Scripts\Activate.ps1

# Run all three baselines (65 questions)
python Experiments/Case_I/run_evaluation.py --baseline all

# Run individual baselines
python Experiments/Case_I/run_evaluation.py --baseline b1   # Naive RAG
python Experiments/Case_I/run_evaluation.py --baseline b2   # SQL Retrieval
python Experiments/Case_I/run_evaluation.py --baseline b3   # Full RCP (with forced strategies)

# Limit to first N questions (for quick testing)
python Experiments/Case_I/run_evaluation.py --baseline b3 --limit 5
```

## Test Questions (`test_questions_appendix_b.json`)

65 human-annotated queries covering two categories:

| Range | Type | Strategy |
|-------|------|----------|
| Q1–Q50 | Direct specification lookups and pairwise comparisons | `DIRECT SPECIFICATION LOOKUP` / `MULTI-PRODUCT COMPARISON` |
| Q51–Q65 | RCP-specific: contextual search, family-level queries, cross-series comparison | `CONTEXTUAL PRODUCT SEARCH` / `MULTI-PRODUCT COMPARISON` |

Each question includes a `"strategy"` field that tells B3 which RCP strategy to use directly, bypassing LLM strategy selection. This improves reproducibility and eliminates strategy-selection errors from the score.

## Evaluation Results (Final — 65 questions)

| Metric | B1: Naive RAG | B2: SQL Retrieval | B3: RCP (Proposed) |
|--------|:---:|:---:|:---:|
| Answer Correctness | 44.6% | 72.3% | **80.0%** |
| Citation Accuracy | 98.5% | 95.4% | 87.7% |
| Unit Fidelity | 72.3% | 92.3% | 87.7% |
| Hallucination Rate ↓ | 55.4% | 27.7% | **7.7%** |
| Avg. Latency (s) | 6.65 | 2.86 | 13.82 |

B3 achieves **90% answer correctness on Q1–Q50** with forced strategy selection.

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
| Product database | `../database/harvested.db` (1,628 products, 168 families) |
| Orchestration DB | `../database/agentic.db` |
| LLM | `llama3.2:latest` via Ollama (temperature 0.0) |
| Embeddings | `qwen3-embedding:8b` via Ollama |
