# Layer Experiments Saab — Case II Baseline Evaluation

This folder contains the baseline experiments for **Case II (Saab)** reported in Sections 5.5–5.7 of the paper. All three baselines operate over the same extracted document corpus (`harvested.db`, 451 tables from 54 PDFs) using local models only (Ollama).

## Structure

```
Layer_Experiments_Saab/
├── run_evaluation_saab.py       # Unified runner: B1, B2, B3
├── rag_baseline_saab.py         # B1: Naive RAG (Ollama embeddings + llama3.2)
├── sql_retrieval_saab.py        # B2: SQL-backed retrieval on extracted_tables
├── rcp_baseline_saab.py         # B3: Local RCP (6-stage control loop, llama3.2)
├── deterministic_judge_saab.py  # Scoring logic (correctness, hallucination, etc.)
├── test_questions_saab.json     # 30 annotated evaluation questions
└── results/                     # Saved evaluation outputs (JSON per run)
    ├── b1_rag_latest.json
    ├── b2_sql_latest.json
    └── b3_rcp_latest.json
```

## Quick Start

```bash
# Activate project venv
.\.venv\Scripts\Activate.ps1

# Run all three baselines (30 questions)
python -m Layer_Experiments_Saab.run_evaluation_saab --baseline all

# Run individual baselines
python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b1   # Naive RAG
python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b2   # SQL Retrieval
python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b3   # Full RCP

# Limit to first N questions (for quick testing)
python -m Layer_Experiments_Saab.run_evaluation_saab --baseline b3 --limit 5
```

> **Note:** B1 builds a 451-chunk embedding index on first run (~18 min with qwen3-embedding:latest). Subsequent questions in the same run use the cached index.

## Evaluation Results (Final — 30 questions)

| Metric | B1: Naive RAG | B2: SQL Retrieval | B3: RCP (Proposed) |
|--------|:---:|:---:|:---:|
| Answer Correctness | 40.0% | 60.0% | **76.7%** |
| Citation Accuracy | 50.0% | 53.3% | **73.3%** |
| Unit Fidelity | 100% | 100% | **100%** |
| Hallucination Rate ↓ | 20.0% | 20.0% | **16.7%** |
| Avg. Latency (s) | 8.65 | 2.55 | 4.98 |

B1→B3 improvement: p=0.022 (McNemar's test, statistically significant).

## Test Questions (`test_questions_saab.json`)

30 human-annotated queries covering connector and cable products from the Saab document corpus:

| Range  | Type                        | Products                          |
|--------|-----------------------------|-----------------------------------|
| Q1–Q5  | Backshell C0000268 specs    | Shell size, plating, cable entry  |
| Q6–Q10 | RPT2356 connector dims      | ø A, M, L, N, thread              |
| Q11–Q15| TFR46310 cable specs        | Jacket ø, conductors, temp range  |
| Q16–Q20| TFR46320 cable specs + comp | Temp range, jacket ø, resistance  |
| Q21–Q25| RNT2240 connector dims      | R1, S, Z, metric thread           |
| Q26–Q30| Mixed (RPT2346, RNT2240,    | MIL-designation, panel cutout,    |
|        | RPT81381)                   | rated current, operating voltage  |

Each question includes a `"strategy"` field used by B3 to bypass LLM strategy selection, improving reproducibility.

## Shared Resources

| Resource         | Path                                                                |
|------------------|---------------------------------------------------------------------|
| Document corpus  | `..\..\..\Test_Projects_DELETE\Project_Saab_fork\Project_Saab\data\database\harvested.db` |
| LLM              | `llama3.2:latest` via Ollama (temperature 0.0)                     |
| Embeddings       | `qwen3-embedding:latest` via Ollama                                |

## B3 RCP Control Loop

The local RCP implements the same 6-stage architecture as Case I:

1. **GoalDefine** — parse query into structured goal
2. **StrategyPlan** — select SIMPLE LOOKUP / ENHANCED LOOKUP / MULTI-PRODUCT COMPARISON
3. **FunctionExecute** — run ordered function pipeline
4. **FunctionValidate** — schema-level output verification
5. **StrategyValidate** — confidence gate; retry with ENHANCED LOOKUP if below threshold
6. **GoalValidate** — final synthesis with confidence scoring

Functions: `Extract Keywords` → `Normalize Keywords` → `Table Search` → `Filter Table` → `Analyze Data`
