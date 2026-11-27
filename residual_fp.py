"""Where do the deployed model's remaining false positives come from?

Scores the held-out legitimate corpus (domains the model never trained on) and splits the
false positives by path depth, then reports how many of them carry a security-sounding
path token such as /login or /account — the words phishing pages also use.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from retrain import load_legit                                    # noqa: E402
from train import FEATURES, SUSPICIOUS_TOKENS, extract_features    # noqa: E402

ART = os.path.join(HERE, "artifacts")
model = joblib.load(os.path.join(ART, "model_selected.joblib"))
_, held_te, _, te_doms, _ = load_legit()
print(f"held-out legitimate URLs: {len(held_te):,} over {len(te_doms)} unseen domains")

rows = []
for u in held_te:
    f = extract_features(u)
    if f is None:
        continue
    v = [f[k] for k in FEATURES][:model.n_features_in_]
    p = float(model.predict_proba([v])[0][list(model.classes_).index(1)])
    rows.append((u, f["path_length"], p))

fp = [r for r in rows if r[2] >= 0.5]
print(f"false positives: {len(fp):,} of {len(rows):,} = {100 * len(fp) / len(rows):.2f}%")

buckets = {}
for u, pl, p in rows:
    key = "0 (no path)" if pl == 0 else "1 (bare slash)" if pl == 1 \
        else "2 (one segment)" if pl <= 6 else "3+ (deeper path)"
    buckets.setdefault(key, []).append(p)
print("\nby path depth:")
out = {}
for k in sorted(buckets):
    ps = buckets[k]
    rate = round(100 * sum(x >= 0.5 for x in ps) / len(ps), 2)
    out[k] = {"n": len(ps), "false_positive_rate": rate}
    print(f"   {k:20s} n {len(ps):5d}   FP {rate:6.2f}%")

tok = [u for u, _, p in fp
       if any(t in u.lower() for t in SUSPICIOUS_TOKENS)]
print(f"\nfalse positives whose URL contains a security-sounding token "
      f"({', '.join(sorted(SUSPICIOUS_TOKENS))}): {len(tok):,} of {len(fp):,} "
      f"= {100 * len(tok) / max(1, len(fp)):.1f}%")
print("examples:", *[u[:72] for u in tok[:6]], sep="\n   ")
out["fp_with_suspicious_token"] = {"n": len(tok), "of_false_positives": len(fp),
                                   "percent": round(100 * len(tok) / max(1, len(fp)), 1)}
out["examples_with_token"] = tok[:12]

import json
json.dump(out, open(os.path.join(ART, "residual_fp.json"), "w"), indent=2)
print("\nwrote artifacts/residual_fp.json")