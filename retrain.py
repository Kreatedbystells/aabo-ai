"""Rebalanced model: train on a legitimate class that contains paths.

Section 4.5.3 established the defect: every legitimate URL in PhiUSIIL is a bare
domain, so the baseline model treats the presence of a path as evidence of attack.
This script fixes the input data and measures the effect, keeping the baseline as
the comparison point.

Models
  baseline    Random Forest on PhiUSIIL only (the model already reported)
  rebalanced  baseline plus legitimate URLs with paths collected from popular
              domains, with class_weight="balanced_subsample"

The reputation layer (verdict overridden to "known domain" when the registrable
domain is in the Umbrella top-10,000) is applied on top of each model's own
probabilities, so its effect is reported separately for both.

Writes artifacts/retrain.json, artifacts/model_rf_v2.joblib, artifacts/feature_importance_v2.csv
"""
import json
import os
from datetime import datetime
import random
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

from domain_utils import (PLATFORM_HOSTS, host_of, is_allowlisted, on_platform_host,
                          registrable, load_allowlist as _load_al)
from train import FEATURES, extract_features

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
SEED = 42
TAU = 0.5

HARD_CASES = [
    "https://www.paypal.com/signin", "https://www.paypal.com/us/home",
    "https://github.com/login", "https://github.com/features/actions",
    "https://www.autozone.com/", "https://www.autozone.com/parts/brakes",
    "https://www.amazon.com/gp/cart/view.html", "https://www.amazon.com/dp/B08N5WRWNW",
    "https://www.facebook.com/login/", "https://www.instagram.com/accounts/login/",
    "https://www.linkedin.com/feed/", "https://www.netflix.com/browse",
    "https://www.apple.com/shop/buy-iphone", "https://www.microsoft.com/en-us/windows/",
    "https://www.nytimes.com/section/technology", "https://www.booking.com/hotel/ng/lagos.html",
    "https://stackoverflow.com/questions/tagged/python", "https://en.wikipedia.org/wiki/Phishing",
    "https://www.jumia.com.ng/phones-tablets/", "https://www.gtbank.com/personal-banking",
    "https://paystack.com/docs/payments/accept-payments/", "https://flutterwave.com/gb/pricing",
    "https://www.coursera.org/learn/machine-learning", "https://medium.com/tag/cybersecurity",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://play.google.com/store/apps",
    "https://www.shopify.com/pricing", "https://www.canva.com/templates/",
    "https://www.accessbankplc.com/pages/Personal/Banking", "https://x.com/home",
]


def ok_url(url):
    return isinstance(url, str) and url.lower().startswith(("http://", "https://"))


def featurise(urls):
    """Return (matrix, kept_urls); anything unparseable is dropped, labels aligned by caller."""
    X, keep = [], []
    for u in urls:
        f = extract_features(u)
        if f is None:
            continue
        X.append([f[k] for k in FEATURES])
        keep.append(u)
    return np.asarray(X, dtype=float), keep


def load_phiusiil():
    """Return feature matrix, labels and the URLs they correspond to."""
    df = pd.read_csv(os.path.join(HERE, "data", "PhiUSIIL_Phishing_URL_Dataset.csv"),
                     usecols=["URL", "label"], low_memory=False)
    df = df.drop_duplicates(subset=["URL"])
    X, y, urls = [], [], []
    for u, lab in zip(df["URL"].tolist(), df["label"].tolist()):
        f = extract_features(u)
        if f is None:
            continue
        X.append([f[k] for k in FEATURES])
        y.append(1 - int(lab))                       # 1 = phishing
        urls.append(u)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), urls


def load_legit():
    """Merge both collectors and split DOMAINS 80/20 so no domain appears in both."""
    domains = {}
    for fn in ("legit_collected.json", "legit_sitemap.json"):
        p = os.path.join(HERE, "data", fn)
        if not os.path.exists(p):
            continue
        for dom, urls in json.load(open(p))["domains"].items():
            domains.setdefault(dom, set()).update(u for u in urls if ok_url(u))
    doms = sorted(domains)
    rng = random.Random(SEED)
    rng.shuffle(doms)
    cut = int(len(doms) * 0.8)
    train_doms, test_doms = doms[:cut], doms[cut:]
    tr = sorted({u for d in train_doms for u in domains[d]})
    te = sorted({u for d in test_doms for u in domains[d]})
    return tr, te, train_doms, test_doms, len(domains)


