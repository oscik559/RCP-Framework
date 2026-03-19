"""
Compute McNemar's test statistics and Wilson CIs for Case II (Saab).

Usage: python Experiments/Case_II/compute_mcnemar.py
"""
import json
import math


def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return max(0, center - margin), min(1, center + margin)


def chi2_cdf(x, df=1):
    """Regularized incomplete gamma function for chi2 CDF (df=1)."""
    # P(chi2 <= x) = erf(sqrt(x/2)) for df=1
    return math.erf(math.sqrt(x / 2))


def mcnemar_chi2(n01, n10):
    """n01: disagreed in favour of A; n10: disagreed in favour of B"""
    if n01 + n10 == 0:
        return 0.0, 1.0
    chi = (abs(n01 - n10) - 1)**2 / (n01 + n10)
    p = 1 - chi2_cdf(chi)
    return chi, p


def load(path):
    with open(path) as f:
        return json.load(f)


# ── Case II ─────────────────────────────────────────────────────────────────
b1_ii = load("Experiments/Case_II/results/b1_rag_latest.json")
b2_ii = load("Experiments/Case_II/results/b2_sql_latest.json")
b3_ii = load("Experiments/Case_II/results/b3_rcp_latest.json")

n_b1_ii = len(b1_ii)

b1_ii_map = {r["question_id"]: r for r in b1_ii}
b2_ii_map = {r["question_id"]: r for r in b2_ii}
b3_ii_map = {r["question_id"]: r for r in b3_ii}

# B1→B2 (n=min(b1,b2) matched)
common_12_ii = set(b1_ii_map) & set(b2_ii_map)
pairs_12_ii = [(b1_ii_map[qid]["answer_correct"], b2_ii_map[qid]["answer_correct"])
               for qid in sorted(common_12_ii)]
n12_ii = len(pairs_12_ii)
n01_12_ii = sum(1 for a, b in pairs_12_ii if a == 0 and b == 1)
n10_12_ii = sum(1 for a, b in pairs_12_ii if a == 1 and b == 0)
chi_12_ii, p_12_ii = mcnemar_chi2(n01_12_ii, n10_12_ii)

# B2→B3 (n=100)
common_23_ii = set(b2_ii_map) & set(b3_ii_map)
pairs_23_ii = [(b2_ii_map[qid]["answer_correct"], b3_ii_map[qid]["answer_correct"])
               for qid in sorted(common_23_ii)]
n23_ii = len(pairs_23_ii)
n01_23_ii = sum(1 for a, b in pairs_23_ii if a == 0 and b == 1)
n10_23_ii = sum(1 for a, b in pairs_23_ii if a == 1 and b == 0)
chi_23_ii, p_23_ii = mcnemar_chi2(n01_23_ii, n10_23_ii)

# B1→B3
common_13_ii = set(b1_ii_map) & set(b3_ii_map)
pairs_13_ii = [(b1_ii_map[qid]["answer_correct"], b3_ii_map[qid]["answer_correct"])
               for qid in sorted(common_13_ii)]
n13_ii = len(pairs_13_ii)
n01_13_ii = sum(1 for a, b in pairs_13_ii if a == 0 and b == 1)
n10_13_ii = sum(1 for a, b in pairs_13_ii if a == 1 and b == 0)
chi_13_ii, p_13_ii = mcnemar_chi2(n01_13_ii, n10_13_ii)

print("=" * 60)
print("CASE II (Saab)")
print("=" * 60)
print(f"B1 AC: {sum(r['answer_correct'] for r in b1_ii)/n_b1_ii*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b1_ii)/n_b1_ii*100:.1f}%  (n={n_b1_ii})")
print(f"B2 AC: {sum(r['answer_correct'] for r in b2_ii)/100*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b2_ii)/100*100:.1f}%  (n=100)")
print(f"B3 AC: {sum(r['answer_correct'] for r in b3_ii)/100*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b3_ii)/100*100:.1f}%  (n=100)")
print()
print(f"McNemar B1→B2 AC (n={n12_ii} matched pairs): χ²={chi_12_ii:.2f}, p={p_12_ii:.3f}")
print(f"McNemar B2→B3 AC (n={n23_ii}): χ²={chi_23_ii:.2f}, p={p_23_ii:.3f}")
print(f"McNemar B1→B3 AC (n={n13_ii} matched pairs): χ²={chi_13_ii:.2f}, p={p_13_ii:.3f}")

k_b3_ii = sum(r['answer_correct'] for r in b3_ii)
k_b3_ii_hr = sum(r['hallucination'] for r in b3_ii)
lo, hi = wilson_ci(k_b3_ii, 100)
print(f"Wilson B3 AC [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
lo, hi = wilson_ci(k_b3_ii_hr, 100)
print(f"Wilson B3 HR [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
if n_b1_ii == 100:
    k_b1_ii = sum(r['answer_correct'] for r in b1_ii)
    lo, hi = wilson_ci(k_b1_ii, 100)
    print(f"Wilson B1 AC [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
