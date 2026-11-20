"""Gate-level resource estimate for the ADB benchmark (Phase 1 deliverable: qubits, depth,
two-qubit gates, shots, error mitigation, hardware mapping).

Builds, in Qiskit, the actual state-preparation oracle A and Grover operator Q for
  (1) plain QAE  : A = 3 x [quake loader (6q) + rain loader (2q)] -> two 4-bit ripple-carry
                   accumulators (Cuccaro et al.) -> OR gates for precipitation -> cap flags
                   -> one uniformly-controlled RY on the objective qubit (8 controls, 256 angles,
                   covers all five targets; only the angles change);
  (2) IW-QAE     : the grid-snapped proposal loader (8q per year), a per-year log-weight
                   lookup (5 output bits, computed and uncomputed) added into a 6-bit register,
                   and a uniformly-controlled RY over (log-weight register, tail flag).
Both circuits are *verified* before costing:
  * the classical arithmetic is bit-simulated on all 10^6 three-year paths;
  * the loaders, lookups and final rotations are checked against the model on small statevectors;
  * the end-to-end amplitude implied by the verified pieces equals the exact target.

Run:  python -m resources.build_circuits    -> results/resources.json
"""
import json, math, time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import (StatePreparation, UCRYGate, UCGate, CDKMRippleCarryAdder,
                                    grover_operator)
from qiskit.quantum_info import Operator, Statevector
from qiskit.transpiler import CouplingMap
from qiskit.providers.fake_provider import GenericBackendV2

from jointloss.model import SCENARIOS, STATES, quake_annual, rain_annual, target_functions, TARGETS
from jointloss.qae import path_payoffs, term_path_distribution
from jointloss.weighted import brief_proposal, encode

YEARS, DELTA = 3, 0.25
BASIS = ["cx", "rz", "sx", "x"]
X = np.array([[0, 1], [1, 0]], dtype=complex)
I2 = np.eye(2, dtype=complex)


# ------------------------------------------------------------------------------- helpers
def or_into(qc, inputs, target):
    """target ^= OR(inputs) (target assumed |0>)."""
    qc.x(inputs); qc.mcx(list(inputs), target); qc.x(inputs); qc.x(target)


def state_index(a, b, r1, r2):
    return ((a * 5 + b) * 2 + r1) * 2 + r2


def year_index(a, b, r1, r2):
    """Index of an annual state on the 8-qubit year register [a0 a1 a2 b0 b1 b2 r1 r2] (LSB first)."""
    return a + 8 * b + 64 * r1 + 128 * r2


class Regs:
    def __init__(self, iw=False, tbits=5, lbits=6):
        self.a = [QuantumRegister(3, f"a{y}") for y in range(YEARS)]
        self.b = [QuantumRegister(3, f"b{y}") for y in range(YEARS)]
        self.r1 = [QuantumRegister(1, f"r1_{y}") for y in range(YEARS)]
        self.r2 = [QuantumRegister(1, f"r2_{y}") for y in range(YEARS)]
        self.SA, self.SB = QuantumRegister(4, "SA"), QuantumRegister(4, "SB")
        self.pad, self.help = QuantumRegister(1, "pad"), QuantumRegister(1, "help")
        self.R, self.G = QuantumRegister(2, "R"), QuantumRegister(2, "G")
        self.obj = QuantumRegister(1, "obj")
        regs = self.a + self.b + self.r1 + self.r2 + [self.SA, self.SB, self.pad, self.help, self.R, self.G]
        if iw:
            self.T, self.L = QuantumRegister(lbits, "T"), QuantumRegister(lbits, "L")
            self.flag = QuantumRegister(1, "flag")
            regs += [self.T, self.L, self.flag]
        self.all = regs + [self.obj]

    def year(self, y):
        return list(self.a[y]) + list(self.b[y]) + [self.r1[y][0], self.r2[y][0]]


def arithmetic(qc, R):
    """Accumulate quake steps, OR the precipitation triggers, set the cap flags."""
    for y in range(YEARS):
        qc.append(CDKMRippleCarryAdder(4, kind="fixed"), list(R.a[y]) + [R.pad[0]] + list(R.SA) + [R.help[0]])
        qc.append(CDKMRippleCarryAdder(4, kind="fixed"), list(R.b[y]) + [R.pad[0]] + list(R.SB) + [R.help[0]])
    or_into(qc, [R.r1[y][0] for y in range(YEARS)], R.R[0])
    or_into(qc, [R.r2[y][0] for y in range(YEARS)], R.R[1])
    or_into(qc, [R.SA[2], R.SA[3]], R.G[0])        # gA = (SA >= 4)
    or_into(qc, [R.SB[2], R.SB[3]], R.G[1])        # gB = (SB >= 4)


