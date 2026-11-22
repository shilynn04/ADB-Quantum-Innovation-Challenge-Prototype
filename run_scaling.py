"""Scaling study for evaluation criterion 2 -> results/scaling.json, results/scaling.png.

1. Validate the n-country conditional-exact model against the brief at n = 2 (all five scenarios),
   and the quantum term-level oracle against it by full statevector simulation at n = 2 and 3.
2. Exact portfolio targets for n = 2..20 (synthetic portfolios cloned from KGZ/TJK parameters).
3. Budget for 10% relative error: Monte Carlo samples vs IQAE oracle calls (IQAE calibrated by
   emulation on the exact amplitude for each n).
4. Oracle A and Grover operator Q built in Qiskit for n = 2..20; qubits, CX, depth.
Runtime: about two minutes on one CPU core.
"""
import json, time
import numpy as np
from jointloss.scaling import (validate_n2, targets, build_term_oracle, oracle_amplitude,
                               oracle_counts, mc_samples, qae_calls)

SEED = 2026
NS = list(range(2, 21))
NS_QAE = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
NS_GATES = [2, 3, 4, 5, 6, 8, 10, 12, 16, 20]
rng = np.random.default_rng(SEED)
t0 = time.time()
res = {"seed": SEED, "model": "single regional factor; countries cloned alternately from KGZ/TJK; adb-base parameters",
       "thresholds": "T_n = 40*n USD m (half of total principal; equals the brief's USD 80m at n = 2)"}

# 1. validation
res["validation_n2_vs_brief"] = validate_n2()
res["validation_oracle_statevector"] = {}
for n in (2, 3):
    a_sv = oracle_amplitude(build_term_oracle(n)); a_ex = targets(n)["all_exhausted"]
    res["validation_oracle_statevector"][n] = {"statevector": a_sv, "exact": a_ex, "rel_diff": abs(a_sv - a_ex) / a_ex}
print("validation done", flush=True)

# 2. exact targets
res["targets"] = {n: targets(n) for n in NS}
res["state_space"] = {n: {"annual_states": f"10^{n}", "three_year_paths": f"10^{3 * n}"} for n in NS}

# 3. query complexity at 10% relative error
qc_tab = {}
for n in NS_QAE:
    row = {}
    for key in ("all_exhausted", "at_least_2_exhausted", "loss_exceed_T"):
        if key != "all_exhausted" and n not in (2, 5, 10, 20):
            continue
        a = res["targets"][n][key]
        calls, pts = qae_calls(a, rng, reps=100)
        row[key] = {"a": a, "mc_samples": mc_samples(a), "qae_calls": calls,
                    "ratio_mc_over_qae": mc_samples(a) / calls, "iqae_points": pts}
    qc_tab[n] = row
    print("query complexity n =", n, flush=True)
res["budget_10pct"] = qc_tab

# 4. gate counts
from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator
gates = {}
for n in NS_GATES:
    A = build_term_oracle(n)
    oracle = QuantumCircuit(A.num_qubits); oracle.z(A.num_qubits - 1)
    Q = grover_operator(oracle, state_preparation=A)
    ca, cq = oracle_counts(A), oracle_counts(Q)
    budget = np.log(2) / 1e-3                       # CX allowed for circuit fidelity >= 0.5 at 2q error 1e-3
    gates[n] = {"A": ca, "Q": cq, "nisq_max_k": int(max(-1, (budget - ca["cx"]) // cq["cx"]))}
    print("gates n =", n, ca, cq, flush=True)
res["oracle_gates"] = gates
ns = np.array(NS_GATES)
for key in ("qubits", "cx", "depth"):
    for which in ("A", "Q"):
        y = np.array([gates[n][which][key] for n in NS_GATES])
        slope, icpt = np.polyfit(ns, y, 1)
        res.setdefault("linear_fits", {})[f"{which}_{key}"] = {"per_country": float(slope), "intercept": float(icpt),
                                                               "max_abs_residual": float(np.max(np.abs(y - (slope * ns + icpt))))}
res["runtime_s"] = round(time.time() - t0, 1)
json.dump(res, open("results/scaling.json", "w"), indent=1, default=float)
print("saved results/scaling.json in", res["runtime_s"], "s")

# plot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
INK, MUTED, GRID = "#22211f", "#6b6a64", "#e4e3de"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK})
fig, ax = plt.subplots(2, 2, figsize=(11, 7.4))


def style(a, title, ylabel, log=True):
    a.set_title(title, loc="left", fontsize=10); a.set_xlabel("countries in portfolio, n"); a.set_ylabel(ylabel)
    if log:
        a.set_yscale("log")
    a.grid(True, color=GRID, lw=0.6); a.set_axisbelow(True)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)


for key, lab, col in (("all_exhausted", "all n bonds exhausted", C1), ("at_least_2_exhausted", "at least 2 bonds exhausted", C2),
                      ("loss_exceed_T", "portfolio loss > 40n USD m", C3)):
    ax[0, 0].plot(NS, [res["targets"][n][key] for n in NS], color=col, lw=1.8, marker="o", ms=4, mec="white", label=lab)
style(ax[0, 0], "Joint-tail probabilities (exact, 3-year term)", "probability")
ax[0, 0].legend(frameon=False, fontsize=8.5)

nq = [n for n in NS_QAE]
ax[0, 1].plot(nq, [qc_tab[n]["all_exhausted"]["mc_samples"] for n in nq], color=C1, lw=1.8, marker="o", ms=4, mec="white", label="Monte Carlo samples")
ax[0, 1].plot(nq, [qc_tab[n]["all_exhausted"]["qae_calls"] for n in nq], color=C2, lw=1.8, ls="--", marker="s", ms=4, mec="white", label="IQAE oracle calls (emulated)")
style(ax[0, 1], "Budget for 10% relative error: 'all bonds exhausted'", "samples / oracle calls")
ax[0, 1].legend(frameon=False, fontsize=8.5)

ax[1, 0].plot(NS_GATES, [gates[n]["A"]["qubits"] for n in NS_GATES], color=C3, lw=1.8, marker="o", ms=4, mec="white", label="logical qubits (= 4n + 7)")
style(ax[1, 0], "Oracle width", "logical qubits", log=False)
ax[1, 0].legend(frameon=False, fontsize=8.5)

ax[1, 1].plot(NS_GATES, [gates[n]["A"]["cx"] for n in NS_GATES], color=C4, lw=1.8, marker="o", ms=4, mec="white", label="oracle A")
ax[1, 1].plot(NS_GATES, [gates[n]["Q"]["cx"] for n in NS_GATES], color=C1, lw=1.8, ls="--", marker="s", ms=4, mec="white", label="Grover operator Q")
style(ax[1, 1], "Two-qubit gates (CX), built and transpiled in Qiskit", "CX count", log=False)
ax[1, 1].legend(frameon=False, fontsize=8.5)
fig.suptitle("Scaling with portfolio size (single regional factor; naive state space 10^n per year, 10^(3n) paths)",
             x=0.01, ha="left", fontsize=10.5, color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig("results/scaling.png", dpi=160, facecolor="white")
print("saved results/scaling.png")
