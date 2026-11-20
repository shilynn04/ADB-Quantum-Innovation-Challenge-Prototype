# v2: Iterative QAE, importance-weighted QAE, and a gate-level resource estimate

This extends the Phase 1 prototype. The exact model (`jointloss/model.py`), the brief's
classical baselines and the original MLAE results are unchanged; everything below is additive.
All quantum numbers are **exact measurement statistics of ideal circuits** (the
`sin²((2k+1)θ)` law, verified against a full statevector simulation), not hardware runs.

| New file | Purpose |
|---|---|
| `jointloss/iqae.py` | Iterative QAE (Grinko et al. 2021): confidence intervals, no aliasing plateau |
| `jointloss/weighted.py` | Importance-weighted amplitude encoding (IW-QAE), grid-snapped so it is exactly unbiased |
| `run_benchmarks_v2.py` | IQAE / IW-IQAE vs the brief's baselines **and two stronger classical baselines** |
| `make_plots_v2.py` | `results/v2_error_vs_budget.png` (all five targets) |
| `resources/build_circuits.py` | Builds and **verifies** the oracles in Qiskit 2.6.2, then counts qubits, CX, depth, T |
| `results/v2_results.json`, `results/resources.json` | Raw outputs (seed 2026) |

## 1. Accuracy per query (evaluation criterion 1)

**IQAE** replaces the fixed-schedule MLAE. MLAE's error stalled near 15% on the rare tail
because the likelihood sometimes locked onto a wrong mode. IQAE keeps shrinking (2.0% at
2.0e5 oracle calls) and reports a confidence interval; empirical coverage at α = 0.05 is
0.95–1.00 in every cell.

**IW-IQAE.** For a rare target the amplitude a is tiny and QAE's relative error ~ 1/(M√a) is
poor. We load an importance-sampling proposal q instead of p and rotate the objective qubit by
the path weight: g(x) = f(x)·w(x)/W, w = Π p/q, W = max f·w. The encoded amplitude becomes
a' = a/W, so the relative error per query improves by √(1/W).

* **Unbiased by construction.** Rounding the log-weights to a fixed-point register would bias
  the estimate by about 1–3%. Instead we *snap the proposal to the grid*:
  q_snap ∝ p·exp(−round(ln p/q)). Its weights are exactly representable, so the bias is zero
  (checked to 1e-13). A 6-qubit log-weight register (δ = 1/4) is enough.
