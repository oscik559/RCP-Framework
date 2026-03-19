import json
from pathlib import Path

results_dir = Path("Experiments/Case_II/results")


def get_avg_metrics(name, file_path):
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    n = len(data)
    if n == 0:
        return None

    avg_tokens = sum(r.get("token_estimate", 0) for r in data) / n

    return {
        "avg_tokens": avg_tokens,
    }


print("=" * 50)
print("CASE II — Token Cost Estimates")
print("=" * 50)
print("B1:", get_avg_metrics("B1", results_dir / "b1_rag_latest.json"))
print("B2:", get_avg_metrics("B2", results_dir / "b2_sql_latest.json"))
print("B3:", get_avg_metrics("B3", results_dir / "b3_rcp_latest.json"))
