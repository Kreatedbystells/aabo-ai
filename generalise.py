"""Out-of-dataset generalisation test.

PhiUSIIL accuracy is measured on a held-out slice of the same dataset. This
script tests the same two trained models on URLs from two independent sources
the models never saw:
  * Phishing Army community blocklist  -> labelled phishing
  * Cisco Umbrella top-1M popular list -> labelled legitimate
Writes artifacts/generalisation.json
"""
import json, os, random, re
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
import sys
sys.path.insert(0, HERE)
from train import extract_features, FEATURES

random.seed(42)
N = 500

# ---- phishing samples (independent of PhiUSIIL)
pa = []
with open(os.path.join(HERE, "data", "pa.txt"), encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        dom = line.split()[0].lower()
        if re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}", dom):
            pa.append(dom)
pa = sorted(set(pa))
phish_domains = random.sample(pa, N)

# ---- legitimate samples (Cisco Umbrella popularity list, mid ranks to avoid huge brands only)
legit = []
with open(os.path.join(HERE, "data", "top-1m.csv"), encoding="utf-8", errors="ignore") as f:
    for line in f:
        rank, _, dom = line.strip().partition(",")
        if not rank.isdigit():
            continue
        if 1000 <= int(rank) <= 200000:
            legit.append(dom)
legit_domains = random.sample(legit, N)

urls = [f"https://{d}" for d in phish_domains] + [f"https://{d}" for d in legit_domains]
y_true = np.array([1] * N + [0] * N)

X = pd.DataFrame([extract_features(u) for u in urls], columns=FEATURES)
keep = X.notna().all(axis=1).values
X, y_true = X[keep].values, y_true[keep]

rf = joblib.load(os.path.join(ART, "model_rf.joblib"))
lr = joblib.load(os.path.join(ART, "model_lr.joblib"))
scaler = joblib.load(os.path.join(ART, "scaler_lr.joblib"))

out = {"sources": {"phishing": f"Phishing Army blocklist ({len(pa):,} domains, {N} sampled)",
                   "legitimate": f"Cisco Umbrella top-1M ranks 1,000-200,000 ({N} sampled)"},
       "n_tested": int(len(X)), "models": {}, "sample_urls": {"phishing": urls[:5], "legitimate": urls[N:N+5]}}

for name, model, Xu in (("random_forest", rf, X), ("logistic_regression", lr, scaler.transform(X))):
    yp = model.predict(Xu)
    cm = confusion_matrix(y_true, yp)
    tn, fp, fn, tp = cm.ravel()
    out["models"][name] = {
        "accuracy": round(float(accuracy_score(y_true, yp)), 4),
        "precision": round(float(precision_score(y_true, yp)), 4),
        "recall": round(float(recall_score(y_true, yp)), 4),
        "f1": round(float(f1_score(y_true, yp)), 4),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "phishing_detected_pct": round(100 * tp / N, 2),
        "legitimate_cleared_pct": round(100 * tn / N, 2),
    }

json.dump(out, open(os.path.join(ART, "generalisation.json"), "w"), indent=2)
print(json.dumps(out, indent=2)[:2200])