* **Gain.** √(1/W) = 2.6× (brief's proposal) or 4.0× (loss² tilt) on the rare tail and the
  stop-loss, about 2× on Pr(L > 80m). There is **no gain on the joint-attachment probability**
  (0.97×), which is not rare.
* **Two negative results** that shaped the design: stratifying by which years pay gives QAE
  **no** gain (≈1.0×), even though it helps classical sampling 2–3×; and weighting each year
  with its own ancilla loses the gain (≤0.5×), because the normaliser is then set by the
  zero-loss state. QAE's cost depends on the *worst-case* weight, whereas classical IS
  depends on the *average* (second moment). Only path-level weights work.

**Equal-budget comparison, all five scenarios.** IW-IQAE (brief's proposal) is run to a 10%
target, and every classical method gets the same mean budget. Relative RMSE:

| Scenario | Target | Budget | IW-IQAE | Best classical (method) |
|---|---|---|---|---|
| adb-base | both bonds exhausted | 58k | **0.018** | 0.117 (IS) |
| adb-independent | both bonds exhausted | 223k | **0.017** | 0.149 (IS) |
| adb-common-shock | both bonds exhausted | 65k | **0.013** | 0.117 (IS) |
| adb-rain-stress | both bonds exhausted | 65k | **0.015** | 0.072 (IS) |
| adb-rain-cover | both bonds exhausted | 56k | **0.018** | 0.142 (IS) |
| adb-base | Pr(L > USD 80m) | 5.5k | **0.017** | 0.045 (stratified IS) |
| adb-base | stop-loss above USD 80m | 6.6k | **0.019** | 0.039 (stratified IS) |
| adb-base | both countries pay | 5.8k | **0.022** | 0.028 (stratified IS) |
| adb-base | expected principal loss | 1.5k | 0.022 | **0.005 (stratified IS)** |

Full table for every scenario and target: `results/v2_results.json → equal_budget_all_scenarios`.

**Honest reading.**
* On the **rare joint tail**, ideal IW-IQAE is 4–9× more accurate than the best classical
  method at the same budget, in all five scenarios. This is where the brief locates the
  bottleneck.
* On **smooth or common targets**, strong classical methods win or tie: stratified IS is about
  4× better on expected loss, and Sobol is competitive. We report this rather than hide it.
* The two extra classical baselines (IS with a loss² tilt, and stratified IS with pilot-based
  Neyman allocation) are stronger than the brief's four on several targets. They are included
  so the quantum method is compared against the best classical methods, not only the easiest.
* RMSE spikes in the plot are the rare (about 1–2%) IQAE runs whose confidence interval
  missed. Medians are smooth; coverage is listed per cell in the JSON.
* A *query* is one application of the oracle A. Per-query cost differs a lot between plain
  and weighted oracles (Section 2), so per-query advantage is not wall-clock advantage.

## 2. Resource estimate (Phase 1 deliverable)

Both oracles are built gate by gate and **verified before costing**:
* The plain oracle's reversible arithmetic is bit-simulated on **all 10⁶ three-year paths**
  and matches the model exactly. Ancillas return clean and inputs are preserved.
* The loaders, lookup bits and final rotations are checked on small exact operators.
* The amplitude implied by the verified circuit equals the exact target:
  3.1633e-5 (plain) and 5.0234e-4 (IW, encoded).

**Oracle structure (plain).** 3 × [quake loader on 6 qubits + rain loader on 2 qubits] →
two 4-bit Cuccaro ripple-carry accumulators → OR gates for the rain triggers → cap flags → one
uniformly-controlled RY with 8 controls (256 angles). The same circuit serves all five targets;
only the angles change.

| Circuit (transpiled to CX + 1q, all-to-all) | Logical qubits | CX | Depth | CX depth |
|---|---|---|---|---|
| A, plain | 39 | 850 | 1,235 | 623 |
| Q, plain (Grover operator) | 39 | 6,494 | 10,915 | 4,993 |
| A, importance-weighted | 52 | 24,545 | 47,199 | 16,293 |
| Q, importance-weighted | 52 | 55,288 | 105,078 | 38,047 |
| A, plain, routed to IBM heavy-hex (57q) | 39 | 2,293 | 1,903 | 1,233 |

**Rare tail to about 2% relative error (emulated runs, 100 shots per IQAE round):**

| | Plain IQAE | IW-IQAE (loss²) |
|---|---|---|
| Relative RMSE achieved | 2.0% | 1.4% |
| Oracle calls (A applications) | 2.0e5 | **6.3e4** |
| Largest Grover power k | 1,331 | **334** |
| T-count total (Ross–Selinger synthesis, ε_total = 1e-2) | 4.2e9 | 8.2e10 as built · **4.1e9 with QROM** |
| Surface-code distance at p = 1e-3 (coarse) | 19 (about 28k physical data qubits) | 21 (about 46k) |

* **Per gate, the weight lookup is the lever.** As built, each log-weight lookup is a
  Qiskit multiplexer made of small-angle rotations (about 50k rotations per Q). Replacing it
  with a unary-iteration QROM (Babbush et al. 2018; 4(N−1) T gates, no rotations) is
  *projected*, not built, to bring IW-IQAE to **4.1e9 T at 1.4% error versus 4.2e9 T at 2.0%
  for plain QAE**. That is break-even in T-count, more accurate, with 3.2× fewer queries and a
  4× shorter maximal coherent circuit.
* **Reflection cost.** Q is 7.6× A because the 39-qubit zero-reflection is synthesised
  without ancillas. An ancilla-assisted (v-chain) multi-controlled Z should cut this
  substantially (Phase 2).
* **Near-term hardware.** At a two-qubit error of 1e-3, a circuit fidelity of 0.5 allows about
  690 CX. The plain A alone needs 850, so **no Grover iteration is feasible on today's NISQ
  devices**. QAE's advantage on this problem is a fault-tolerant proposition, which we state
  plainly.
* **Error mitigation** (for the small-k demonstrations planned in Phase 2): readout-error
  mitigation; zero-noise extrapolation on k ∈ {0, 1, 2}; and a noise-aware likelihood (the
  contrast-decay model already in `qae.mlae`) or noise-robust IQAE variants. Dynamical
  decoupling on idle qubits.
* **Hardware modality.** All-to-all connectivity avoids the 2.7× CX routing overhead seen on
  heavy-hex, so trapped-ion (or neutral-atom with movable qubits) is preferred for near-term
  demonstrations. Superconducting or neutral-atom surface-code machines are the fault-tolerant
  target. Factories and full layout are left to a dedicated estimator (for example Azure
  Quantum Resource Estimator or Qualtran) in Phase 2.

## 3. Reproduce

```bash
pip install -r requirements.txt qiskit==2.6.2
python run_benchmarks_v2.py 40          # a few minutes, one CPU core -> results/v2_results.json
python make_plots_v2.py                 # -> results/v2_error_vs_budget.png
python -m resources.build_circuits      # ~1 min -> results/resources.json (includes all checks)
```

Environment as run: Python 3.13, NumPy 2.x, SciPy 1.x, Qiskit 2.6.2, CPU only, seed 2026.

## 4. Open items for the Phase 2 plan

1. Build the unary-iteration QROM and ancilla-assisted reflection; re-cost with a full
   fault-tolerant estimator.
2. IW encoding for expectation targets needs f(final) inside the final rotation. It is costed
   here only for the indicator (rare-tail) target.
3. **Scaling to n countries** (evaluation criterion 2): exploit conditional independence
   given shared events (the latent-factor structure of Egger et al. 2021), with tensor-train
   references for n ≥ 3 where exact enumeration is impractical.
4. The official benchmark repository (World Bank event-loss-table cases) is not yet covered.

## AI-use disclosure

The v2 code, benchmarks and this note were drafted with the assistance of Claude (Anthropic).
The authors are responsible for reviewing and verifying them before submission.
