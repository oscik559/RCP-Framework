"""
Shared statistics helpers for the revision experiments (Reviewer 2 #1 & #2).

Pure-Python (stdlib only) so the harness has no extra dependencies beyond what the
repo already pins. All functions operate on lists of 0/1 integers unless noted.

Methods implemented:
  - wilson_ci ............ Wilson score interval for a single proportion.
  - mcnemar_chi2 ......... McNemar's test (continuity-corrected) for paired binaries.
  - newcombe_paired_diff_ci  95% CI on the change in a *matched* proportion
                             (Newcombe's method 10 — the Wilson-based interval for
                             the difference of two paired proportions; this is the
                             "Wilson method on matched proportions" used in the paper).
  - bootstrap_ci ......... Percentile bootstrap CI for a proportion (resample labels).
  - cohens_kappa ......... Cohen's kappa + raw percent agreement for two raters.
"""

from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple


# --------------------------------------------------------------------------------------
# Single-proportion Wilson interval
# --------------------------------------------------------------------------------------
def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for k successes out of n (returns proportions in [0,1])."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


# --------------------------------------------------------------------------------------
# McNemar's test (paired binary)
# --------------------------------------------------------------------------------------
def _chi2_sf_df1(x: float) -> float:
    """Survival function P(chi2_1 > x) for 1 degree of freedom."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def discordant_counts(a: Sequence[int], b: Sequence[int]) -> Tuple[int, int, int, int]:
    """Return (both1, a1b0, a0b1, both0) for two matched 0/1 sequences."""
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    n11 = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n00 = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    return n11, n10, n01, n00


def mcnemar_chi2(n10: int, n01: int) -> Tuple[float, float]:
    """Continuity-corrected McNemar chi-square and p-value from the discordant cells.

    n10 = #(a=1, b=0), n01 = #(a=0, b=1). Matches Experiments/Case_*/compute_mcnemar.py.
    """
    disc = n10 + n01
    if disc == 0:
        return 0.0, 1.0
    chi = (abs(n10 - n01) - 1) ** 2 / disc
    return chi, _chi2_sf_df1(chi)


# --------------------------------------------------------------------------------------
# Newcombe method 10 — 95% CI on the difference of two *paired* proportions
# --------------------------------------------------------------------------------------
def newcombe_paired_diff_ci(a: Sequence[int], b: Sequence[int], z: float = 1.96
                            ) -> Tuple[float, float, float]:
    """95% CI for the change p_b - p_a on matched binary labels (Newcombe 1998, method 10).

    Returns (delta, lower, upper) as proportions. This is the Wilson-score interval
    generalised to the difference of two paired proportions and is what the paper's
    significance table reports in its "95% CI" column.
    """
    n11, n10, n01, n00 = discordant_counts(a, b)
    n = n11 + n10 + n01 + n00
    if n == 0:
        return (0.0, 0.0, 0.0)
    p_a = (n11 + n10) / n           # proportion correct under system A
    p_b = (n11 + n01) / n           # proportion correct under system B
    delta = p_b - p_a
    l1, u1 = wilson_ci(n11 + n10, n, z)   # Wilson for p_a
    l2, u2 = wilson_ci(n11 + n01, n, z)   # Wilson for p_b

    # correlation correction phi
    denom = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    phi = 0.0
    if denom > 0:
        phi = (n11 * n00 - n10 * n01) / math.sqrt(denom)

    lower = delta - math.sqrt(max(0.0, (p_a - l1) ** 2 - 2 * phi * (p_a - l1) * (u2 - p_b) + (u2 - p_b) ** 2))
    upper = delta + math.sqrt(max(0.0, (p_b - l2) ** 2 - 2 * phi * (p_b - l2) * (u1 - p_a) + (u1 - p_a) ** 2))
    return (delta, max(-1.0, lower), min(1.0, upper))


# --------------------------------------------------------------------------------------
# Bootstrap CI for a proportion
# --------------------------------------------------------------------------------------
def bootstrap_ci(labels: Sequence[int], n_boot: int = 10000, seed: int = 12345,
                 alpha: float = 0.05) -> Tuple[float, float, float]:
    """Percentile bootstrap CI for the mean of binary labels.

    Returns (point_estimate, lower, upper) as proportions. Resamples the labels with
    replacement n_boot times (default 10k), as specified in the experiment brief.
    """
    n = len(labels)
    if n == 0:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    point = sum(labels) / n
    means = []
    for _ in range(n_boot):
        s = 0
        for _ in range(n):
            s += labels[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (point, lo, hi)


# --------------------------------------------------------------------------------------
# Cohen's kappa
# --------------------------------------------------------------------------------------
def cohens_kappa(a: Sequence[int], b: Sequence[int]) -> Tuple[float, float]:
    """Cohen's kappa and raw percent agreement for two raters' binary labels."""
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        return (0.0, 0.0)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1.0:
        return (1.0, po)  # perfect/degenerate agreement
    kappa = (po - pe) / (1 - pe)
    return (kappa, po)
