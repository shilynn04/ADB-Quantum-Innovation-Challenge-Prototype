"""v2 benchmark: Iterative QAE and importance-weighted IQAE against classical baselines.

Adds to run_benchmarks.py (which is left unchanged):
  * IQAE (Grinko et al. 2021) instead of fixed-schedule MLAE: confidence intervals, no aliasing plateau.
  * IW-IQAE: importance-weighted amplitude encoding (jointloss/weighted.py) with the brief's
    proposal, grid-snapped (delta = 1/4, 6-bit log-weight register) so it is exactly unbiased.
  * Two stronger classical baselines, so the quantum method is not compared only against the
    brief's four: importance sampling with a loss^2 tilt, and stratified importance sampling
    (strata = which of the 3 years have a payout; pilot + Neyman allocation).

Budget = sampled paths (classical) or applications of the state-preparation oracle A (quantum;
a shot at Grover power k costs 2k+1). Query counts, not wall-clock: see docs/V2_NOTES.md.

Usage:  python run_benchmarks_v2.py [reps]      -> results/v2_results.json
"""
import itertools, json, sys
import numpy as np
from jointloss.model import SCENARIOS, TARGETS, annual_distribution, target_functions, exact_targets
from jointloss.baselines import _walk, _invert, METHODS as BRIEF_METHODS
from jointloss.weighted import brief_proposal, encode
from jointloss.iqae import iqae

REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
Q_REPS = 5 * REPS                       # quantum runs are cheap to emulate
SEED, DELTA, YEARS = 2026, 0.25, 3
BUDGETS = [2**k for k in range(10, 17)]
REL = [0.6, 0.4, 0.25, 0.15, 0.1, 0.06, 0.04, 0.025, 0.015, 0.01]
rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------- classical extras
def is_est(n, rng, p, F, q):
    st = _invert(rng.random((n, YEARS)), np.cumsum(q))
    w = np.prod(p[st] / q[st], axis=1)
    return (F[:, _walk(st)] * w).mean(1)


def strat_is(n, rng, p, F, q, pilot_frac=0.1, only=None):
    """Strata = zero/non-zero pattern of the three years; IS with q inside non-zero years."""
    p0 = p[0]
    nz = np.arange(len(p)) != 0
    qn = np.where(nz, q, 0); qn /= qn.sum()
    ratio = np.where(nz, p / np.where(qn > 0, qn, 1), 0) / (1 - p0)   # p_nz / q_nz
    cdf = np.cumsum(qn)
    pats = [z for z in itertools.product([0, 1], repeat=YEARS) if any(z)]
    pis = np.array([p0 ** (YEARS - sum(z)) * (1 - p0) ** sum(z) for z in pats])

    def draw(z, m):
        st = np.zeros((m, YEARS), dtype=np.int64); w = np.ones(m)
        for y, on in enumerate(z):
            if on:
                s = _invert(rng.random(m), cdf); st[:, y] = s; w *= ratio[s]
        return F[:, _walk(st)] * w                       # (targets, m)

    m0 = max(int(pilot_frac * n / len(pats)), 4)
    pilot = [draw(z, m0) for z in pats]
    out = np.zeros(F.shape[0])
    for j in (range(F.shape[0]) if only is None else [only]):
        sd = np.array([pl[j].std() for pl in pilot]) + 1e-300
        rest = max(n - m0 * len(pats), 0)
        alloc = np.floor(rest * pis * sd / (pis * sd).sum()).astype(int)
        est = 0.0
        for z, pl, k, pi in zip(pats, pilot, alloc, pis):
            vals = pl[j] if k == 0 else np.concatenate([pl[j], draw(z, k)[j]])
            est += pi * vals.mean()
        out[j] = est
    return out


def rel_rmse(e, t): return float(np.sqrt(np.mean((np.asarray(e) - t) ** 2)) / t)
def rel_med(e, t): return float(np.median(np.abs(np.asarray(e) - t)) / t)


# ---------------------------------------------------------------- quantum (emulated)
def iqae_sweep(a_enc, mult, truth):
    """Run IQAE on encoded amplitude a_enc; estimate = mult * a_hat. Returns rows over REL."""
    rows = []
    for r in REL:
        runs = [iqae(a_enc, r * a_enc, rng) for _ in range(Q_REPS)]
        est = np.array([x["estimate"] for x in runs]) * mult
        cov = np.mean([x["ci"][0] * mult <= truth <= x["ci"][1] * mult for x in runs])
        rows.append({"target_rel": r, "calls": float(np.mean([x["calls"] for x in runs])),
                     "max_k": int(max(x["max_k"] for x in runs)),
                     "rmse": rel_rmse(est, truth), "median": rel_med(est, truth), "coverage": float(cov)})
    return rows


