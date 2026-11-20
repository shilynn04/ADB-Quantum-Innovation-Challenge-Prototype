import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
r = json.load(open("results/results.json"))
sw, nz = r["sweep_base"], r["sweep_noisy_qae"]
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
for a, (t, ttl) in zip(ax, [("both_exhausted_prob", "Both bonds exhausted (3.2e-5)"),
                            ("loss_exceed_T_prob", "Pr(L > USD 80m) (1.2%)"),
                            ("expected_loss_usd_m", "Expected principal loss")]):
    for m, d in sw.items():
        x = [v[0] for v in d[t]]
        a.loglog(x, [v[1] for v in d[t]], "o-" if "QAE" not in m else "s--", label=m + (" – RMSE" if "QAE" in m else ""))
    d = sw["QAE (ideal)"][t]
    a.loglog([v[0] for v in d], [max(v[2], 1e-4) for v in d], "k:", label="QAE (ideal) – median")
    a.set_title(ttl); a.set_xlabel("budget (paths / oracle calls)"); a.set_ylabel("relative error"); a.grid(alpha=.3, which="both")
ax[0].legend(fontsize=7)
plt.tight_layout(); plt.savefig("results/error_vs_budget.png", dpi=140)
