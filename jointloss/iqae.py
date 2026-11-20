"""Iterative Quantum Amplitude Estimation (IQAE), Grinko et al. (2021), npj Quantum Inf. 7:52.

Emulated at the level of measurement statistics, exactly like `qae.mlae`: a shot at Grover
power k returns 1 with probability sin^2((2k+1) theta), a = sin^2(theta). That law is checked
against an explicit statevector simulation in `qae.statevector_check`.

Differences from the Qiskit reference implementation (same algorithm otherwise):
* the loop stops on the half-width of the *amplitude* confidence interval (`eps` is an
  absolute target on `a`), so small amplitudes are not over-resolved;
* cost is counted in applications of the state-preparation oracle A: a shot at power k
  costs 2k+1 (consistent with `qae.mlae` and `run_benchmarks.py`).
"""
import numpy as np
from scipy.stats import beta


def _clopper_pearson(ones, shots, alpha):
    lo = 0.0 if ones == 0 else beta.ppf(alpha / 2, ones, shots - ones + 1)
    hi = 1.0 if ones == shots else beta.ppf(1 - alpha / 2, ones + 1, shots - ones)
    return lo, hi


def _find_next_k(k, upper, th_l, th_u, min_ratio=2.0):
    """Largest admissible power K=4k+2 (theta in units of 2*pi, theta in [0, 1/4])."""
    old = 4 * k + 2
    K = int(1 / (2 * (th_u - th_l)))
    K = K - (K - 2) % 4
    while K >= min_ratio * old:
        lo, hi = K * th_l - int(K * th_l), K * th_u - int(K * th_u)
        if lo <= hi <= 0.5 and lo <= 0.5:
            return (K - 2) // 4, True
        if hi >= 0.5 and hi >= lo >= 0.5:
            return (K - 2) // 4, False
        K -= 4
    return k, upper


def iqae(a_true, eps, rng, alpha=0.05, shots=100, min_ratio=2.0, max_iter=200):
    """Estimate a = sin^2(theta) to absolute half-width `eps` with confidence 1-alpha.

    Returns dict(estimate, ci=(lo, hi), calls, max_k, rounds).
    """
    phi = np.arcsin(np.sqrt(np.clip(a_true, 0.0, 1.0)))
    T = int(np.log(min_ratio * np.pi / 8 / eps) / np.log(min_ratio)) + 1   # max rounds (alpha split)
    th_l, th_u = 0.0, 0.25
    k, upper = 0, True
    hist_k, hist_ones = [], []
    calls, it = 0, 0
    a_l, a_u = 0.0, 1.0
    while (a_u - a_l) / 2 > eps and it < max_iter:
        it += 1
        k, upper = _find_next_k(k, upper, th_l, th_u, min_ratio)
        ones = rng.binomial(shots, np.sin((2 * k + 1) * phi) ** 2)
        calls += shots * (2 * k + 1)
        hist_k.append(k); hist_ones.append(ones)
        # pool all consecutive rounds that used the same power
        n, o = 0, 0
        for kk, oo in zip(reversed(hist_k), reversed(hist_ones)):
            if kk != k:
                break
            n += shots; o += oo
        p_lo, p_hi = _clopper_pearson(o, n, alpha / T)
        if upper:
            t_lo = np.arccos(1 - 2 * p_lo) / (2 * np.pi)
            t_hi = np.arccos(1 - 2 * p_hi) / (2 * np.pi)
        else:
            t_lo = 1 - np.arccos(1 - 2 * p_hi) / (2 * np.pi)
            t_hi = 1 - np.arccos(1 - 2 * p_lo) / (2 * np.pi)
        K = 4 * k + 2
        new_u = (int(K * th_u) + t_hi) / K
        new_l = (int(K * th_l) + t_lo) / K
        th_l, th_u = max(th_l, new_l), min(th_u, new_u)
        a_l, a_u = np.sin(2 * np.pi * th_l) ** 2, np.sin(2 * np.pi * th_u) ** 2
    return {"estimate": float((a_l + a_u) / 2), "ci": (float(a_l), float(a_u)),
            "calls": int(calls), "max_k": int(max(hist_k) if hist_k else 0), "rounds": it}
