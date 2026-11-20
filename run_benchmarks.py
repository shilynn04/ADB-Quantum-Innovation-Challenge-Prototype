"""Reproduce all prototype results: exact check, classical baselines vs simulated QAE, error-vs-queries."""
import json, time, sys
import numpy as np
from jointloss.model import SCENARIOS, annual_distribution, target_functions, exact_targets, TARGETS
from jointloss import baselines as B, qae

REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
BUDGETS = [2**k for k in range(10, 17)]       # classical paths / samples
SEED = 2026
rng = np.random.default_rng(SEED)
res = {"seed": SEED, "reps": REPS}

# ---- 1. exact reference + statevector validation of the amplitude model --------------------
res["exact"] = {n: exact_targets(sc).tolist() for n, sc in SCENARIOS.items()}
sc = SCENARIOS["adb-base"]; p = annual_distribution(sc); F = target_functions(sc)
Fp = qae.path_payoffs(F)
th, chk = qae.statevector_check(p, Fp[4])
res["statevector_check_both_exhausted"] = {"theta": th, "rows": chk,
                                           "max_abs_err": max(abs(a - b) for _, a, b in chk)}
print("statevector check max |sim - sin^2((2k+1)theta)| =", res["statevector_check_both_exhausted"]["max_abs_err"])

# scale factors so every target is an expectation of f in [0,1] for QAE
Lmax = 2 * (sc.eq_limit + sc.rain_limit)
SCALE = np.array([Lmax, 1, 1, Lmax - sc.T, 1])

def rel_rmse(est, truth):
    return float(np.sqrt(np.mean((est - truth) ** 2)) / truth)

def rel_med(est, truth):
    return float(np.median(np.abs(est - truth)) / truth)

# ---- 2. error vs. budget on adb-base, all 5 targets, all methods -----------------------------
truth = exact_targets(sc)
sweep = {m: {t: [] for t in TARGETS} for m in list(B.METHODS) + ["QAE (ideal)"]}
for n in BUDGETS:
    for name, fn in B.METHODS.items():
        ests = np.array([fn(sc, n, rng, p, F) for _ in range(REPS)])
        for j, t in enumerate(TARGETS):
            sweep[name][t].append((n, rel_rmse(ests[:, j], truth[j]), rel_med(ests[:, j], truth[j])))
    print("classical done n =", n, flush=True)

SHOTS = 50
for m in range(2, 11):
    calls = SHOTS * (1 + 2 * (2**m - 1) + m)
    for j, t in enumerate(TARGETS):
        a = truth[j] / SCALE[j]
        e = [qae.mlae(a, SHOTS, m, rng)[0] * SCALE[j] for _ in range(REPS * 2)]
        sweep["QAE (ideal)"][t].append((calls, rel_rmse(np.array(e), truth[j]), rel_med(np.array(e), truth[j])))
res["sweep_base"] = sweep

# noisy QAE (illustrative depolarising-contrast model, NOT hardware data)
noisy = {}
for kappa in (1e-4, 1e-3):
    noisy[str(kappa)] = {t: [] for t in TARGETS}
    for m in range(2, 11):
        calls = SHOTS * (1 + 2 * (2**m - 1) + m)
        for j, t in enumerate(TARGETS):
            a = truth[j] / SCALE[j]
            e = [qae.mlae(a, SHOTS, m, rng, kappa)[0] * SCALE[j] for _ in range(REPS * 2)]
            noisy[str(kappa)][t].append((calls, rel_rmse(np.array(e), truth[j]), rel_med(np.array(e), truth[j])))
res["sweep_noisy_qae"] = noisy

# ---- 3. all scenarios at one budget (2^14 paths vs ~2e4 oracle calls) -------------------------
N0, M0 = 2**15, 8
tab = {}
for name, s in SCENARIOS.items():
    pp, FF = annual_distribution(s), target_functions(s)
    tr = exact_targets(s)
    sc_ = np.array([2 * (s.eq_limit + s.rain_limit), 1, 1, 2 * (s.eq_limit + s.rain_limit) - s.T, 1])
    row = {}
    for mname, fn in B.METHODS.items():
        ests = np.array([fn(s, N0, rng, pp, FF) for _ in range(REPS)])
        row[mname] = [rel_rmse(ests[:, j], tr[j]) for j in range(5)]
        row[mname + " (median)"] = [rel_med(ests[:, j], tr[j]) for j in range(5)]
    q, qm = [], []
    for j in range(5):
        e = np.array([qae.mlae(tr[j] / sc_[j], SHOTS, M0, rng)[0] * sc_[j] for _ in range(REPS * 2)])
        q.append(rel_rmse(e, tr[j])); qm.append(rel_med(e, tr[j]))
    row["QAE (ideal)"] = q; row["QAE (ideal) (median)"] = qm
    tab[name] = row
    print("scenario", name, "done", flush=True)
res["table_all_scenarios"] = {"classical_budget": N0,
                              "qae_oracle_calls": SHOTS * (1 + 2 * (2**M0 - 1) + M0), "rel_rmse": tab}
json.dump(res, open("results/results.json", "w"), indent=1)
print("saved results/results.json")
