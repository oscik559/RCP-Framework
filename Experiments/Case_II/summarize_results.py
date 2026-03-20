import json
from pathlib import Path

results_dir = Path("Experiments/Case_II/results")


def summarize(name, file_path):
    if not file_path.exists():
        print(f"{name}: File not found")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    n = len(data)
    if n == 0:
        return
    correct = sum(r.get("answer_correct", 0) for r in data)
    citation = sum(r.get("citation_accurate", 0) for r in data)
    units = sum(r.get("unit_fidelity", 0) for r in data)
    halluc = sum(r.get("hallucination", 0) for r in data)
    avg_lat = sum(r.get("latency_s", 0) for r in data) / n

    print(f"--- {name} (n={n}) ---")
    print(f"Correctness:   {correct/n*100:.1f}%")
    print(f"Citation:      {citation/n*100:.1f}%")
    print(f"Units:         {units/n*100:.1f}%")
    print(f"Hallucination: {halluc/n*100:.1f}%")
    print(f"Avg Latency:   {avg_lat:.2f}s")
    print("")


print("=" * 50)
print("CASE II — Company B")
print("=" * 50)
summarize("B1: Naive RAG", results_dir / "b1_rag_latest.json")
summarize("B2: SQL Retrieval", results_dir / "b2_sql_latest.json")
summarize("B3: RCP Framework", results_dir / "b3_rcp_latest.json")
