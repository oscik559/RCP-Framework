# RCP Framework Baseline (B3) — Case II (Saab)

This is the proposed system: the **RCP (Relational Control Plane)** reasoning engine adapted for Case II (Saab aerospace connector/cable catalog).

## Pipeline Details

The RCP implements the same 6-stage verify-then-summarise control loop as Case I:

1. **Goal Definition** — parse the query into a structured goal
2. **Strategy Selection** — choose a retrieval strategy (`SIMPLE LOOKUP`, `ENHANCED LOOKUP`, `MULTI-PRODUCT COMPARISON`)
3. **Function Execution** — execute an ordered function pipeline: `Extract Keywords` → `Normalize Keywords` → `Table Search` → `Filter Table` → `Analyze Data`
4. **Function Validation** — schema-level output verification per function
5. **Strategy Validation** — confidence gate; retry with `ENHANCED LOOKUP` if below threshold
6. **Goal Validation** — final synthesis with confidence scoring

## Evaluation

Run via the unified runner:
```bash
python Experiments/Case_II/run_evaluation_saab.py --baseline b3
```

Results are saved to `Experiments/Case_II/results/`.