def load_shape_variants():
    """The URL shapes users actually paste, over well-known legitimate domains.

    PhiUSIIL's legitimate class is a single template: every one of its 134,850 legitimate
    rows is https://www.<domain> with no path (measured). A model trained on that alone
    learns "www and no path means safe", which is why https://www.google.com is called
    legitimate 99.9% of the time while https://google.com is called phishing. These rows
    vary only the shape of the URL; no page is fetched and no domain identity is encoded
    in the features, so the classifier cannot memorise the list.
    """
    doms = [l.strip() for l in open(os.path.join(ART, "allowlist_top10k.txt")) if l.strip()]
    doms = [d for d in doms if not on_platform_host(d) and d not in PLATFORM_HOSTS]
    shapes = ["https://{d}", "https://www.{d}", "https://{d}/", "https://www.{d}/",
              "https://{d}/login", "https://{d}/about"]
    return [s.format(d=d) for d in doms for s in shapes]


def load_phishing_feeds():
    pdb = [l.strip() for l in open(os.path.join(HERE, "data", "pdb_active.txt"), errors="ignore")]
    pdb = [u for u in pdb if u.lower().startswith("http")]            # full hostile URLs
    pa = [l.strip() for l in open(os.path.join(HERE, "data", "pa.txt"), errors="ignore")]
    pa = ["https://" + d for d in pa if d and not d.lower().startswith("http")]  # bare, same scheme as legit
    rng = random.Random(SEED)
    return rng.sample(pdb, 500), rng.sample(pa, 500)


def load_allowlist():
    """Two tiers, written by the build step; see artifacts/allowlist_*.txt."""
    out = {}
    for tag, fn in (("top10k", "allowlist_top10k.txt"), ("top100k", "allowlist_top100k.txt"),
                    ("ng", "allowlist_ng.txt")):
        out[tag] = _load_al(os.path.join(ART, fn))
    # the deployment configuration: global popularity list plus the Nigerian list
    out["deployed"] = out["top100k"] | out["ng"]
    return out


# Ranks of the Nigerian domains checked by hand, for the coverage note in Chapter Four.
LOCAL_DOMAINS = {"gtbank.com": 365782, "paystack.com": 432967, "zenithbank.com": 527015,
                 "firstbanknigeria.com": 505608, "jumia.com.ng": 212517}


def phish_scores(model, X):
    return model.predict_proba(X)[:, list(model.classes_).index(1)]


def summarise(y_true, p, urls, allow, tau=TAU):
    """Metrics before and after the reputation layer, on the same rows."""
    base = (p >= tau).astype(int)
    after = base.copy()
    for i, u in enumerate(urls):
        if after[i] == 1 and is_allowlisted(u, allow):
            after[i] = 0

    def pack(pred):
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        return {"n": int(len(y_true)), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                "accuracy": round(float((pred == y_true).mean()) * 100, 2),
                "false_positive_rate": round(float(fp / max(1, fp + tn)) * 100, 2),
                "recall": round(rec * 100, 2), "precision": round(prec * 100, 2),
                "f1": round(2 * prec * rec / max(1e-9, prec + rec) * 100, 2)}

    return {"model_only": pack(base), "with_reputation_layer": pack(after),
            "verdicts_overridden": int((base - after).sum())}


