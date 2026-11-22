"""n-country generalisation of the ADB benchmark, exact by conditioning on the regional factor.

Two facts make this exact and cheap:

1. Caps commute with summation of non-negative steps: min(min(x,4) + y, 4) = min(x + y, 4).
   So each country's capped 3-year quake total is min(own + shared, 4), where over the whole term
   own ~ compound Poisson(years * (Lambda_i - c)) with step law w_i = lambda_ik / Lambda_i, and
   shared = sum of K independent draws from w_i, K ~ Poisson(years * c). Shared events hit *all*
   countries (one regional factor); their sizes are drawn independently per country, as in the brief.
2. Precipitation: the brief's 2x2 law (Eqs. 5-6) is exactly "own Poisson rate mu_i - c_r plus a shared
   rate c_r"; a country's term trigger fires if any own or shared event occurs in the term.

Conditional on the latent pair (K capped at 4, shared-rain indicator S) the countries are independent,
so every portfolio target is a mixture over 10 latent states of products / convolutions of per-country
laws: cost O(n * loss grid), not 10^n annual states or 10^(3n) three-year paths.
At n = 2 this reproduces the brief's Table 5 (checked in validate_n2).

Synthetic portfolios clone countries alternately from the Kyrgyz Republic / Tajikistan parameters.
"""
import math
from fractions import Fraction
import numpy as np
from .model import TAILS, COND, SCENARIOS, cp_rates

CAP = 4
KEYS = ("KGZ", "TJK")


def country(i):
    lam, L = cp_rates(TAILS[KEYS[i % 2]])
    return {"w": np.concatenate([[0.0], lam / L]), "Lambda": float(L), "cond": COND[i % 2]}


def _pois(k, mu):
    return math.exp(-mu) * mu ** k / math.factorial(k)


def capped_compound_poisson(rate, w):
    """Law of min(S, CAP), S compound Poisson(rate) with step law w on {1..4} (w[0] = 0)."""
    out = np.zeros(CAP + 1)
    conv = np.zeros(CAP + 1); conv[0] = 1.0
    for N in range(CAP):                                   # N events give >= N steps
        out[:CAP] += _pois(N, rate) * conv[:CAP]
        conv = np.convolve(conv, w)[:CAP + 1]
    out[CAP] = 1.0 - out[:CAP].sum()
    return out


def capped_sum_of_draws(K, w):
    """Law of min(sum of K iid draws from w, CAP)."""
    if K >= CAP:
        d = np.zeros(CAP + 1); d[CAP] = 1.0
        return d
    conv = np.zeros(CAP + 1); conv[0] = 1.0
    for _ in range(K):
        conv = np.convolve(conv, w)[:CAP + 1]
    d = np.zeros(CAP + 1); d[:CAP] = conv[:CAP]; d[CAP] = 1.0 - conv[:CAP].sum()
    return d


def capped_add(x, y):
    z = np.convolve(x, y)
    out = z[:CAP + 1].copy(); out[CAP] = z[CAP:].sum()
    return out


def setup(n, sc=SCENARIOS["adb-base"]):
    """Latent law and per-country conditional laws for an n-country portfolio under scenario sc."""
    cs = [country(i) for i in range(n)]
    c = sc.m * float(np.mean([ci["cond"] * ci["Lambda"] for ci in cs]))
    Y = sc.years
    pK = np.array([_pois(k, Y * c) for k in range(CAP)] + [0.0]); pK[CAP] = 1.0 - pK[:CAP].sum()
    mu = -math.log(1 - sc.q) * sc.rain_mult
    cr = sc.rain_share * mu                                 # all countries share q, so min(mu_i) = mu
    pS = 1.0 - math.exp(-Y * cr)
    p_own_rain = 1.0 - math.exp(-Y * (mu - cr))
    a_given_K = []                                          # [country][K] -> law of capped quake steps
    for ci in cs:
        own = capped_compound_poisson(Y * (ci["Lambda"] - c), ci["w"])
        a_given_K.append([capped_add(own, capped_sum_of_draws(K, ci["w"])) for K in range(CAP + 1)])
    return {"n": n, "c": c, "pK": pK, "pS": pS, "p_own_rain": p_own_rain, "a_given_K": a_given_K, "sc": sc}


