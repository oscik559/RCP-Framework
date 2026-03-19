# Experiments — Case II: Saab Aerospace Documentation

This folder contains the baseline experiments for **Case II (Saab AB)** reported in the paper ($n = 100$ queries). All three baselines operate over the same extracted document corpus (`harvested.db`, 451 tables from 54 revision-controlled aerospace PDFs) using local models only (Ollama).

## Structure

```
Experiments/Case_II/
├── run_evaluation_saab.py          # Unified runner: B1, B2, B3 (main entry point)
├── deterministic_judge_saab.py     # Scoring logic (correctness, hallucination, etc.)
├── summarize_results.py            # Prints summary tables from saved JSON results
├── extract_costs.py                # Token/latency cost extraction helper
├── compute_mcnemar.py              # McNemar's test for statistical significance
├── test_questions_saab.json        # 100 annotated evaluation questions
│
├── Baseline_RAG/                   # B1: Naive RAG baseline
│   ├── rag_baseline_saab.py        #   Pipeline implementation
│   └── results/
│
├── Baseline_SQL_Retrieval/         # B2: SQL-backed retrieval baseline
│   ├── sql_retrieval_saab.py       #   Pipeline implementation
│   └── results/
│
├── RCP_Framework/                  # B3: RCP framework
│   ├── rcp_baseline_saab.py        #   Pipeline implementation
│   └── results/
│
└── results/                        # Consolidated evaluation outputs (JSON per run)
    ├── b1_rag_latest.json
    ├── b2_sql_latest.json
    └── b3_rcp_latest.json
```

## Quick Start

```bash
# Run all three baselines (100 questions)
python Experiments/Case_II/run_evaluation_saab.py --baseline all

# Run individual baselines
python Experiments/Case_II/run_evaluation_saab.py --baseline b1   # Naive RAG
python Experiments/Case_II/run_evaluation_saab.py --baseline b2   # SQL Retrieval
python Experiments/Case_II/run_evaluation_saab.py --baseline b3   # Full RCP

# Limit to first N questions (for quick testing)
python Experiments/Case_II/run_evaluation_saab.py --baseline b3 --limit 5
```

> **Note:** B1 builds a 451-chunk embedding index on first run (~18 min with `qwen3-embedding:latest`). Subsequent questions in the same run use the cached index.

## Test Questions (`test_questions_saab.json`)

100 human-annotated queries covering connector and cable products from the Saab document corpus (connector families: RPT, RNT, TFR, C0-series). Each question includes a `"strategy"` field used by B3 to bypass LLM strategy selection, improving reproducibility.

## Evaluation Results (Final — $n = 100$ queries)

| Metric | B1: Naive RAG | B2: SQL Retrieval | B3: RCP (Proposed) |
|--------|:---:|:---:|:---:|
| Answer Correctness (%) | 23.0 | 76.0 | **81.0** |
| Citation Accuracy (%) | 33.0 | 59.0 | **78.0** |
| Unit Fidelity (%) | 100.0 | 100.0 | 100.0 |
| Hallucination Rate (%) ↓ | 47.0 | 12.0 | **11.0** |
| Avg. Latency (s) | 5.25 | 2.55 | 12.84 |

B1→B3 correctness improvement: +58 pp ($p < 0.001$, McNemar's test).
B1→B2 correctness improvement: +53 pp ($p < 0.001$).
B2→B3 correctness improvement: +5 pp ($p = 0.359$, not significant).

## Shared Resources

| Resource | Path |
|----------|------|
| Document corpus | `database/saab_harvested.db` (451 tables, 54 PDFs) — set `SAAB_DB_PATH` env var to override |
| Orchestration DB | `database/agentic.db` |
| LLM | `llama3.2:latest` (8B) via Ollama, temperature 0.0 |
| Embeddings | `qwen3-embedding:latest` via Ollama |

## B3 RCP Control Loop

The local RCP implements the same 6-stage architecture as Case I:

1. **GoalDefine** — parse query into structured goal
2. **StrategyPlan** — select SIMPLE LOOKUP / ENHANCED LOOKUP / MULTI-PRODUCT COMPARISON
3. **FunctionExecute** — run ordered function pipeline: `Extract Keywords` → `Normalize Keywords` → `Table Search` → `Filter Table` → `Analyze Data`
4. **FunctionValidate** — schema-level output verification
5. **StrategyValidate** — confidence gate; retry with ENHANCED LOOKUP if below threshold
6. **GoalValidate** — final synthesis with confidence scoring