def main():
    print("loading data ...")
    Xp, yp, up = load_phiusiil()
    legit_tr, legit_te, tr_doms, te_doms, n_doms = load_legit()
    phish_full, phish_bare = load_phishing_feeds()
    allow = load_allowlist()
    allow_wide = allow.get("top100k", set())
    print(f"PhiUSIIL {len(Xp):,} rows | legit corpus {len(legit_tr) + len(legit_te):,} URLs "
          f"over {n_doms:,} domains ({len(te_doms):,} held out)")

    Xp_tr, Xp_te, yp_tr, yp_te, up_tr, up_te = train_test_split(
        Xp, yp, up, test_size=0.2, stratify=yp, random_state=SEED)
    Xl_tr, kept_tr = featurise(legit_tr)
    Xl_te, kept_te = featurise(legit_te)
    shape_urls = load_shape_variants()
    Xs, kept_s = featurise(shape_urls)
    print(f"shape variants for well-known legitimate domains: {len(kept_s):,} rows")

    # field test: held-out legitimate URLs with paths + legitimate bare domains + hostile URLs
    rng = random.Random(SEED)
    bare_idx = [i for i in range(len(yp_te)) if yp_te[i] == 0]
    bare_idx = rng.sample(bare_idx, min(5_000, len(bare_idx)))
    Xf_full, kept_full = featurise(phish_full)
    Xf_bare, kept_bare = featurise(phish_bare)

    field_X = np.vstack([Xl_te, Xp_te[bare_idx], Xf_full, Xf_bare])
    field_y = np.r_[np.zeros(len(Xl_te)), np.zeros(len(bare_idx)),
                    np.ones(len(Xf_full)), np.ones(len(Xf_bare))]
    field_urls = kept_te + [up_te[i] for i in bare_idx] + kept_full + kept_bare
    n_path, n_bare = len(Xl_te), len(bare_idx)
    sl_path = slice(0, n_path)
    sl_bare = slice(n_path, n_path + n_bare)
    sl_phish = slice(n_path + n_bare, len(field_y))

    X_hard, hard_urls = featurise(HARD_CASES)

    keep_cols = [i for i, f in enumerate(FEATURES) if f != "path_length"]
    models = {
        "baseline": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1),
        "rebalanced": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1,
                                            class_weight="balanced_subsample"),
    }
    models["baseline"].fit(Xp_tr, yp_tr)
    legit_extra = np.vstack([Xl_tr, Xs])
    print(f"legitimate training rows beyond PhiUSIIL: {len(legit_extra):,}")
    models["rebalanced"].fit(np.vstack([Xp_tr, legit_extra]),
                             np.r_[yp_tr, np.zeros(len(legit_extra))])
    # third variant: corpus change alone, with the artefact feature removed entirely
    models["rebalanced_no_path"] = RandomForestClassifier(
        n_estimators=200, random_state=SEED, n_jobs=-1, class_weight="balanced_subsample")
    models["rebalanced_no_path"].fit(
        np.vstack([Xp_tr[:, keep_cols], legit_extra[:, keep_cols]]),
        np.r_[yp_tr, np.zeros(len(legit_extra))])

    # fourth variant: a legitimate class in which HALF the rows carry a path, so that
    # "has a path" can no longer be a sufficient condition for the phishing label
    rng_bal = random.Random(SEED)
    bare_pool = [i for i in range(len(yp_tr)) if yp_tr[i] == 0]
    bare_pick = rng_bal.sample(bare_pool, min(len(legit_extra), len(bare_pool)))
    X_bal = np.vstack([Xp_tr, legit_extra, Xp_tr[bare_pick]])
    y_bal = np.r_[yp_tr, np.zeros(len(legit_extra)), np.zeros(len(bare_pick))]
    models["rebalanced_balanced"] = RandomForestClassifier(
        n_estimators=200, random_state=SEED, n_jobs=-1, class_weight="balanced")
    models["rebalanced_balanced"].fit(X_bal, y_bal)
    print(f"balanced variant: {len(legit_extra):,} collected legitimate + "
          f"{len(bare_pick):,} bare legitimate + {len(yp_tr):,} hostile rows")
    joblib.dump(models["rebalanced"], os.path.join(ART, "model_rf_v2.joblib"))

    out = {"meta": {"seed": SEED, "threshold": TAU,
                    "phiusiil_rows": int(len(Xp)),
                    "legit_corpus_urls": int(len(legit_tr) + len(legit_te)),
                    "legit_train_urls": int(len(Xl_tr) + len(kept_s)),
                    "legit_collected_train_urls": int(len(Xl_tr)),
                    "legit_shape_variant_urls": int(len(kept_s)),
                    "legit_holdout_urls": int(len(Xl_te)),
                    "legit_domains_total": int(n_doms),
                    "legit_domains_held_out": len(te_doms),
                    "allowlist_domains": {k: len(v) for k, v in allow.items()},
                    "nigerian_domain_ranks": LOCAL_DOMAINS,
                    "nigerian_domains_in_top100k": sorted(
                        d for d in LOCAL_DOMAINS if registrable(d) in allow_wide),
                    "field_test_size": int(len(field_y))},
           "models": {}}

    for name, m in models.items():
        cols = keep_cols if name == "rebalanced_no_path" else list(range(len(FEATURES)))
        sel = lambda A: A[:, cols]
        none = set()
        res = {"phiusiil_test": summarise(yp_te, phish_scores(m, sel(Xp_te)), up_te, none),
               "field_all": summarise(field_y, phish_scores(m, sel(field_X)), field_urls,
                                      allow.get("top10k", none)),
               "field_all_top100k": summarise(field_y, phish_scores(m, sel(field_X)), field_urls,
                                              allow_wide),
               "field_legit_with_paths": summarise(np.zeros(n_path),
                                                   phish_scores(m, sel(field_X[sl_path])),
                                                   kept_te, allow_wide),
               "field_legit_bare": summarise(np.zeros(n_bare),
                                             phish_scores(m, sel(field_X[sl_bare])),
                                             field_urls[sl_bare], allow_wide),
               "field_phishing": summarise(np.ones(len(field_y[sl_phish])),
                                           phish_scores(m, sel(field_X[sl_phish])),
                                           field_urls[sl_phish], none),
               "field_phishing_top100k": summarise(np.ones(len(field_y[sl_phish])),
                                                   phish_scores(m, sel(field_X[sl_phish])),
                                                   field_urls[sl_phish], allow_wide),
               "hard_cases": summarise(np.zeros(len(X_hard)), phish_scores(m, sel(X_hard)),
                                       hard_urls, allow_wide),
               "field_all_deployed": summarise(field_y, phish_scores(m, sel(field_X)),
                                               field_urls, allow.get("deployed", none)),
               "hard_cases_deployed": summarise(np.zeros(len(X_hard)), phish_scores(m, sel(X_hard)),
                                                hard_urls, allow.get("deployed", none))}
        p_hard = phish_scores(m, sel(X_hard))
        res["hard_case_detail"] = {u: round(float(p) * 100, 1) for u, p in zip(hard_urls, p_hard)}
        out["models"][name] = res
        print(f"\n=== {name}")
        print(json.dumps({k: v for k, v in res.items() if k != "hard_case_detail"}, indent=1))

    # ---- pick the model on FIELD behaviour, not in-dataset accuracy ----
    def key(n):
        r = out["models"][n]
        return (-r["field_all"]["model_only"]["accuracy"],
                r["field_legit_with_paths"]["model_only"]["false_positive_rate"],
                -r["field_phishing"]["model_only"]["recall"])

    winner = min(models, key=key)
    out["selection"] = {
        "rule": ("highest accuracy on the field test (held-out legitimate URLs with paths, "
                 "held-out legitimate bare domains, 500 hostile full URLs, 500 hostile bare "
                 "domains); ties broken by the lower false-positive rate on legitimate URLs "
                 "that carry a path, then by higher recall on hostile URLs"),
        "winner": winner,
        "ranker": {n: {"field_accuracy": out["models"][n]["field_all"]["model_only"]["accuracy"],
                       "legit_with_paths_fp": out["models"][n]["field_legit_with_paths"
                                                              ]["model_only"]["false_positive_rate"]}
                   for n in models},
    }
    joblib.dump(models[winner], os.path.join(ART, "model_selected.joblib"))
    cols = keep_cols if winner == "rebalanced_no_path" else list(range(len(FEATURES)))
    json.dump({"variant": winner, "artifact": "model_selected.joblib",
               "algorithm": "Random Forest", "n_features": len(cols),
               "phiusiil_accuracy": out["models"][winner]["phiusiil_test"]["model_only"]["accuracy"],
               "field_accuracy": out["models"][winner]["field_all"]["model_only"]["accuracy"],
               "field_accuracy_with_reputation": out["models"][winner]["field_all_top100k"
                                                                    ]["with_reputation_layer"]["accuracy"],
               "trained_at": datetime.now().strftime("%Y-%m-%d")},
              open(os.path.join(ART, "selected.json"), "w"), indent=2)
    print(f"\nselected on field performance: {winner}")

    # decision threshold: the app uses 0.5; show what moving it costs on the field test
    wm = models[winner]
    wcols = keep_cols if winner == "rebalanced_no_path" else list(range(len(FEATURES)))
    sweep = {}
    fsc = phish_scores(wm, field_X[:, wcols])
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        s = summarise(field_y, fsc, field_urls, allow.get("deployed", set()), tau=t)
        sweep[f"{t:.1f}"] = {"accuracy": s["model_only"]["accuracy"],
                             "precision": s["model_only"]["precision"],
                             "recall": s["model_only"]["recall"],
                             "f1": s["model_only"]["f1"]}
        sweep[f"{t:.1f}"]["accuracy_with_reputation"] = s["with_reputation_layer"]["accuracy"]
    out["threshold_sweep"] = sweep
    print("threshold sweep:", json.dumps(sweep, indent=1))

    imp = pd.DataFrame({"feature": FEATURES,
                        "baseline_importance": models["baseline"].feature_importances_,
                        "rebalanced_importance": models["rebalanced"].feature_importances_})
    imp["no_path_importance"] = [                     # NaN for the feature that was removed
        models["rebalanced_no_path"].feature_importances_[keep_cols.index(i)]
        if i in keep_cols else float("nan")
        for i in range(len(FEATURES))]
    imp["balanced_importance"] = models["rebalanced_balanced"].feature_importances_
    imp.sort_values("rebalanced_importance", ascending=False).to_csv(
        os.path.join(ART, "feature_importance_v2.csv"), index=False)
    json.dump(out, open(os.path.join(ART, "retrain.json"), "w"), indent=2)
    print("\nwrote", os.path.join(ART, "retrain.json"))


if __name__ == "__main__":
    main()