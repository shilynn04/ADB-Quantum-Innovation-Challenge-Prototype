"""Plot v2 error-versus-budget for all five targets -> results/v2_error_vs_budget.png.

Classical curves: MC, Sobol, Importance from results/results.json (brief baselines, unchanged);
Importance (loss^2) and Stratified IS from results/v2_results.json.
Quantum curves: MLAE (original prototype), IQAE, IW-IQAE (loss^2 proposal).
Classical = solid lines with circles; quantum = dashed lines with squares (identity is never
colour alone). Palette: validated 8-slot categorical order, fixed (not cycled).
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

old = json.load(open("results/results.json"))
v2 = json.load(open("results/v2_results.json"))
exact = old["exact"]["adb-base"]

PANELS = [("both_exhausted_prob", "Both bonds exhausted", exact[4], "{:.1e}"),
          ("loss_exceed_T_prob", "Pr(L > USD 80m)", exact[2], "{:.2%}"),
          ("stop_loss_usd_m", "Expected loss above USD 80m", exact[3] * 1e6, "USD {:,.0f}"),
          ("joint_attachment_prob", "Both countries pay", exact[1], "{:.2%}"),
          ("expected_loss_usd_m", "Expected principal loss", exact[0], "USD {:.2f}m")]

SERIES = [  # (label, colour, quantum?, getter)
    ("MC", "#2a78d6", False, lambda t: [(n, e) for n, e, _ in old["sweep_base"]["MC"][t]]),
    ("Sobol", "#eb6834", False, lambda t: [(n, e) for n, e, _ in old["sweep_base"]["Sobol"][t]]),
    ("Importance (brief)", "#1baf7a", False, lambda t: [(n, e) for n, e, _ in old["sweep_base"]["Importance"][t]]),
    ("Importance (loss²)", "#eda100", False, lambda t: [(n, e) for n, e, _ in v2["classical_extra_base"]["Importance (loss^2)"][t]]),
    ("Stratified IS", "#e87ba4", False, lambda t: [(n, e) for n, e, _ in v2["classical_extra_base"]["Stratified IS"][t]]),
    ("MLAE (prototype v1)", "#008300", True, lambda t: [(n, e) for n, e, _ in old["sweep_base"]["QAE (ideal)"][t]]),
    ("IQAE", "#6250d6", True, lambda t: [(r["calls"], r["rmse"]) for r in v2["quantum_base"][t]["IQAE"]]),
    ("IW-IQAE (loss²)", "#e34948", True, lambda t: [(r["calls"], r["rmse"]) for r in v2["quantum_base"][t]["IW-IQAE (loss^2 proposal)"]]),
]

INK, MUTED, GRID = "#22211f", "#6b6a64", "#e4e3de"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK})
fig, axes = plt.subplots(2, 3, figsize=(13, 7.6))
for ax, (t, title, val, fmt) in zip(axes.flat, PANELS):
    for label, col, quantum, get in SERIES:
        pts = sorted(get(t))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.8,
                ls="--" if quantum else "-", marker="s" if quantum else "o", ms=4.5,
                mec="white", mew=0.8, label=label)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_title(f"{title}  (exact {fmt.format(val)})", fontsize=10, loc="left")
    ax.set_xlabel("budget: classical paths  /  quantum oracle calls")
    ax.set_ylabel("relative RMSE")
    ax.grid(True, which="major", color=GRID, lw=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(2e2, 3e6)
leg_ax = axes.flat[5]; leg_ax.axis("off")
h, l = axes.flat[0].get_legend_handles_labels()
leg_ax.legend(h, l, loc="center left", frameon=False, fontsize=9.5,
              title="solid ● classical    dashed ■ quantum (ideal, emulated)", title_fontsize=9)
fig.suptitle("ADB benchmark (adb-base): accuracy per query. Quantum = exact measurement statistics of "
             "ideal circuits, not hardware.", x=0.01, ha="left", fontsize=10.5, color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig("results/v2_error_vs_budget.png", dpi=160, facecolor="white")
print("saved results/v2_error_vs_budget.png")
