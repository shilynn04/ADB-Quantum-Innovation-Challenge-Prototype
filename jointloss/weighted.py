"""Importance-weighted amplitude encoding (IW-QAE) for the ADB benchmark.

Plain QAE encodes a = E_p[f] with f in [0,1]. For a rare joint tail, a is tiny and the QAE
relative error ~ 1/(M sqrt(a)) is poor. IW-QAE loads a proposal q (the same half-true /
half-loss-tilted proposal the brief prescribes for classical importance sampling) and rotates
the objective qubit by the path weight:

    A_q |0> = sum_x sqrt(q(x)) |x> ( sqrt(1-g(x)) |0> + sqrt(g(x)) |1> ),
    g(x)    = f(x) * w(x) / W,   w(x) = prod_y p(s_y)/q(s_y),   W = max_x f(x) w(x),

so the encoded amplitude is a' = E_q[g] = a / W and the estimator is a_hat = W * a'_hat.
If W < 1 (the proposal over-weights the paths where f > 0), the amplitude is boosted and the
relative error per oracle call improves by sqrt(1/W).

Circuit realisation (costed in resources/build_circuits.py): the log-weight is accumulated in
a fixed-point register, log w(x) = sum_y l(s_y), l(s) = ln p(s) - ln q(s) looked up per year,
and the final rotation is a uniformly-controlled RY over that register. `delta` is the
fixed-point resolution. Rounding l(s) would bias the estimate (about 1-3% at delta = 1/16), so
instead we *snap the proposal to the grid*: with l_hat(s) = l(s) rounded to the grid, load
q_snap(s) = p(s) exp(-l_hat(s)) / Z. Then ln p - ln q_snap = l_hat + ln Z exactly, the weights
are exactly representable, and the estimator is unbiased for any delta. `bias_rel` is
returned (and asserted ~0) as a check.
"""
import numpy as np
from .model import annual_distribution, annual_loss, target_functions
from .qae import path_payoffs, term_path_distribution


def brief_proposal(sc, p=None, lam=0.5, power=1):
    """q = (1-lam) p + lam * (p * loss^power, normalised). lam=0.5, power=1 is the brief's proposal."""
    p = annual_distribution(sc) if p is None else p
    t = p * annual_loss(sc) ** power
    return (1 - lam) * p + lam * t / t.sum()


def encode(sc, j, q, delta=None, p=None, F=None):
    """Encoded amplitude for target j under proposal q.

    Returns dict with: a (true target, scaled to [0,1]), scale, a_enc (= E_q[g]), W,
    gain (= sqrt(a_enc / a): relative-error improvement per oracle call vs plain QAE),
    bias_rel (exact relative bias of W*a_enc vs a caused by fixed-point rounding),
    g_path (per-path rotation probabilities, 10^6), L_bits (register width if delta given).
    """
    p = annual_distribution(sc) if p is None else p
    Fp = path_payoffs(target_functions(sc) if F is None else F)
    scale = Fp[j].max()
    f = Fp[j] / scale
    a = float(term_path_distribution(p) @ f)
    ell = np.log(p) - np.log(q)
    L_bits, u = None, None
    if delta is not None:
        lo = np.floor(ell.min() / delta) * delta
        u = np.round((ell - lo) / delta).astype(int)            # non-negative integers per state
        q = p * np.exp(-(u * delta + lo))
        q = q / q.sum()                                          # grid-snapped proposal
        ell = np.log(p) - np.log(q)                              # = u*delta + lo + ln Z, exactly
        L_bits = int(np.ceil(np.log2(3 * u.max() + 1)))
    Q = term_path_distribution(q)
    Lw = (ell[:, None, None] + ell[None, :, None] + ell[None, None, :]).reshape(-1)
    with np.errstate(divide="ignore"):
        lf = np.where(f > 0, np.log(np.where(f > 0, f, 1.0)), -np.inf)
    lg = Lw + lf
    lW = lg.max()
    g = np.exp(lg - lW)                                          # in [0,1], 0 where f == 0
    a_enc = float(Q @ g)
    W = float(np.exp(lW))
    return {"a": a, "scale": float(scale), "a_enc": a_enc, "W": W,
            "gain": float(np.sqrt(a_enc / a)), "bias_rel": float((W * a_enc - a) / a),
            "g_path": g, "L_bits": L_bits, "q": q, "u": u}
