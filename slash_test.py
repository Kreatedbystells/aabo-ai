"""Quantify the surviving shortcut: does a bare trailing slash still read as "attack"?

Takes popular legit domains, asks the deployed model about each as
  https://<domain>        (no path)
  https://<domain>/       (empty path, one slash)
  https://<domain>/about  (a real path)
and reports the false-positive rate per form, plus the FP rate of the held-out
legitimate corpus bucketed by path length.
"""
import json
import os
import random
import warnings

warnings.filterwarnings("ignore")
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
import sys
sys.path.insert(0, HERE)
from domain_utils import PLATFORM_HOSTS, host_of, on_platform_host, registrable   # noqa: E402
from train import FEATURES, extract_features                                       # noqa: E402

N = 300
rng = random.Random(7)


def score(model, url):
    f = extract_features(url)
    if f is None:
        return None
    v = [f[k] for k in FEATURES][:model.n_features_in_]
    return float(model.predict_proba([v])[0][list(model.classes_).index(1)])


doms = [l.strip() for l in open(os.path.join(ART, "allowlist_top10k.txt")) if l.strip()]
doms = [d for d in doms if not on_platform_host(d) and d not in PLATFORM_HOSTS]
sample = rng.sample(doms, N)

forms = {
    "https://{d}": "bare host, no path",
    "https://{d}/": "bare host, one trailing slash",
    "https://{d}/about": "host with a one-segment path",
    "https://{d}/account/login": "host with a two-segment path",
    "https://www.{d}/help/faq.html": "www host, deep path",
}

out = {}
for label in ("model_rf.joblib", "model_selected.joblib"):
    model = joblib.load(os.path.join(ART, label))
    res = {}
    for form, desc in forms.items():
        ps = [score(model, form.format(d=d)) for d in sample]
        ps = [p for p in ps if p is not None]
        res[desc] = {"n": len(ps),
                     "false_positive_rate": round(100 * sum(p >= 0.5 for p in ps) / len(ps), 2),
                     "median_probability_phishing": round(100 * float(np.median(ps)), 2)}
    out[label] = res
    print(label)
    for desc, v in res.items():
        print(f"   {desc:36s} FP {v['false_positive_rate']:6.2f}%  median p {v['median_probability_phishing']:6.2f}%")

# held-out legitimate corpus bucketed by path length
corp = json.load(open(os.path.join(HERE, "data", "legit_collected.json")))
urls = corp["urls"] if isinstance(corp, dict) and "urls" in corp else corp
urls = [u if isinstance(u, str) else u.get("url", "") for u in urls]
model = joblib.load(os.path.join(ART, "model_selected.joblib"))
buckets = {}
for u in urls:
    f = extract_features(u)
    if f is None:
        continue
    p = score(model, u)
    key = "0 (no path)" if f["path_length"] == 0 else \
          "1 (single slash)" if f["path_length"] == 1 else "2 or more"
    buckets.setdefault(key, []).append(p)
print("\nheld-out legitimate corpus by path length (deployed model)")
for k in ("0 (no path)", "1 (single slash)", "2 or more"):
    if k in buckets:
        ps = buckets[k]
        print(f"   path_length {k:18s} n {len(ps):5d}  FP {100 * sum(p >= 0.5 for p in ps) / len(ps):6.2f}%")
out["legit_corpus_by_path_length"] = {k: {"n": len(v),
                                          "false_positive_rate": round(100 * sum(p >= 0.5 for p in v) / len(v), 2)}
                                      for k, v in buckets.items()}
json.dump(out, open(os.path.join(ART, "slash_test.json"), "w"), indent=2)
print("\nwrote artifacts/slash_test.json")