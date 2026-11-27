"""fig20: how feature importance moved when the legitimate class gained
path-bearing URLs. Shows the shortcut weakening rather than disappearing."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
NAVY, ORANGE = "#122a4d", "#e67e22"

df = pd.read_csv(os.path.join(ART, "feature_importance_v2.csv"))
df = df.sort_values("baseline_importance", ascending=False).head(10).iloc[::-1]

y = np.arange(len(df))
h = 0.38
fig, ax = plt.subplots(figsize=(9.4, 4.6))
b1 = ax.barh(y + h / 2, df["baseline_importance"], h, color=NAVY,
             label="baseline (PhiUSIIL only)")
b2 = ax.barh(y - h / 2, df["rebalanced_importance"], h, color=ORANGE,
             label="rebalanced (+ collected legitimate URLs)")
ax.bar_label(b1, fmt="%.3f", fontsize=7, padding=2, color=NAVY)
ax.bar_label(b2, fmt="%.3f", fontsize=7, padding=2, color=ORANGE)
ax.set_yticks(y)
ax.set_yticklabels(df["feature"], fontsize=9)
ax.set_xlabel("Gini importance", fontsize=9)
ax.set_xlim(0, df["baseline_importance"].max() * 1.28)
ax.set_title("Feature importance before and after the legitimate class was extended",
             fontsize=11, color=NAVY, pad=10)
ax.legend(fontsize=8, frameon=False, loc="lower right")
ax.grid(axis="x", alpha=0.25, linewidth=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
out = os.path.join(ART, "figs", "fig20_importance_shift.png")
fig.savefig(out, dpi=200, facecolor="white", bbox_inches="tight")
print("fig20_importance_shift.png")
print(df[["feature", "baseline_importance", "rebalanced_importance"]].iloc[::-1].to_string(index=False))