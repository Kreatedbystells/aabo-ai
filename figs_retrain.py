"""Figures for the retraining and reputation-layer results (Chapter Four).

fig18  the four model variants measured on field data rather than on the training set:
       false positives on legitimate URLs that carry a path, recall on hostile URLs,
       accuracy on the whole field test, and false positives on the thirty hard cases,
       each with and without the reputation layer.
fig19  why a popularity-based allow-list is weak for Nigerian users: the rank of each
       locally relevant domain against the two global tiers.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
FIGS = os.path.join(ART, "figs")
os.makedirs(FIGS, exist_ok=True)

NAVY, ORANGE, GREEN, RED, GREY = "#122a4d", "#e67e22", "#1b6b3a", "#b3261e", "#6b7280"
R = json.load(open(os.path.join(ART, "retrain.json")))
NAMES = ["baseline", "rebalanced", "rebalanced_no_path", "rebalanced_balanced"]
PRETTY = ["baseline\n(PhiUSIIL only)", "rebalanced\n(+ collected + shapes)",
          "rebalanced\n(no path_length)", "rebalanced\n(balanced classes)"]


def v(name, key, where="model_only"):
    return R["models"][name][key][where]


def dep(name, key):
    return R["models"][name][key]["with_reputation_layer"]


x = np.arange(len(NAMES))
w = 0.64
fig, axes = plt.subplots(1, 4, figsize=(16.4, 4.4))

# (a) false positives on legitimate URLs that carry a path
a = axes[0]
b = a.bar(x, [v(n, "field_legit_with_paths")["false_positive_rate"] for n in NAMES], w,
          color=RED)
a.bar_label(b, fmt="%.1f", fontsize=8, padding=1)
a.set_ylim(0, 118)
a.set_title("Legitimate URLs with a path\ncalled phishing, %", fontsize=9.5, color=NAVY, pad=8)

# (b) recall on hostile URLs
a = axes[1]
b = a.bar(x, [v(n, "field_phishing")["recall"] for n in NAMES], w, color=GREY)
a.bar_label(b, fmt="%.1f", fontsize=8, padding=1)
a.set_ylim(60, 104)
a.set_title("Hostile URLs detected, %", fontsize=9.5, color=NAVY, pad=8)

# (c) accuracy on the whole field test, with and without the reputation layer
a = axes[2]
b1 = a.bar(x - w / 2, [v(n, "field_all")["accuracy"] for n in NAMES], w / 2,
           color=NAVY, label="classifier alone")
b2 = a.bar(x + w / 2, [dep(n, "field_all_deployed")["accuracy"] for n in NAMES], w / 2,
           color=GREEN, label="+ reputation layer")
a.bar_label(b1, fmt="%.1f", fontsize=7, padding=1)
a.bar_label(b2, fmt="%.1f", fontsize=7, padding=1)
a.set_ylim(60, 110)
a.set_title("Accuracy on the whole field test, %", fontsize=9.5, color=NAVY, pad=8)
a.legend(fontsize=7.5, frameon=False, loc="lower right")

# (d) false positives on the thirty hard cases, with and without the reputation layer
a = axes[3]
b1 = a.bar(x - w / 2, [v(n, "hard_cases")["false_positive_rate"] for n in NAMES], w / 2,
           color=RED, label="classifier alone")
b2 = a.bar(x + w / 2, [dep(n, "hard_cases_deployed")["false_positive_rate"] for n in NAMES],
           w / 2, color=ORANGE, label="+ reputation layer")
a.bar_label(b1, fmt="%.0f", fontsize=7, padding=1)
a.bar_label(b2, fmt="%.0f", fontsize=7, padding=1)
a.set_ylim(0, 118)
a.set_title("Hard legitimate cases\ncalled phishing, %", fontsize=9.5, color=NAVY, pad=8)
a.legend(fontsize=7.5, frameon=False, loc="upper right")

for a in axes:
    a.set_xticks(x)
    a.set_xticklabels(PRETTY, fontsize=7)
    a.grid(axis="y", alpha=0.25, linewidth=0.6)
    a.set_axisbelow(True)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)

fig.suptitle("Model variants measured on field data, not on the training set",
             fontsize=12, color=NAVY, y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(os.path.join(FIGS, "fig18_model_variants.png"), dpi=200,
            facecolor="white", bbox_inches="tight")
plt.close(fig)
print("fig18_model_variants.png")

# ---------------------------------------------------------------- fig 19
ranks = R["meta"]["nigerian_domain_ranks"]
order = sorted(ranks.items(), key=lambda kv: kv[1])
labels = [k for k, _ in order]
values = [val for _, val in order]
fig, ax = plt.subplots(figsize=(9.4, 4.3))
colors = [GREEN if val <= 10_000 else (ORANGE if val <= 100_000 else RED) for val in values]
ax.barh(range(len(labels)), values, color=colors, height=0.62)
for i, val in enumerate(values):
    ax.text(val * 1.05, i, f"{val:,}", va="center", fontsize=8, color=NAVY)
ax.axvline(10_000, color=GREEN, linestyle="--", linewidth=1.2)
ax.axvline(100_000, color=ORANGE, linestyle="--", linewidth=1.2)
ax.text(10_000, len(labels) - 0.4, " top 10,000", fontsize=8, color=GREEN, rotation=90,
        va="top")
ax.text(100_000, len(labels) - 0.4, " top 100,000", fontsize=8, color=ORANGE, rotation=90,
        va="top")
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=9)
ax.set_xscale("log")
ax.set_xlabel("rank in the merged global popularity list, log scale (lower is more popular)",
              fontsize=9)
ax.set_title("Every locally relevant domain falls outside both global allow-list tiers",
             fontsize=10.5, color=NAVY, pad=8)
ax.grid(axis="x", alpha=0.25, linewidth=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig19_nigerian_ranks.png"), dpi=200,
            facecolor="white", bbox_inches="tight")
plt.close(fig)
print("fig19_nigerian_ranks.png")