def _unit(sc):
    e, r = Fraction(sc.eq_limit) / 4, Fraction(sc.rain_limit)
    g = Fraction(math.gcd(e.numerator * r.denominator, r.numerator * e.denominator), e.denominator * r.denominator)
    return float(g), int(e / g), int(r / g)


def targets(n, sc=SCENARIOS["adb-base"], T=None):
    """Exact portfolio targets. T defaults to 40*n USD m (half the total principal; = 80 at n = 2)."""
    S = setup(n, sc)
    T = 40.0 * n if T is None else T
    unit, se, sr = _unit(sc)
    full = sc.eq_limit + sc.rain_limit
    t_units = T / unit
    res = {"expected_loss": 0.0, "all_pay": 0.0, "loss_exceed_T": 0.0, "stop_loss": 0.0,
           "all_exhausted": 0.0, "at_least_2_exhausted": 0.0}
    for K in range(CAP + 1):
        for s in (0, 1):
            pl = S["pK"][K] * (S["pS"] if s else 1 - S["pS"])
            if pl == 0:
                continue
            pr1 = 1.0 if s else S["p_own_rain"]
            port = np.zeros(1); port[0] = 1.0
            ex, pay = [], []
            for i in range(n):
                a = S["a_given_K"][i][K]
                li = np.zeros(CAP * se + sr + 1)
                for av in range(CAP + 1):
                    li[av * se] += a[av] * (1 - pr1)
                    li[av * se + sr] += a[av] * pr1
                port = np.convolve(port, li)
                ex.append(a[CAP] * pr1)
                pay.append(1.0 - li[0])
            L = np.arange(len(port)) * unit
            res["expected_loss"] += pl * float(port @ L)
            res["loss_exceed_T"] += pl * float(port[np.arange(len(port)) > t_units + 1e-9].sum())
            res["stop_loss"] += pl * float(port @ np.maximum(L - T, 0.0))
            res["all_exhausted"] += pl * float(np.prod(ex))
            res["all_pay"] += pl * float(np.prod(pay))
            pb = np.array([1.0])                                  # Poisson-binomial of exhausted count
            for e in ex:
                pb = np.convolve(pb, [1 - e, e])
            res["at_least_2_exhausted"] += pl * float(pb[2:].sum())
    res["T_usd_m"] = T
    res["full_loss_per_bond"] = full
    return res


def validate_n2():
    """Compare with the brief's exact enumeration (jointloss.model.exact_targets) for all five scenarios."""
    from .model import exact_targets
    out = {}
    for name, sc in SCENARIOS.items():
        ex = exact_targets(sc)
        t = targets(2, sc, T=sc.T)
        mine = np.array([t["expected_loss"], t["all_pay"], t["loss_exceed_T"], t["stop_loss"], t["all_exhausted"]])
        out[name] = {"max_rel_diff": float(np.max(np.abs(mine - ex) / np.abs(ex))),
                     "conditional": mine.tolist(), "brief_enumeration": ex.tolist()}
    return out


def mux_loader(qc, controls, targets, dists):
    """Multiplexed real-amplitude state preparation: for control value c, load sqrt(dists[c]) on targets.

    Moettoenen-style: set target bits from most to least significant with uniformly-controlled RY
    gates; the controls of bit j are the external controls plus the already-set higher bits.
    CX cost ~ sum_j 2^(len(controls) + m - 1 - j), i.e. 8 + 16 + 32 = 56 for 3 controls, 3 targets.
    """
    from qiskit.circuit.library import UCRYGate
    m, nc = len(targets), len(controls)
    vals = np.arange(2 ** m)
    for j in range(m - 1, -1, -1):
        hi_bits = m - 1 - j
        ang = np.zeros(2 ** (nc + hi_bits))
        for c in range(2 ** nc):
            d = dists[c]
            for hi in range(2 ** hi_bits):
                # hi encodes bits targets[j+1], ..., targets[m-1] (little-endian in that order)
                mask = np.ones(len(vals), bool)
                for l in range(hi_bits):
                    mask &= ((vals >> (j + 1 + l)) & 1) == ((hi >> l) & 1)
                tot = d[mask].sum()
                one = d[mask & (((vals >> j) & 1) == 1)].sum()
                ang[c + (2 ** nc) * hi] = 2 * math.asin(math.sqrt(min(1.0, one / tot))) if tot > 0 else 0.0
        qc.append(UCRYGate(list(ang)), [targets[j]] + list(controls) + [targets[l] for l in range(j + 1, m)])


