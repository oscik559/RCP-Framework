"""Smoke-test the L2 notebook by extracting and running its code cells, skipping LLM/Chroma calls."""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

nb = json.load(open(HERE / "02_agentic_reasoning.ipynb", encoding="utf-8"))

# Cells we skip — they require Ollama to actually be running, or Chroma populated.
SKIP_PATTERNS = [
    "build_or_open_family_index(reset=False)",
    "ollama_chat(",                  # smoke test inside the LLM helpers cell
    "chat_basic(",                   # smoke test
    "embed(",                        # smoke test
    "graph.invoke",
    "graph.stream",
    "run_traced(",
    "graph.get_graph().draw_mermaid",
]

def cell_calls_runtime(src: str) -> bool:
    """Cells that run the graph or hit live LLM/Chroma — we drop them entirely."""
    triggers = [
        "graph.invoke", "graph.stream", "run_traced(", "final = run_traced(",
        "build_or_open_family_index(reset=False)",
        "graph.get_graph().draw_mermaid",
        "show_state(final)",
        "init_agentic_db(drop_and_recreate=True); populate_template_libraries()",  # the per-run reset cells
    ]
    return any(t in src for t in triggers)


def smoke_only(src: str) -> str:
    """Strip a few trailing lines that call the LLM as a smoke test inside def cells."""
    drops = ("print(ollama_chat", "print(\"chat_basic",
             "print(f\"embed", "v = embed(")
    return "\n".join(ln for ln in src.splitlines()
                     if not any(d in ln for d in drops))


stitched = []
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    src = "".join(c["source"])
    if cell_calls_runtime(src):
        stitched.append(f"# === cell {i} SKIPPED (runtime/LLM/Chroma) ===")
        continue
    stitched.append(f"# === cell {i} ===")
    stitched.append(smoke_only(src))

out = HERE / "_smoke_extracted.py"
out.write_text("\n\n".join(stitched), encoding="utf-8")
print(f"wrote {out.name}: {len(stitched)//2} chunks")

# Compile-check it.
import py_compile
py_compile.compile(str(out), doraise=True)
print("compile OK")

# Try to actually exec the safe portion (everything but Chroma build / LLM smoke / runs).
print("\n--- exec'ing extracted ---")
ns: dict = {"__name__": "__main__", "__file__": str(out)}
try:
    exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), ns)
except Exception as e:
    print(f"\n❌ EXEC FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All non-LLM defs run cleanly")
print(f"  FUNCTION_MAP entries     : {len(ns.get('FUNCTION_MAP', {}))}")
print(f"  STRATEGIES_SEED entries  : {len(ns.get('STRATEGIES_SEED', []))}")
print(f"  FUNCTIONS_SEED entries   : {len(ns.get('FUNCTIONS_SEED', []))}")
print(f"  PROMPTS keys             : {list(ns.get('PROMPTS', {}).keys())}")
print(f"  graph nodes              : {list(ns['graph'].get_graph().nodes) if 'graph' in ns else 'N/A'}")
