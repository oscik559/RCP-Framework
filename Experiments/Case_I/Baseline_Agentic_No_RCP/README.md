# Agentic (No RCP) Baseline Experiment

This baseline evaluates a multi-step agentic loop (ReAct style) that can call tools but lacks the Relational Control Plane's (RCP) persistence, multi-stage validation, and structured state tracking.

## Pipeline Details

1.  **ReAct Loop**: Uses a standard reasoning-action loop where the LLM decides which tools to call sequentially.
2.  **Tools**: Accesses the `Layer_2_Agentic_Reasoning` function library adapted to the current database schema via shims.
3.  **No Persistence**: Intermediate thoughts, tool outputs, and validation states are kept in memory and lost after each query.
4.  **No Validation Gates**: Does not enforce schema or logic validation between steps; relies solely on the LLM's internal reasoning.

## Evaluation

Run the evaluation using:
```bash
python evaluate_agentic_no_rcp.py
```

Results demonstrate the "latency-instability paradox" where faster execution comes at the cost of significantly higher hallucination rates due to the lack of structured verification nodes.
