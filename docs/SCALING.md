# Scaling to larger portfolios (evaluation criterion 2)

Code: `jointloss/scaling.py`, `run_scaling.py` (about 30 s on one CPU core) → `results/scaling.json`, `results/scaling.png`.

## The n-country model, and why it is exact

The brief's two-country model generalises without approximation:

* **Caps commute with sums.** For non-negative steps, min(min(x,4) + y, 4) = min(x + y, 4). So a
  country's capped 3-year quake total is min(own + shared, 4). Here *own* is compound Poisson
  over the whole term (rate 3(Λᵢ − c), step law wᵢ = λᵢₖ/Λᵢ), and *shared* is the sum of K
  independent size draws from wᵢ, with K ~ Poisson(3c).
* **Shared events hit every country** (one regional factor). Their sizes are drawn
  independently per country, exactly as in the brief.
* **Precipitation.** The brief's 2×2 law (Eqs. 5–6) is exactly "own rate μᵢ − c_r plus a
  shared rate c_r". A country's trigger fires if any own or shared event occurs in the term.
* **Conditional independence.** Given the latent pair (K capped at 4, shared-rain indicator),
  countries are independent. Every portfolio target is then a mixture over 10 latent states of
  per-country products or convolutions: cost O(n × loss grid), instead of 10ⁿ annual states
  or 10³ⁿ three-year paths.

**Validation.** At n = 2 the conditional method reproduces the brief's exact enumeration for all
five scenarios and all five targets. The largest relative difference is 5e-14.

**Synthetic portfolios.** Countries are cloned alternately from the Kyrgyz Republic and
Tajikistan parameters. The shared rate is c = m·meanᵢ(condᵢ·Λᵢ), with cond = 0.075 / 0.074, and
c_r = 0.25·μ (adb-base). The threshold is Tₙ = 40n USD m, half the total principal, which equals
the brief's USD 80m at n = 2.

## Quantum oracle: linear in n, built and verified

Only term totals enter the targets, and their law is known in closed form given the latent
factor. So the oracle loads the term law directly, not three annual states plus adders:

* a latent register (3 qubits for K ∈ {0,…,4}, exact; 1 qubit for shared rain);
* per country, a K-multiplexed 3-qubit loader (uniformly-controlled RY gates, 56 CX) and an
  own-rain qubit;
* the payoff AND(aᵢ = 4) ∧ (shared rain ∨ AND own-rain), as multi-controlled X gates.

**Verified by full statevector simulation** at n = 2 and 3: the result equals the exact
amplitude to 1e-13. Transpiled to {CX, RZ, SX, X} in Qiskit 2.6.2:

* **qubits = 4n + 7, exactly**;
* **CX(A) = 70.0·n + 0.6** (largest residual 1.5);
* **depth(A) = 277·n**;
* CX(Q) ≈ 716·n − 225. It is dominated by the 4n+7-qubit zero-reflection, synthesised without
  ancillas, and ancilla-assisted synthesis should reduce it.

At n = 2 this term-level oracle needs **142 CX**, against 850 for the annual-level oracle in
`resources/`. A single A circuit (k = 0) fits a 0.5-fidelity budget at 2-qubit error 1e-3 up to
n ≈ 8. Grover iterations do not, so advantage remains a fault-tolerant proposition.

## Results: rare joint tails get rarer, and that is where QAE's scaling matters

Budget for 10% relative error on P(all n bonds exhausted):
* **Monte Carlo:** (1−a)/(0.01·a) samples.
* **IQAE:** calls calibrated by emulating IQAE on the exact a for each n (realised RMSE ∝
  1/calls; median constant).

| n | annual states | a = P(all exhausted) | MC samples | IQAE calls | MC / IQAE | qubits | CX(A) | CX(Q) |
|---|---|---|---|---|---|---|---|---|
| 2 | 10^2 | 3.16e-05 | 3.2e+06 | 2.6e+04 | 123× | 15 | 142 | 1012 |
| 3 | 10^3 | 5.25e-06 | 1.9e+07 | 6.8e+04 | 280× | 19 | 210 | 1648 |
| 4 | 10^4 | 1.46e-06 | 6.8e+07 | 1.1e+05 | 621× | 23 | 280 | 2410 |
| 5 | 10^5 | 5.42e-07 | 1.8e+08 | 2.2e+05 | 829× | 27 | 350 | 3304 |
| 6 | 10^6 | 1.85e-07 | 5.4e+08 | 3.7e+05 | 1,460× | 31 | 420 | 4326 |
| 8 | 10^8 | 3.62e-08 | 2.8e+09 | 7.6e+05 | 3,645× | 39 | 560 | 5918 |
| 10 | 10^10 | 1.16e-08 | 8.6e+09 | 1.4e+06 | 6,067× | 47 | 700 | 7236 |
| 12 | 10^12 | 4.83e-09 | 2.1e+10 | 2.0e+06 | 10,109× | 55 | 840 | 8544 |
| 15 | 10^15 | 1.71e-09 | 5.8e+10 | 3.6e+06 | 16,194× | 67 | 1050 (fit) | – |
| 20 | 10^20 | 3.22e-10 | 3.1e+11 | 8.5e+06 | 36,787× | 87 | 1400 | 13776 |

Other targets (in `results/scaling.json`):
* **P(at least 2 bonds exhausted)** *rises* with n (3.2e-5 → 2.7e-3), so its MC/IQAE ratio
  falls (129× → 12×).
* **P(portfolio loss > 40n)** plateaus near 0.5% (ratio about 10×). One shared quake moves the
  whole portfolio, so this tail does **not** diversify away. That is a direct, quantitative
  illustration of why the joint tail decides whether pooling saves money.

## Honest framing

1. **For this single-factor model, a classical conditional DP is also exact and polynomial.**
   We use it as the ground truth that makes benchmarking at large n possible. It is not a
   quantum result.
2. **The quantum oracle exploits the same conditional independence.** Its width (4n + 7) and
   gate count (about 70 CX per country) grow linearly in n, and linearly in the number of
   latent-factor qubits.
3. **Where a quantum route matters.** With many factors, heterogeneous pairwise links or
   data-driven copulas, the treewidth grows and exact DP becomes exponential. Sampling is then
   the only option. QAE's 1/√a versus Monte Carlo's 1/a matters most exactly where the brief
   says the bottleneck is, because the joint-tail amplitude a shrinks with n.
4. **IW-QAE** (docs/V2_NOTES.md) gains a further 2.6–4× on the rare tail at n = 2. Its weight
   bound W needs a maximum over paths, which we computed by enumeration at n = 2 only. A
   factor-conditional bound is Phase 2 work.
5. **Quantum-inspired route.** Tensor networks (MPS / tensor trains) give exact answers for
   moderate-treewidth dependence on classical hardware. They are the planned Phase 2 reference
   between DP and sampling.

## AI-use disclosure

Drafted with the assistance of Claude (Anthropic); the authors are responsible for review and verification.
