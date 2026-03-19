"""
Compute McNemar's test statistics and Wilson CIs for Case I (Hydroscand).

Usage: python Experiments/Case_I/compute_mcnemar.py
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


# ── Case I ──────────────────────────────────────────────────────────────────
b1_i = load("Experiments/Case_I/results/b1_rag_latest.json")
b2_i = load("Experiments/Case_I/results/b2_sql_latest.json")
b3_i = load("Experiments/Case_I/results/b3_rcp_latest.json")

n_i = len(b3_i)
paired_ids_b3 = {r["question_id"] for r in b3_i}

b1_map = {r["question_id"]: r for r in b1_i}
b2_map = {r["question_id"]: r for r in b2_i}
b3_map = {r["question_id"]: r for r in b3_i}

# B1→B2 (n=100)
pairs_12 = [(b1_map[qid]["answer_correct"], b2_map[qid]["answer_correct"])
            for qid in range(1, 101) if qid in b1_map and qid in b2_map]
n12 = len(pairs_12)
n01_12 = sum(1 for a, b in pairs_12 if a == 0 and b == 1)
n10_12 = sum(1 for a, b in pairs_12 if a == 1 and b == 0)
chi_12, p_12 = mcnemar_chi2(n01_12, n10_12)

# B2→B3 (n=len(b3_i))
pairs_23 = [(b2_map[qid]["answer_correct"], b3_map[qid]["answer_correct"])
            for qid in paired_ids_b3 if qid in b2_map]
n23 = len(pairs_23)
n01_23 = sum(1 for a, b in pairs_23 if a == 0 and b == 1)
n10_23 = sum(1 for a, b in pairs_23 if a == 1 and b == 0)
chi_23, p_23 = mcnemar_chi2(n01_23, n10_23)

# B1→B3 AC
pairs_13_ac = [(b1_map[qid]["answer_correct"], b3_map[qid]["answer_correct"])
               for qid in paired_ids_b3 if qid in b1_map]
n13 = len(pairs_13_ac)
n01_13 = sum(1 for a, b in pairs_13_ac if a == 0 and b == 1)
n10_13 = sum(1 for a, b in pairs_13_ac if a == 1 and b == 0)
chi_13, p_13 = mcnemar_chi2(n01_13, n10_13)

# B2→B3 HR
pairs_23_hr = [(b2_map[qid]["hallucination"], b3_map[qid]["hallucination"])
               for qid in paired_ids_b3 if qid in b2_map]
n01_hr = sum(1 for a, b in pairs_23_hr if a == 1 and b == 0)  # B2 hallucinates, B3 doesn't
n10_hr = sum(1 for a, b in pairs_23_hr if a == 0 and b == 1)
chi_hr, p_hr = mcnemar_chi2(n01_hr, n10_hr)

print("=" * 60)
print("CASE I (Hydroscand)")
print("=" * 60)
print(f"B1 AC: {sum(r['answer_correct'] for r in b1_i)/100*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b1_i)/100*100:.1f}%  (n=100)")
print(f"B2 AC: {sum(r['answer_correct'] for r in b2_i)/100*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b2_i)/100*100:.1f}%  (n=100)")
print(f"B3 AC: {sum(r['answer_correct'] for r in b3_i)/n_i*100:.1f}%  "
      f"HR: {sum(r['hallucination'] for r in b3_i)/n_i*100:.1f}%  "
      f"CA: {sum(r['citation_accurate'] for r in b3_i)/n_i*100:.1f}%  "
      f"UF: {sum(r['unit_fidelity'] for r in b3_i)/n_i*100:.1f}%  (n={n_i})")
print()
print(f"McNemar B1→B2 AC (n={n12}): χ²={chi_12:.2f}, p={p_12:.3f}")
print(f"McNemar B2→B3 AC (n={n23}): χ²={chi_23:.2f}, p={p_23:.3f}")
print(f"McNemar B1→B3 AC (n={n13}): χ²={chi_13:.2f}, p={p_13:.3f}")
print(f"McNemar B2→B3 HR (n={len(pairs_23_hr)}): χ²={chi_hr:.2f}, p={p_hr:.3f}")
print()

# Wilson CIs Case I
k_b1 = sum(r['answer_correct'] for r in b1_i)
k_b2 = sum(r['answer_correct'] for r in b2_i)
k_b3 = sum(r['answer_correct'] for r in b3_i)
k_b3_hr = sum(r['hallucination'] for r in b3_i)

lo, hi = wilson_ci(k_b1, 100)
print(f"Wilson B1 AC [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
lo, hi = wilson_ci(k_b2, 100)
print(f"Wilson B2 AC [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
lo, hi = wilson_ci(k_b3, n_i)
print(f"Wilson B3 AC [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")
lo, hi = wilson_ci(k_b3_hr, n_i)
print(f"Wilson B3 HR [95%]: [{lo*100:.1f}%, {hi*100:.1f}%]")

print()