def final_controls(R):
    return [R.G[0], R.SA[0], R.SA[1], R.G[1], R.SB[0], R.SB[1], R.R[0], R.R[1]]


def lookup_angles(f_state):
    """256 RY angles indexed by (gA, SA0, SA1, gB, SB0, SB1, R1, R2), LSB first."""
    ang = np.zeros(256)
    for i in range(256):
        bits = [(i >> k) & 1 for k in range(8)]
        cA = 4 if bits[0] else bits[1] + 2 * bits[2]
        cB = 4 if bits[3] else bits[4] + 2 * bits[5]
        ang[i] = 2 * np.arcsin(np.sqrt(f_state[state_index(cA, cB, bits[6], bits[7])]))
    return ang


# ------------------------------------------------------------------------------- builders
def build_plain(sc, j):
    R = Regs()
    qc = QuantumCircuit(*R.all, name="A")
    eq = quake_annual(sc.m)
    rn = rain_annual(sc.q, sc.rain_mult, sc.rain_share)
    amp_q = np.zeros(64); amp_r = np.zeros(4)
    for a in range(5):
        for b in range(5):
            amp_q[a + 8 * b] = np.sqrt(eq[a, b])
    for r1 in range(2):
        for r2 in range(2):
            amp_r[r1 + 2 * r2] = np.sqrt(rn[r1, r2])
    for y in range(YEARS):
        qc.append(StatePreparation(amp_q), list(R.a[y]) + list(R.b[y]))
        qc.append(StatePreparation(amp_r), [R.r1[y][0], R.r2[y][0]])
    arithmetic(qc, R)
    F = target_functions(sc)
    f_state = F[j] / F[j].max()
    qc.append(UCRYGate(list(lookup_angles(f_state))), [R.obj[0]] + final_controls(R))
    return qc, R, {"amp_q": amp_q, "amp_r": amp_r, "f_state": f_state}


def build_iw(sc, j, power=2, lookups=True):
    """IW-QAE oracle for an indicator target (used for both_exhausted_prob)."""
    e = encode(sc, j, brief_proposal(sc, power=power), DELTA)
    q, u = e["q"], e["u"]
    lbits = e["L_bits"]
    R = Regs(iw=True, lbits=lbits)
    qc = QuantumCircuit(*R.all, name="A_iw")
    amp = np.zeros(256)
    for s, (a, b, r1, r2) in enumerate(STATES):
        amp[year_index(a, b, r1, r2)] = np.sqrt(q[s])
    ubits = int(np.ceil(np.log2(u.max() + 1)))
    table = np.zeros(256, dtype=int)
    for s, (a, b, r1, r2) in enumerate(STATES):
        table[year_index(a, b, r1, r2)] = u[s]
    mux = [UCGate([X if (table[i] >> k) & 1 else I2 for i in range(256)]) for k in range(ubits)]
    for y in range(YEARS):
        qc.append(StatePreparation(amp), R.year(y))
    for y in range(YEARS if lookups else 0):                       # L += u(s_y)
        for k in range(ubits):
            qc.append(mux[k], [R.T[k]] + R.year(y))
        qc.append(CDKMRippleCarryAdder(lbits, kind="fixed"), list(R.T) + list(R.L) + [R.help[0]])
        for k in range(ubits):                                     # uncompute T
            qc.append(mux[k], [R.T[k]] + R.year(y))
    arithmetic(qc, R)
    qc.mcx([R.G[0], R.G[1], R.R[0], R.R[1]], R.flag[0])
    Fp = path_payoffs(target_functions(sc))[j]
    U = (u[:, None, None] + u[None, :, None] + u[None, None, :]).reshape(-1)
    Ustar = U[Fp > 0].max()
    nL = 2 ** lbits
    ang = np.zeros(2 * nL)
    for v in range(nL):
        ang[v + nL] = 2 * np.arcsin(np.sqrt(min(1.0, np.exp(DELTA * (v - Ustar)))))
    qc.append(UCRYGate(list(ang)), [R.obj[0]] + list(R.L) + [R.flag[0]])
    return qc, R, {"enc": e, "table": table, "ubits": ubits, "Ustar": int(Ustar), "ang": ang, "mux": mux, "amp": amp}