def main():
    res = {"seed": SEED, "reps_classical": REPS, "reps_quantum": Q_REPS, "delta": DELTA}
    sc = SCENARIOS["adb-base"]
    p, F = annual_distribution(sc), target_functions(sc)
    truth = exact_targets(sc)
    q1, q2 = brief_proposal(sc, p), brief_proposal(sc, p, power=2)

    # encodings
    enc = {}
    for j, t in enumerate(TARGETS):
        e1, e2 = encode(sc, j, q1, DELTA, p, F), encode(sc, j, q2, DELTA, p, F)
        assert abs(e1["bias_rel"]) < 1e-9 and abs(e2["bias_rel"]) < 1e-9
        enc[t] = {"scale": e1["scale"], "a_plain": e1["a"],
                  "iw_brief": {k: e1[k] for k in ("a_enc", "W", "gain", "L_bits")},
                  "iw_loss2": {k: e2[k] for k in ("a_enc", "W", "gain", "L_bits")}}
    res["encodings"] = enc
    print("encodings done", flush=True)

    # classical extras on adb-base (brief's four are in results/results.json, same seed/budgets)
    extra = {"Importance (loss^2)": {t: [] for t in TARGETS}, "Stratified IS": {t: [] for t in TARGETS}}
    for n in BUDGETS:
        e_is2 = np.array([is_est(n, rng, p, F, q2) for _ in range(REPS)])
        e_sis = np.array([strat_is(n, rng, p, F, q1) for _ in range(REPS)])
        for j, t in enumerate(TARGETS):
            extra["Importance (loss^2)"][t].append((n, rel_rmse(e_is2[:, j], truth[j]), rel_med(e_is2[:, j], truth[j])))
            extra["Stratified IS"][t].append((n, rel_rmse(e_sis[:, j], truth[j]), rel_med(e_sis[:, j], truth[j])))
        print("classical extras n =", n, flush=True)
    res["classical_extra_base"] = extra

    # quantum sweeps on adb-base
    qs = {}
    for t in TARGETS:
        e = enc[t]; s = e["scale"]
        qs[t] = {"IQAE": iqae_sweep(e["a_plain"], s, e["a_plain"] * s),
                 "IW-IQAE (brief proposal)": iqae_sweep(e["iw_brief"]["a_enc"], s * e["iw_brief"]["W"], e["a_plain"] * s),
                 "IW-IQAE (loss^2 proposal)": iqae_sweep(e["iw_loss2"]["a_enc"], s * e["iw_loss2"]["W"], e["a_plain"] * s)}
        print("quantum sweep", t, flush=True)
    res["quantum_base"] = qs

    # equal-budget table, all scenarios: IW-IQAE at target 10% vs classical at the same mean budget
    table = {}
    for name, s_ in SCENARIOS.items():
        pp, FF, tr = annual_distribution(s_), target_functions(s_), exact_targets(s_)
        qq = brief_proposal(s_, pp)
        row = {}
        for j, t in enumerate(TARGETS):
            e = encode(s_, j, qq, DELTA, pp, FF)
            runs = [iqae(e["a_enc"], 0.1 * e["a_enc"], rng) for _ in range(Q_REPS)]
            est = np.array([x["estimate"] for x in runs]) * e["scale"] * e["W"]
            M = int(np.mean([x["calls"] for x in runs]))
            cl = {}
            for mname, fn in (("MC", BRIEF_METHODS["MC"]), ("Sobol", BRIEF_METHODS["Sobol"]),
                              ("Importance", BRIEF_METHODS["Importance"])):
                ests = np.array([fn(s_, M, rng, pp, FF)[j] for _ in range(REPS)])
                cl[mname] = rel_rmse(ests, tr[j])
            ests = np.array([strat_is(M, rng, pp, FF, qq, only=j)[j] for _ in range(REPS)])
            cl["Stratified IS"] = rel_rmse(ests, tr[j])
            row[t] = {"budget": M, "IW-IQAE": rel_rmse(est, tr[j]),
                      "IW-IQAE coverage": float(np.mean([x["ci"][0] * e["scale"] * e["W"] <= tr[j] <= x["ci"][1] * e["scale"] * e["W"] for x in runs])),
                      **cl}
        table[name] = row
        print("scenario", name, flush=True)
    res["equal_budget_all_scenarios"] = table
    json.dump(res, open("results/v2_results.json", "w"), indent=1)
    print("saved results/v2_results.json")


if __name__ == "__main__":
    main()
