# ADB Quantum Challenge - Phase 1 lightweight prototype
Joint-loss modelling for the Kyrgyz Republic / Tajikistan disaster-relief-bond benchmark.

> **Status: Phase 1 prototype.** Everything below is simulation on a laptop CPU. No quantum hardware was used.
> Quantum results are *ideal-circuit simulations* (plus an illustrative noise model) - not hardware measurements.

## What this repo does
| Module | Purpose |
|---|---|
| `jointloss/model.py` | Exact reference model (brief steps 1-8): compound-Poisson earthquake CTMC with shared events, correlated precipitation, 100-state annual law, 3-year capped convolution, 5 focus targets, 5 scenarios. **Reproduces every value in the brief's Table 5.** |
| `jointloss/baselines.py` | Classical baselines from step 9: Monte Carlo, scrambled Sobol (8 scrambles), stratified (first-payout-year), importance sampling (½ true + ½ loss-tilted). |
| `jointloss/qae.py` | Amplitude-estimation engine: payoff oracle over all 10^6 three-year paths, an explicit 2^21x2 **statevector simulation** of Grover iterates `Q^k A|0>` (matches `sin²((2k+1)θ)` to 1e-15), and a maximum-likelihood AE (MLAE) estimator with binomial shot noise and an optional per-call contrast-decay noise model. |
| `run_benchmarks.py` | Runs everything -> `results/results.json`. `make_plots.py` -> `results/error_vs_budget.png`. |

## Reproduce
```bash
pip install -r requirements.txt
python run_benchmarks.py 40     # 40 repetitions, seed 2026, ~1 min on one CPU core
python make_plots.py
```

## Results (adb-base unless stated; relative error vs exact, 40-80 repetitions)
Budget is "paths" for classical methods and "applications of the state-preparation oracle A" for QAE
(one QAE shot at Grover power k costs 2k+1 applications of A).

Rare target `both_exhausted` (exact 3.2e-5), RMSE / median relative error:

| Budget | MC | Sobol | Stratified | Importance | QAE (ideal, MLAE) |
|---|---|---|---|---|---|
| ~3.3e4 paths / 2.6e4 calls | 1.06 / 0.97 | 1.00 / 0.48 | 0.48 / 0.39 | 0.20 / 0.15 | 0.15 / 0.09 |
| 6.6e4 paths / 5.2e4 calls | 0.69 / 0.52 | 0.64 / 0.52 | 0.32 / 0.27 | 0.12 / 0.08 | 0.14 / 0.03 |

Smooth targets (e.g. expected loss, `Pr(L>80m)`): QAE error falls roughly ∝ 1/calls (≈0.09 -> 0.002 between 450 and 2.6e4 calls), versus ∝ 1/√N for MC; scrambled Sobol is already about as accurate as ideal QAE on expected loss (0.001 at 3.3e4 paths).

### Honest reading
* Importance sampling is a **strong classical baseline** on the rare joint tail; ideal QAE only edges it (≈1.3× lower RMSE at ~2.6e4 calls, mixed at 5e4) and its RMSE plateaus around 0.15 because MLAE with a fixed schedule sometimes aliases to a wrong mode, even while its *median* error keeps shrinking.
* A QAE "oracle call" (load three annual states + capped-sum + payoff) is far more expensive than a classical path evaluation, so equal-count comparisons favour QAE. This is a query-complexity comparison, **not** a wall-clock or hardware claim.
* Illustrative noise (`κ=1e-3` contrast decay per oracle call, an assumption, not measured) leaves the exhaustion RMSE essentially unchanged (≈0.15-0.18) and erodes the median improvement at the deepest circuits.
* The 2-country benchmark is small: exact enumeration takes ~0.2 ms, so this prototype validates *methodology and accounting*, not practical advantage. The scaling claim (10^n states) needs the Phase 2 work below.

## Resource estimate (ADB 2-country, 3-year term, coarse)
* Annual-state register: 100 states -> 7 qubits; three years -> 21 qubits (product-state loading, 3 × a 7-qubit loader)
* Running capped total (a,b ≤4; r1,r2 ≤1): 3+3+1+1 = 8 qubits; payoff/comparator ancillas ≈ 6; objective qubit 1 -> **≈ 36 qubits** (target: gate-based, fault-tolerant; statevector-simulable on a laptop up to ~21 qubits in `qae.py`)
* Deepest MLAE run in the sweep: k = 2^9 -> Grover power 512, ~1.0e5 A-applications total. Gate counts per A not yet compiled (Phase 2: Qiskit/Cirq transpile for 2q-gate and T counts).
* Scaling note: for n countries the annual state space is 10^n (≈3.3n qubits per year); loading a general joint distribution is the open bottleneck (cf. Herbert 2021, Chakrabarti et al. 2021).

## Phase 2 plan (summary)
1. Compile A and Q to a gate set; report qubits, depth, 2-qubit/T counts and shots.
2. Replace ideal MLAE with Iterative QAE and run noisy simulation on a GPU.
3. Quantum-inspired route: tensor-train/MPS representation of the joint annual law to extend to n = 5+ countries (10^5 states), benchmarked against MC/IS.
4. Variance-reduced QAE (importance-weighted amplitude) for the rare joint tail.

## Environment and hardware
Python 3.12.3, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2 (as run); CPU only (1 core). Fixed seed 2026.

## AI-use disclosure
This prototype's code, benchmark harness and README were drafted with the assistance of Claude (Anthropic). The authors are responsible for reviewing and verifying the code and results before submission. Model equations and benchmark definitions are from the ADB Quantum Challenge brief.
