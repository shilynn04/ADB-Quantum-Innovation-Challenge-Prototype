"""Amplitude-estimation engine (ideal-circuit simulation) + explicit statevector check.

Each target is an expectation a = E[f] with f scaled to [0,1].  A|0> = sum_x sqrt(p(x)) |x>(sqrt(1-f)|0>+sqrt(f)|1>),
Grover operator Q = A S0 A^dag S_chi, and P(measure 1 | Q^k A|0>) = sin^2((2k+1) theta), a = sin^2(theta).
Cost accounting: one shot at power k uses (2k+1) applications of A (A counted as one oracle call).
"""
import numpy as np
from .model import CAPTAB, annual_distribution, target_functions

YEARS = 3


def term_path_distribution(p):
    """Joint pmf over (year1, year2, year3) annual states = amplitudes^2 loaded by A (10^6 entries)."""
    return np.einsum("i,j,k->ijk", p, p, p).reshape(-1)


def path_payoffs(F):
    """Payoff of every 3-year path (vectorised): F_path[j, i*10^4+j*100+k]."""
    s1 = CAPTAB[0]                       # after year 1 (start at state 0)
    s2 = CAPTAB[s1]                      # (100,100): [y1, y2]
    s3 = CAPTAB[s2[:, :, None], np.arange(100)[None, None, :]]  # (100,100,100)
    return F[:, s3.reshape(-1)]


def statevector_check(p, f_path, ks=(0, 1, 2, 3, 5, 8)):
    """Explicit 2^21 x 2 statevector simulation of Q^k A|0>; returns (theta_exact, [(k, P1_sim, P1_theory)])."""
    amp = np.sqrt(term_path_distribution(p))
    psi = np.stack([amp * np.sqrt(1 - f_path), amp * np.sqrt(f_path)], axis=1)  # [..., objective qubit]
    chi = np.array([1.0, -1.0])                                                # S_chi flips 'good' (obj=1)
    a = float((psi[:, 1] ** 2).sum())
    theta = np.arcsin(np.sqrt(a))
    out, v = [], psi.copy()
    for k in range(max(ks) + 1):
        if k in ks:
            out.append((k, float((v[:, 1] ** 2).sum()), float(np.sin((2 * k + 1) * theta) ** 2)))
        v = v * chi[None, :]                           # S_chi
        v = 2 * psi * (psi.ravel() @ v.ravel()) - v    # A S0 A^dag = 2|psi><psi| - I  (apply via overlap)
        v = -v                                         # global sign convention Q = -A S0 A^dag S_chi
    return theta, out


def schedule(m):
    return [0] + [2**j for j in range(m)]   # powers k: 0,1,2,4,...,2^(m-1)


def mlae(a_true, shots, m, rng, kappa=0.0):
    """Maximum-likelihood AE with ideal binomial shot noise; kappa = per-oracle-call contrast decay (noise model).

    Returns (estimate, oracle_calls).  P_k = 1/2 + (sin^2((2k+1)theta) - 1/2) * exp(-kappa*(2k+1)).
    """
    th = np.arcsin(np.sqrt(a_true))
    ks = schedule(m)
    hits = []
    calls = 0
    for k in ks:
        pk = 0.5 + (np.sin((2 * k + 1) * th) ** 2 - 0.5) * np.exp(-kappa * (2 * k + 1))
        hits.append(rng.binomial(shots, pk))
        calls += shots * (2 * k + 1)
    grid = np.concatenate([np.geomspace(1e-6, 0.05, 4000), np.linspace(0.05, np.pi / 2, 4000)])
    ll = np.zeros_like(grid)
    for k, h in zip(ks, hits):
        pk = 0.5 + (np.sin((2 * k + 1) * grid) ** 2 - 0.5) * np.exp(-kappa * (2 * k + 1))
        pk = np.clip(pk, 1e-12, 1 - 1e-12)
        ll += h * np.log(pk) + (shots - h) * np.log(1 - pk)
    i = int(np.argmax(ll))
    lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    fine = np.linspace(lo, hi, 400)
    ll2 = np.zeros_like(fine)
    for k, h in zip(ks, hits):
        pk = 0.5 + (np.sin((2 * k + 1) * fine) ** 2 - 0.5) * np.exp(-kappa * (2 * k + 1))
        pk = np.clip(pk, 1e-12, 1 - 1e-12)
        ll2 += h * np.log(pk) + (shots - h) * np.log(1 - pk)
    return float(np.sin(fine[int(np.argmax(ll2))]) ** 2), calls
