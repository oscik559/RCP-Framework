# RCP Framework Baseline (B3)

This is the proposed system: the full **RCP (Relational Control Plane)** reasoning engine applied to Case I (Hydroscand).

## Pipeline Details

The RCP implements a 6-stage verify-then-summarise control loop:

1. **Goal Definition** — parse the query into a structured goal
2. **Strategy Selection** — choose a retrieval strategy (e.g. `DIRECT SPECIFICATION LOOKUP`, `CONTEXTUAL PRODUCT SEARCH`, `MULTI-PRODUCT COMPARISON`)
3. **Function Execution** — execute an ordered function pipeline against `harvested.db`
4. **Function Validation** — schema-level output verification per function
5. **Strategy Validation** — confidence gate; retry with a stronger strategy if below threshold
6. **Goal Validation** — final synthesis with citation and confidence scoring

Synthesis is only permitted after retrieved evidence satisfies all validation constraints, transforming potential hallucinations into explicit, auditable failures.

## Evaluation

Run via the unified runner:
```bash
python Experiments/Case_I/run_evaluation.py --baseline b3
```

Or with the standalone script:
```bash
python Experiments/Case_I/RCP_Framework/evaluate_rcp.py
```

Results are saved to `Experiments/Case_I/results/`.