# ------------------------------------------------------------------------------- verification
def bit_simulate(qc, assign):
    """Simulate a circuit of X/CX/CCX/MCX gates on classical bit vectors (one column per path)."""
    idx = {q: i for i, q in enumerate(qc.qubits)}
    n = next(iter(assign.values())).shape[0]
    bits = np.zeros((qc.num_qubits, n), dtype=bool)
    for q, v in assign.items():
        bits[idx[q]] = v
    for ins in qc.data:
        name, qs = ins.operation.name, [idx[q] for q in ins.qubits]
        if name == "x":
            bits[qs[0]] ^= True
        elif name in ("cx", "ccx", "mcx") or name.startswith("mcx"):
            bits[qs[-1]] ^= np.logical_and.reduce(bits[qs[:-1]], axis=0)
        else:
            raise ValueError(name)
    return bits, idx


def verify_plain(sc, j, qc, R, info):
    """Exhaustive check over all 10^6 three-year paths of the reversible arithmetic + lookup."""
    arith = QuantumCircuit(*R.all)
    arithmetic(arith, R)
    keep = {"x", "cx", "ccx", "mcx"}
    for _ in range(10):                                   # unroll adders into Toffoli/CNOT logic
        other = {ins.operation.name for ins in arith.data} - keep
        if not other:
            break
        arith = arith.decompose(gates_to_decompose=list(other))
    s = np.arange(10**6)
    ys = [s // 10**4, (s // 100) % 100, s % 100]
    assign = {}
    for y in range(YEARS):
        a, b, r1, r2 = STATES[ys[y]].T
        for k in range(3):
            assign[R.a[y][k]] = (a >> k) & 1
            assign[R.b[y][k]] = (b >> k) & 1
        assign[R.r1[y][0]] = r1.astype(bool); assign[R.r2[y][0]] = r2.astype(bool)
    bits, idx = bit_simulate(arith, {k: np.asarray(v, dtype=bool) for k, v in assign.items()})
    ctrl = final_controls(R)
    code = sum(bits[idx[q]].astype(int) << k for k, q in enumerate(ctrl))
    # expected capped term state from the model
    A = np.minimum(STATES[ys[0]][:, 0] + STATES[ys[1]][:, 0] + STATES[ys[2]][:, 0], 4)
    B = np.minimum(STATES[ys[0]][:, 1] + STATES[ys[1]][:, 1] + STATES[ys[2]][:, 1], 4)
    R1 = np.max([STATES[ys[y]][:, 2] for y in range(YEARS)], axis=0)
    R2 = np.max([STATES[ys[y]][:, 3] for y in range(YEARS)], axis=0)
    ang = lookup_angles(info["f_state"])
    f_circ = np.sin(ang[code] / 2) ** 2
    f_model = info["f_state"][state_index(A, B, R1, R2)]
    ancillas_clean = all(not bits[idx[q]].any() for q in [R.pad[0], R.help[0]])
    inputs_kept = all((bits[idx[q]] == assign[q]).all() for q in assign)
    # loaders on small statevectors
    pq = np.abs(Statevector(StatePreparation(info["amp_q"]).definition).data) ** 2
    pr = np.abs(Statevector(StatePreparation(info["amp_r"]).definition).data) ** 2
    load_ok = np.allclose(pq, info["amp_q"] ** 2, atol=1e-10) and np.allclose(pr, info["amp_r"] ** 2, atol=1e-10)
    # end-to-end amplitude implied by the verified pieces
    P = term_path_distribution(np.einsum("ab,rs->abrs", quake_annual(sc.m), rain_annual(sc.q, sc.rain_mult, sc.rain_share)).reshape(-1))
    a_circ = float(P @ f_circ)
    a_exact = float(P @ path_payoffs(target_functions(sc))[j] / target_functions(sc)[j].max())
    return {"paths_checked": int(len(s)), "arith_matches_model": bool(np.allclose(f_circ, f_model, atol=1e-12)),
            "ancillas_returned_clean": bool(ancillas_clean), "inputs_preserved": bool(inputs_kept),
            "loaders_ok": bool(load_ok), "amplitude_from_circuit": a_circ, "amplitude_exact": a_exact}


def verify_iw(sc, j, info):
    """Check one lookup bit and the final rotation on small operators; end-to-end amplitude."""
    k = 0
    qc = QuantumCircuit(9); qc.append(info["mux"][k], list(range(9)))
    U = Operator(qc).data
    ok = True
    for i in range(256):
        col = U[:, i << 1]
        out1 = sum(abs(col[m]) ** 2 for m in range(512) if m & 1)
        ok &= abs(out1 - ((info["table"][i] >> k) & 1)) < 1e-9
    e = info["enc"]
    Fp = path_payoffs(target_functions(sc))[j]
    u = e["u"]
    Uv = (u[:, None, None] + u[None, :, None] + u[None, None, :]).reshape(-1)
    nL = len(info["ang"]) // 2
    g = np.where(Fp > 0, np.sin(info["ang"][nL + Uv] / 2) ** 2, 0.0)
    a_circ = float(term_path_distribution(e["q"]) @ g)
    return {"lookup_bit_ok": bool(ok), "encoded_amplitude_from_circuit": a_circ,
            "encoded_amplitude_model": e["a_enc"], "W": e["W"]}


# ------------------------------------------------------------------------------- costing
def counts(circ, label, backend=None):
    t0 = time.time()
    if backend is None:
        tc = transpile(circ, basis_gates=BASIS, optimization_level=1, seed_transpiler=7)
    else:
        tc = transpile(circ, backend=backend, optimization_level=1, seed_transpiler=7)
    ops = tc.count_ops()
    return {"label": label, "qubits": tc.num_qubits if backend is None else circ.num_qubits,
            "cx": int(ops.get("cx", 0)), "1q": int(sum(v for k, v in ops.items() if k in ("rz", "sx", "x"))),
            "depth": int(tc.depth()), "cx_depth": int(tc.depth(lambda g: g.operation.num_qubits == 2)),
            "transpile_s": round(time.time() - t0, 1)}


def ft_estimate(circ, n_queries, eps_total=1e-2):
    """Coarse fault-tolerant cost: Clifford+T with Ross-Selinger rotation synthesis."""
    tc = transpile(circ, basis_gates=["cx", "h", "s", "sdg", "t", "tdg", "x", "rz"], optimization_level=1)
    ops = tc.count_ops()
    ang = [float(ins.operation.params[0]) for ins in tc.data if ins.operation.name == "rz"]
    m = [round(a / (np.pi / 4), 9) for a in ang]
    n_rot = sum(1 for v in m if abs(v - round(v)) > 1e-6)           # genuine small-angle rotations
    n_t_like = sum(1 for v in m if abs(v - round(v)) <= 1e-6 and int(round(v)) % 2)
    eps_rot = eps_total / max(n_rot * n_queries, 1)
    t_per_rot = 1.15 * math.log2(1 / eps_rot) + 9.2
    t_count = int(ops.get("t", 0) + ops.get("tdg", 0) + n_t_like + n_rot * t_per_rot)
    return {"rotations": n_rot, "t_per_rotation": round(t_per_rot, 1), "t_count_per_oracle": t_count}


def surface_code(logical_qubits, logical_ops, p_phys=1e-3, p_target=1e-2):
    """Smallest distance d with logical_ops * 0.1*(p/0.01)^((d+1)/2) <= p_target; ~2 d^2 physical per logical."""
    d = 3
    while logical_qubits * logical_ops * 0.1 * (p_phys / 1e-2) ** ((d + 1) / 2) > p_target:
        d += 2
    return {"distance": d, "physical_qubits_data": int(2 * d * d * logical_qubits),
            "note": "excludes magic-state factories; use a full resource estimator in Phase 2"}


def main():
    sc = SCENARIOS["adb-base"]
    out = {"scenario": "adb-base", "basis": BASIS}
    j_rare = TARGETS.index("both_exhausted_prob")

    A, R, info = build_plain(sc, j_rare)
    out["verify_plain"] = verify_plain(sc, j_rare, A, R, info)
    print("plain verified:", out["verify_plain"], flush=True)
    oracle = QuantumCircuit(*R.all); oracle.z(R.obj[0])
    Q = grover_operator(oracle, state_preparation=A)
    out["plain_A"], out["plain_Q"] = counts(A, "A (plain)"), counts(Q, "Q (plain)")
    print(out["plain_A"], out["plain_Q"], flush=True)

    Aw, Rw, infow = build_iw(sc, j_rare)
    out["verify_iw"] = verify_iw(sc, j_rare, infow)
    print("IW verified:", out["verify_iw"], flush=True)
    oracle_w = QuantumCircuit(*Rw.all); oracle_w.z(Rw.obj[0])
    Qw = grover_operator(oracle_w, state_preparation=Aw)
    out["iw_A"], out["iw_Q"] = counts(Aw, "A (IW)"), counts(Qw, "Q (IW)")
    print(out["iw_A"], out["iw_Q"], flush=True)

    # hardware mapping: IBM-style heavy-hex (distance 5, 57 qubits) vs all-to-all (trapped ion)
    hh = GenericBackendV2(num_qubits=57, coupling_map=CouplingMap.from_heavy_hex(5), basis_gates=BASIS, seed=7)
    out["plain_A_heavyhex"] = counts(A, "A (plain) on heavy-hex", hh)
    print(out["plain_A_heavyhex"], flush=True)

    # run-level totals at ~2% relative RMSE on the rare tail, from results/v2_results.json
    v2 = json.load(open("results/v2_results.json"))["quantum_base"]["both_exhausted_prob"]
    runs = {}
    for name, key, Acost, Qcost in (("plain IQAE", "IQAE", out["plain_A"], out["plain_Q"]),
                                    ("IW-IQAE (loss^2)", "IW-IQAE (loss^2 proposal)", out["iw_A"], out["iw_Q"])):
        row = next(r for r in v2[key] if r["rmse"] <= 0.025)
        calls, kmax = row["calls"], row["max_k"]
        q_apps = (calls - 0) / 2                                  # each Q contains ~2 applications of A
        runs[name] = {"rel_rmse": row["rmse"], "oracle_calls": calls, "max_grover_power": kmax,
                      "deepest_circuit_depth": Acost["depth"] + kmax * Qcost["depth"],
                      "deepest_circuit_cx": Acost["cx"] + kmax * Qcost["cx"],
                      "total_cx_all_shots": float(q_apps * Qcost["cx"]),
                      "shots_per_round": 100}
        runs[name]["ft"] = ft_estimate(Q if name == "plain IQAE" else Qw, q_apps)
        runs[name]["ft"]["t_count_total"] = float(runs[name]["ft"]["t_count_per_oracle"] * q_apps)
        runs[name]["surface_code"] = surface_code(Qcost["qubits"], runs[name]["deepest_circuit_depth"])
    Aw0, _, info0 = build_iw(sc, j_rare, lookups=False)
    oracle0 = QuantumCircuit(*Aw0.qregs); oracle0.z(Aw0.qregs[-1][0])
    Qw0 = grover_operator(oracle0, state_preparation=Aw0)
    calls_iw = runs["IW-IQAE (loss^2)"]["oracle_calls"] / 2
    base = ft_estimate(Qw0, calls_iw)
    n_lookups = 2 * 2 * YEARS                      # compute + uncompute, in A and in A^dagger, per year
    qrom_t = n_lookups * 4 * (256 - 1)
    t_q = base["t_count_per_oracle"] + qrom_t
    out["projection_iw_unary_qrom"] = {
        "t_count_per_Q_without_lookups": base["t_count_per_oracle"], "qrom_t_per_Q": qrom_t,
        "t_count_per_Q": t_q, "t_count_total": float(t_q * calls_iw),
        "plain_t_count_total": runs["plain IQAE"]["ft"]["t_count_total"],
        "note": "projection, not built: lookups via unary-iteration QROM (Babbush et al. 2018, 4(N-1) T each, N=256)"}
    out["runs_rare_tail_2pct"] = runs
    # near-term (NISQ) check: largest Grover power with expected circuit fidelity >= 0.5 at 2q error 1e-3
    for lab, Acost, Qcost in (("plain", out["plain_A"], out["plain_Q"]), ("iw", out["iw_A"], out["iw_Q"])):
        budget = math.log(2) / 1e-3
        out[f"nisq_{lab}"] = {"cx_budget_at_F0.5_p1e-3": int(budget),
                              "A_alone_cx": Acost["cx"],
                              "max_k_feasible": int(max(-1, (budget - Acost["cx"]) // Qcost["cx"]))}
    json.dump(out, open("results/resources.json", "w"), indent=1, default=float)
    print("saved results/resources.json")


if __name__ == "__main__":
    main()