# ------------------------------------------------------------------------------- quantum oracle
def build_term_oracle(n, sc=SCENARIOS["adb-base"]):
    """State-preparation oracle A for P(all n bonds exhausted), at term level.

    Only 3-year term totals enter the targets, and their law is available in closed form given the
    latent factor, so A loads the term law directly instead of three annual states plus adders:
      latent K (3 qubits, values 0..4 with 4 meaning >= 4; exact, no truncation) and shared-rain S (1),
      per country a K-multiplexed 3-qubit loader of a_i = min(own + shared, 4) and an own-rain qubit,
      then rain_all = S OR AND_i(own_i), and objective = AND_i(a_i == 4) AND rain_all.
    Qubits: 4n + 7. Each country adds one multiplexed loader and one control to the final MCX.
    """
    from qiskit import QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import StatePreparation
    S = setup(n, sc)
    K, Sr = QuantumRegister(3, "K"), QuantumRegister(1, "S")
    A_ = [QuantumRegister(3, f"a{i}") for i in range(n)]
    Rn = QuantumRegister(n, "rain")
    anc = QuantumRegister(2, "anc")
    obj = QuantumRegister(1, "obj")
    qc = QuantumCircuit(K, Sr, *A_, Rn, anc, obj, name=f"A_n{n}")
    ampK = np.zeros(8); ampK[:CAP + 1] = np.sqrt(S["pK"])
    qc.append(StatePreparation(ampK), list(K))
    qc.ry(2 * math.asin(math.sqrt(S["pS"])), Sr[0])
    for i in range(n):
        dists = [np.zeros(8) for _ in range(8)]                 # K values 5..7 never occur
        for k in range(CAP + 1):
            dists[k][:CAP + 1] = S["a_given_K"][i][k]
        mux_loader(qc, list(K), list(A_[i]), dists)
        qc.ry(2 * math.asin(math.sqrt(S["p_own_rain"])), Rn[i])
    qc.mcx(list(Rn), anc[0])                               # AND of own-rain triggers
    qc.x([Sr[0], anc[0]]); qc.ccx(Sr[0], anc[0], anc[1]); qc.x([Sr[0], anc[0], anc[1]])   # anc1 = S OR anc0
    qc.mcx([A_[i][2] for i in range(n)] + [anc[1]], obj[0])  # a_i == 4  <=>  bit 2 set (values <= 4)
    return qc


def oracle_amplitude(qc):
    """P(objective = 1) by exact statevector simulation (small n only)."""
    from qiskit.quantum_info import Statevector
    sv = Statevector.from_instruction(qc)
    return float(sv.probabilities([qc.num_qubits - 1])[1])


def oracle_counts(qc):
    from qiskit import transpile
    tc = transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1, seed_transpiler=7)
    ops = tc.count_ops()
    return {"qubits": tc.num_qubits, "cx": int(ops.get("cx", 0)), "depth": int(tc.depth())}


# ------------------------------------------------------------------------------- query complexity
def mc_samples(a, rel=0.1):
    """Monte Carlo samples for relative standard error `rel`."""
    return (1 - a) / (rel ** 2 * a)


def qae_calls(a, rng, rel=0.1, reps=200, sweep=(1.0, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12, 0.08)):
    """Oracle calls for IQAE to reach relative RMSE `rel`, calibrated by emulation on the exact a.

    For each IQAE precision target r we run `reps` emulated estimations and record (mean calls,
    realised relative RMSE). IQAE's realised error falls ~ 1/calls, so C = median(calls * rmse)
    and calls(rel) = C / rel. The per-point data are returned for inspection.
    """
    from .iqae import iqae
    pts = []
    for r in sweep:
        runs = [iqae(a, r * a, rng) for _ in range(reps)]
        est = np.array([x["estimate"] for x in runs])
        rmse = float(np.sqrt(np.mean((est - a) ** 2)) / a)
        pts.append((float(np.mean([x["calls"] for x in runs])), rmse))
    C = float(np.median([c * e for c, e in pts]))
    return C / rel, pts
