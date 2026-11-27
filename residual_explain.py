"""What separates the held-out legitimate URLs the model still flags from those it clears?

Compares feature medians for false positives against true negatives on the held-out corpus,
so the residual can be described rather than just reported.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from retrain import load_legit                                   # noqa: E402
from train import FEATURES, extract_features                     # noqa: E402

ART = os.path.join(HERE, "artifacts")
model = joblib.load(os.path.join(ART, "model_selected.joblib"))
_, held_te, _, te_doms, _ = load_legit()

fp_vecs, tn_vecs = [], []
for u in held_te:
    f = extract_features(u)
    if f is None:
        continue
    v = [f[k] for k in FEATURES][:model.n_features_in_]
    p = float(model.predict_proba([v])[0][list(model.classes_).index(1)])
    (fp_vecs if p >= 0.5 else tn_vecs).append((u, f, p))

names = list(FEATURES)
print(f"false positives {len(fp_vecs):,} | cleared {len(tn_vecs):,}\n")
print(f"{'feature':24s} {'FP median':>11s} {'cleared median':>15s}")
interesting = []
for k in names:
    a = np.median([f[k] for _, f, _ in fp_vecs]) if fp_vecs else float("nan")
    b = np.median([f[k] for _, f, _ in tn_vecs]) if tn_vecs else float("nan")
    if abs(a - b) > 1e-9:
        interesting.append((k, a, b))
for k, a, b in sorted(interesting, key=lambda t: -abs(t[1] - t[2])):
    print(f"{k:24s} {a:11.2f} {b:15.2f}")

print("\nlongest URLs among false positives:")
for u, f, p in sorted(fp_vecs, key=lambda t: -t[1]["url_length"])[:5]:
    print(f"   p={p:.2f} len={f['url_length']:4d} hyphens={f['hyphen_count']} "
          f"digits={f['digit_ratio']:.2f}  {u[:80]}")
print("\nshortest URLs the model cleared:")
for u, f, p in sorted(tn_vecs, key=lambda t: t[1]["url_length"])[:3]:
    print(f"   p={p:.2f} len={f['url_length']:4d}  {u[:80]}")