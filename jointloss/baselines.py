"""Classical sampling baselines from the brief (step 9): MC, scrambled Sobol, stratified, importance."""
import numpy as np
from scipy.stats import qmc
from .model import CAPTAB, annual_distribution, annual_loss, target_functions

YEARS = 3


def _walk(states):
    """states: (n, years) annual-state indices -> capped term-state index (n,)."""
    s = np.zeros(states.shape[0], dtype=np.int64)
    for y in range(states.shape[1]):
        s = CAPTAB[s, states[:, y]]
    return s


def _invert(u, cdf):
    return np.minimum(np.searchsorted(cdf, u, side="right"), len(cdf) - 1)


def mc(sc, n, rng, p=None, F=None):
    p = annual_distribution(sc) if p is None else p
    F = target_functions(sc) if F is None else F
    cdf = np.cumsum(p)
    st = _invert(rng.random((n, YEARS)), cdf)
    return F[:, _walk(st)].mean(1)


def sobol(sc, n, rng, p=None, F=None, scrambles=8):
    """8 independent scrambles, averaged. n = total budget (split evenly, power of 2 each)."""
    p = annual_distribution(sc) if p is None else p
    F = target_functions(sc) if F is None else F
    cdf = np.cumsum(p)
    per = max(int(n // scrambles), 1)
    m = int(np.floor(np.log2(per)))
    ests = []
    for _ in range(scrambles):
        pts = qmc.Sobol(d=YEARS, scramble=True, seed=rng).random_base2(m)
        ests.append(F[:, _walk(_invert(pts, cdf))].mean(1))
    return np.mean(ests, axis=0)


def stratified(sc, n, rng, p=None, F=None):
    """Strata = first year with any payout (1,2,3); weight p0^(k-1)(1-p0); no-payout path -> 0."""
    p = annual_distribution(sc) if p is None else p
    F = target_functions(sc) if F is None else F
    p0 = p[0]
    pnz = p.copy(); pnz[0] = 0; pnz /= pnz.sum()
    cdf_full, cdf_nz = np.cumsum(p), np.cumsum(pnz)
    per = n // YEARS
    est = np.zeros(F.shape[0])
    for k in range(1, YEARS + 1):
        st = np.zeros((per, YEARS), dtype=np.int64)       # years before k: state 0
        st[:, k - 1] = _invert(rng.random(per), cdf_nz)   # year k: conditioned non-zero
        for y in range(k, YEARS):
            st[:, y] = _invert(rng.random(per), cdf_full)
        est += p0 ** (k - 1) * (1 - p0) * F[:, _walk(st)].mean(1)
    return est


def importance(sc, n, rng, p=None, F=None):
    """Proposal per year = 0.5*true + 0.5*(true tilted by principal loss); likelihood-ratio reweighting."""
    p = annual_distribution(sc) if p is None else p
    F = target_functions(sc) if F is None else F
    loss = annual_loss(sc)
    tilt = p * loss
    tilt /= tilt.sum()
    q = 0.5 * p + 0.5 * tilt
    st = _invert(rng.random((n, YEARS)), np.cumsum(q))
    w = np.prod(p[st] / q[st], axis=1)
    return (F[:, _walk(st)] * w).mean(1)


METHODS = {"MC": mc, "Sobol": sobol, "Stratified": stratified, "Importance": importance}
