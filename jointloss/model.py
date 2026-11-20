"""Exact reference model for the ADB two-country (Kyrgyz Republic / Tajikistan) benchmark.

Implements steps 1-8 of the challenge brief: compound-Poisson earthquake CTMC with shared
events, correlated precipitation triggers, 100-state annual distribution, 3-year capped
convolution, and the five focus targets.
"""
from dataclasses import dataclass, replace
import numpy as np
from scipy.linalg import expm

# Table 1: tail probabilities  P(annual aggregate payout >= 25/50/75/100 %)
TAILS = {
    "KGZ": (0.03883, 0.02331, 0.01790, 0.01184),
    "TJK": (0.03925, 0.01743, 0.01332, 0.01043),
}
COND = (0.075, 0.074)  # P(TJK|KGZ), P(KGZ|TJK)  (Table / Eq. 4)


@dataclass(frozen=True)
class Scenario:
    name: str = "adb-base"
    m: float = 1.0            # shared-earthquake-rate multiplier
    rain_mult: float = 1.0    # precipitation rate multiplier
    rain_share: float = 0.25  # shared precip rate as share of smaller country rate
    q: float = 0.02           # annual precip trigger probability
    eq_limit: float = 70.0    # USD m earthquake sub-limit per country
    rain_limit: float = 10.0  # USD m precipitation sub-limit per country
    years: int = 3
    T: float = 80.0           # USD m principal (threshold for loss exceedance / stop-loss)


SCENARIOS = {
    "adb-base": Scenario(),
    "adb-independent": Scenario("adb-independent", m=0.0, rain_share=0.0),
    "adb-common-shock": Scenario("adb-common-shock", m=2.0),
    "adb-rain-stress": Scenario("adb-rain-stress", rain_mult=2.0),
    "adb-rain-cover": Scenario("adb-rain-cover", eq_limit=60.0, rain_limit=20.0),
}


def cp_rates(tails):
    """Eqs. (2)-(3): compound-Poisson rates lambda_1..4 and total Lambda from tail probs."""
    t1, t2, t3, t4 = tails
    p0, p1, p2, p3 = 1 - t1, t1 - t2, t2 - t3, t3 - t4
    Lam = -np.log(p0)
    l1 = p1 / p0
    l2 = p2 / p0 - l1**2 / 2
    l3 = p3 / p0 - l1 * l2 - l1**3 / 6
    l4 = Lam - l1 - l2 - l3
    return np.array([l1, l2, l3, l4]), Lam


def quake_annual(m=1.0):
    """25-state CTMC for cumulative quarter steps (a,b), capped at 4. Returns 5x5 joint pmf."""
    lam1, L1 = cp_rates(TAILS["KGZ"])
    lam2, L2 = cp_rates(TAILS["TJK"])
    c = m * 0.5 * (COND[0] * L1 + COND[1] * L2)
    w1, w2 = lam1 / L1, lam2 / L2
    idx = lambda a, b: a * 5 + b
    G = np.zeros((25, 25))
    for a in range(5):
        for b in range(5):
            s = idx(a, b)
            for k in range(1, 5):
                G[s, idx(min(a + k, 4), b)] += (L1 - c) * w1[k - 1]
                G[s, idx(a, min(b + k, 4))] += (L2 - c) * w2[k - 1]
                for j in range(1, 5):
                    G[s, idx(min(a + k, 4), min(b + j, 4))] += c * w1[k - 1] * w2[j - 1]
            G[s, s] -= (L1 - c) + (L2 - c) + c
    return expm(G)[0].reshape(5, 5)


def rain_annual(q=0.02, mult=1.0, share=0.25):
    """Eqs. (5)-(6): 2x2 joint pmf of precipitation triggers (r1, r2)."""
    mu1 = mu2 = -np.log(1 - q) * mult
    cr = share * min(mu1, mu2)
    p00 = np.exp(-(mu1 + mu2 - cr))
    p10 = np.exp(-mu2) - p00
    p01 = np.exp(-mu1) - p00
    p11 = 1 - p00 - p10 - p01
    return np.array([[p00, p01], [p10, p11]])  # index [r1, r2]


def annual_distribution(sc: Scenario):
    """100-state annual pmf over (a, b, r1, r2); flat index = ((a*5+b)*2+r1)*2+r2."""
    eq = quake_annual(sc.m)
    rn = rain_annual(sc.q, sc.rain_mult, sc.rain_share)
    P = np.einsum("ab,rs->abrs", eq, rn)
    return P.reshape(-1)


STATES = np.array([(a, b, r1, r2) for a in range(5) for b in range(5)
                   for r1 in range(2) for r2 in range(2)])


def annual_loss(sc: Scenario):
    """Uncapped single-year principal loss per annual state (USD m)."""
    a, b, r1, r2 = STATES.T
    return sc.eq_limit * (a + b) / 4 + sc.rain_limit * (r1 + r2)


CAP = np.array([4, 4, 1, 1])


def _cap_index():
    """Map pair (state s of running total, annual state t) -> capped running total."""
    idx = {tuple(s): i for i, s in enumerate(STATES)}
    tab = np.zeros((100, 100), dtype=np.int64)
    for i, s in enumerate(STATES):
        for j, t in enumerate(STATES):
            tab[i, j] = idx[tuple(np.minimum(s + t, CAP))]
    return tab


CAPTAB = _cap_index()


def term_distribution(sc: Scenario, p=None):
    """Exact capped 3-year term distribution via direct convolution (3 passes over 100x100)."""
    if p is None:
        p = annual_distribution(sc)
    d = np.zeros(100); d[0] = 1.0
    for _ in range(sc.years):
        nd = np.zeros(100)
        for i in np.nonzero(d)[0]:
            np.add.at(nd, CAPTAB[i], d[i] * p)
        d = nd
    return d


def term_losses(sc: Scenario):
    """Per-term-state principal losses L1, L2, L (USD m), same state indexing."""
    a, b, r1, r2 = STATES.T
    L1 = sc.eq_limit * a / 4 + sc.rain_limit * r1
    L2 = sc.eq_limit * b / 4 + sc.rain_limit * r2
    return L1, L2, L1 + L2


TARGETS = ["expected_loss_usd_m", "joint_attachment_prob", "loss_exceed_T_prob",
           "stop_loss_usd_m", "both_exhausted_prob"]


def target_values(sc: Scenario, d):
    """Five focus targets from a term-state distribution d."""
    L1, L2, L = term_losses(sc)
    full = sc.eq_limit + sc.rain_limit
    return np.array([
        d @ L,
        d @ ((L1 > 0) & (L2 > 0)),
        d @ (L > sc.T + 1e-9),
        d @ np.maximum(L - sc.T, 0),
        d @ ((np.isclose(L1, full)) & (np.isclose(L2, full))),
    ])


def target_functions(sc: Scenario):
    """Per-term-state payoff matrix F (5 x 100): target_j = F[j] @ d."""
    L1, L2, L = term_losses(sc)
    full = sc.eq_limit + sc.rain_limit
    return np.vstack([L, (L1 > 0) & (L2 > 0), L > sc.T + 1e-9,
                      np.maximum(L - sc.T, 0), np.isclose(L1, full) & np.isclose(L2, full)]).astype(float)


def exact_targets(sc: Scenario):
    return target_values(sc, term_distribution(sc))
