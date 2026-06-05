# Revision Experiments (Reviewer 2)

Self-contained harness for the revision experiments, kept separate from the main
`Experiments/` tree so it can be reviewed and merged deliberately. It addresses
Reviewer 2's two empirical asks:

- **#1 Statistical rigour** — variance across repeated runs, bootstrap confidence
  intervals, McNemar significance, and inter-annotator agreement (Cohen's κ).
- **#2 Ablation** — a *no-gate* variant of the full loop that isolates the contribution
  of the validation layer.

> These scripts **build and smoke-test** the experiments; they do not themselves
> constitute the reported results. The author runs the full sweeps and interprets them.
> No numbers here are presented as findings.

## Files

| File | Task | What it does |
|------|------|--------------|
| `_stats.py` | shared | Wilson CI, McNemar χ², Newcombe paired-difference CI, percentile bootstrap, Cohen's κ (stdlib only). |
| `revision_runner.py` | 2 | Runs one Case I **B3** configuration (`full` / `no_gate`) at a chosen temperature; wraps the real controller + deterministic judge. |
| `run_variance.py` | 2 (↔ 8) | Repeats a configuration N times → per-metric **mean ± SD** + **bootstrap 95% CI** (10k) for correctness & hallucination. Tidy CSV + JSON. |
| `mcnemar_compare.py` | 3 | McNemar χ² + p + **Wilson/Newcombe 95% CI on the matched-proportion change** for any two matched result files (e.g. B3 vs B3⁻). |
| `make_grading_sheet.py` | 4a | Blind CSV grading sheet for a random, seeded subset of stored B3 outputs (original grade withheld). |
| `compute_kappa.py` | 4b | Cohen's κ + raw agreement from the completed sheet vs the original machine grades. |

## The no-gate ablation (B3⁻) — exact mechanism

The ablation is a single environment flag read by the controller's validation nodes:

```bash
RCP_DISABLE_VALIDATION=1   # gates OFF (B3⁻);  unset / =0 → gates ON (default, B3)
```

Implemented in `Layer_2_Agentic_Reasoning/logic/workflow_nodes.py` via
`validation_enabled()` (read at call time, so it can be toggled per run without
rebuilding the compiled graph). It makes the **three** validation gates pass-through:

| Gate | Node (function) | Behaviour when `RCP_DISABLE_VALIDATION=1` |
|------|------------------|--------------------------------------------|
| Function-level | `node_function_validate` | returns immediately with `functionValidated=True`; never flags the strategy for abort. |
| Strategy-level | `node_strategy_validate` | the `failed > 0 → abort` branch is skipped; the plan proceeds (success when nothing pending, else continue). |
| Goal-level | `node_goal_validate` | accepts the assembled answer without the LLM judge (no acceptance predicate, no retry). |

Retrieval, extraction, and synthesis are **unchanged**; only the gates and their
backtracking are removed. Model (`llama3.2:3b`), `harvested.db`, strategies, functions,
prompts, and embeddings (`qwen3-embedding:8b`) are identical to the shipped B3.

**Scope:** the flag lives in the Layer-2 controller, which is B3 for **Case I**. Case II's
B3 is a separate standalone pipeline
(`Experiments/Case_II/RCP_Framework/rcp_baseline_company_b.py`) and is *not* driven by
this flag — the no-gate ablation here is Case I only.

## Typical workflow

```bash
# 1) Variance (full system), 5 repeats at temperature 0, full 100-query set
python Experiments/Revision/run_variance.py --config full   --temperature 0.0 --repeats 5 --out Experiments/Revision/out

# 1b) Temperature sweep (stochasticity), e.g. 5 repeats at 0.7
python Experiments/Revision/run_variance.py --config full   --temperature 0.7 --repeats 5 --out Experiments/Revision/out

# 2) Ablation: same harness with gates off
python Experiments/Revision/run_variance.py --config no_gate --temperature 0.0 --repeats 5 --out Experiments/Revision/out

# 3) Significance of B3 vs B3- (e.g. one representative run of each)
python Experiments/Revision/mcnemar_compare.py \
    --a Experiments/Revision/out/run_full_t0.0_s0.json \
    --b Experiments/Revision/out/run_no_gate_t0.0_s0.json \
    --metric answer_correct --label-a B3 --label-b "B3- (no-gate)"

# 4) Inter-annotator agreement
python Experiments/Revision/make_grading_sheet.py \
    --results Experiments/Case_I/results/b3_rcp_latest.json \
              Experiments/Case_II/results/b3_rcp_latest.json \
    --n 40 --seed 20260602 --out Experiments/Revision/out/grading_sheet.csv
#   ... a second author fills the 'Correct (Y/N)' column ...
python Experiments/Revision/compute_kappa.py --sheet Experiments/Revision/out/grading_sheet.csv
```

## Notes / honest caveats

- **LLM seed is not pinned.** Ollama is left at its default sampling, so repeats at
  `temperature > 0` produce genuine variance (the point of the sweep). At `temperature 0`
  runs are near-deterministic modulo Ollama non-determinism. The `--seed` flag labels runs
  and seeds the bootstrap; it does not fix the generation seed.
- **Temperature override** is applied by mutating the in-memory `CONFIG` for this process
  (`revision_runner._set_temperature`); it does not edit `config.yaml`.
- **Bootstrap CI** resamples each run's per-query labels (default 10k draws) for correctness
  and hallucination; `run_variance.py` reports the run-0 CI plus the per-run CIs in JSON.
- **Newcombe method 10** is used for the matched-proportion-difference CI in
  `mcnemar_compare.py` (the Wilson-score interval generalised to paired proportions),
  matching the paper's significance-table CI column.
- Output artefacts are namespaced by `config/temperature/seed`; nothing is overwritten.
