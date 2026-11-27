"""Second generalisation test: full phishing URLs (with paths) from an
independent active feed, measured for detection rate only (one-sided, so no
legitimate counterpart is needed).
Writes artifacts/generalisation_fullurl.json
"""
import json, os, random, sys
import joblib
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
sys.path.insert(0, HERE)
from train import extract_features, FEATURES

random.seed(7)
N = 500

urls = []
with open(os.path.join(HERE, "data", "pdb_active.txt"), encoding="utf-8", errors="ignore") as f:
    for line in f:
        u = line.strip()
        if u.startswith(("http://", "https://")) and len(u) < 400:
            urls.append(u)
urls = sorted(set(urls))
sample = random.sample(urls, min(N, len(urls)))

X = pd.DataFrame([extract_features(u) for u in sample], columns=FEATURES)
keep = X.notna().all(axis=1).values
X = X[keep].values
n = len(X)

rf = joblib.load(os.path.join(ART, "model_rf.joblib"))
lr = joblib.load(os.path.join(ART, "model_lr.joblib"))
scaler = joblib.load(os.path.join(ART, "scaler_lr.joblib"))

out = {"source": "Phishing.Database active phishing links (community-maintained)",
       "available_urls": len(urls), "sampled": n, "models": {}}
for name, model, Xu in (("random_forest", rf, X), ("logistic_regression", lr, scaler.transform(X))):
    yp = model.predict(Xu)
    tp = int((yp == 1).sum())
    out["models"][name] = {"detected_phishing": tp, "tested": n,
                           "detection_rate_pct": round(100 * tp / n, 2)}
json.dump(out, open(os.path.join(ART, "generalisation_fullurl.json"), "w"), indent=2)
print(json.dumps(out, indent=2))