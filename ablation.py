"""Ablation: how much of the in-dataset accuracy is carried by trivial signals?

Trains the same Random Forest with the same split twice:
  A. all sixteen features (the deployed model)
  B. fifteen features, path_length removed

and evaluates both on (i) the PhiUSIIL held-out test set and (ii) 1,000 URLs from
sources the models never saw. Writes artifacts/ablation.json
"""
import json, os, random, re
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from train import FEATURES, extract_features

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
SEED = 42


def build_frame():
    df = pd.read_csv(os.path.join(HERE, "data", "PhiUSIIL_Phishing_URL_Dataset.csv"),
                     usecols=["URL", "label"], low_memory=False)
    df = df.drop_duplicates(subset=["URL"])
    rows, ys = [], []
    for url, lab in zip(df["URL"].values, df["label"].values):
        f = extract_features(url)
        if f is None:
            continue
        rows.append([f[k] for k in FEATURES])
        ys.append(1 - int(lab))          # 1 = phishing
    return pd.DataFrame(rows, columns=FEATURES), np.array(ys)


def unseen_urls():
    """Same recipe as generalise.py / generalise_fullurl.py."""
    rng = random.Random(SEED)

    pdb = [l.strip() for l in open(os.path.join(HERE, "data", "pdb_active.txt"),
                                   errors="ignore")]
    pdb = [u for u in pdb if u.lower().startswith("http")]
    phish_full = rng.sample(pdb, 500)

    pa = [l.strip() for l in open(os.path.join(HERE, "data", "pa.txt"), errors="ignore")]
    pa = [u for u in pa if u and not u.lower().startswith("http")]
    phish_dom = ["https://" + d for d in rng.sample(pa, 500)]   # same scheme as the legit set

    top = pd.read_csv(os.path.join(HERE, "data", "top-1m.csv"), header=None,
                      names=["rank", "domain"])
    top = top[(top["rank"] >= 1000) & (top["rank"] <= 200000)]
    legit = ["https://" + d for d in rng.sample(list(top["domain"]), 500)]
    return phish_full, phish_dom, legit


def vec(urls):
    X, keep = [], []
    for u in urls:
        f = extract_features(u)
        if f is None:
            continue
        X.append([f[k] for k in FEATURES])
        keep.append(u)
    return X, keep


def evaluate(model, cols, urls):
    X, _ = vec(urls)
    X = pd.DataFrame(X, columns=FEATURES)[cols].values
    classes = list(model.classes_)
    p = model.predict_proba(X)[:, classes.index(1)]
    return p


def main():
    X, y = build_frame()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    phish_full, phish_dom, legit = unseen_urls()
    out = {"n_train": len(Xtr), "n_test": len(Xte)}

    for name, cols in [("all_16", list(FEATURES)),
                       ("without_path_length", [f for f in FEATURES if f != "path_length"])]:
        m = RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1)
        m.fit(Xtr[cols], ytr)
        p_te = m.predict_proba(Xte[cols])[:, 1]
        pred = (p_te >= 0.5).astype(int)
        acc = float((pred == yte).mean())
        rec = float(pred[yte == 1].mean())
        fp = int(((pred == 1) & (yte == 0)).sum())

        p_full = evaluate(m, cols, phish_full)
        p_dom = evaluate(m, cols, phish_dom)
        p_leg = evaluate(m, cols, legit)

        out[name] = {
            "test_accuracy": round(acc * 100, 2),
            "test_recall_phishing": round(rec * 100, 2),
            "test_false_positives": fp,
            "unseen_full_urls_detected": round(float((p_full >= 0.5).mean()) * 100, 1),
            "unseen_bare_domains_detected": round(float((p_dom >= 0.5).mean()) * 100, 1),
            "unseen_legit_cleared": round(float((p_leg < 0.5).mean()) * 100, 1),
            "hard_cases": {u: round(float(pp) * 100, 2) for u, pp in zip(
                ["paypal.com/signin", "github.com/login", "autozone.com", "google.com"],
                evaluate(m, cols, ["https://www.paypal.com/signin", "https://github.com/login",
                                   "https://autozone.com", "https://www.google.com"]))},
        }
        joblib.dump(m, os.path.join(ART, f"ablation_{name}.joblib"))
        print(name, json.dumps(out[name], indent=1))

    # class medians, to state the artefact precisely
    med = pd.DataFrame(X.assign(y=y)).groupby("y")[FEATURES].median().T
    out["class_medians"] = {k: {"legitimate": round(float(med.loc[k, 0]), 4),
                                "phishing": round(float(med.loc[k, 1]), 4)} for k in FEATURES}
    out["path_length_zero_share"] = {
        "legitimate": round(float((X.loc[y == 0, "path_length"] == 0).mean()) * 100, 1),
        "phishing": round(float((X.loc[y == 1, "path_length"] == 0).mean()) * 100, 1)}

    json.dump(out, open(os.path.join(ART, "ablation.json"), "w"), indent=2)
    print("\npath_length == 0 share:", out["path_length_zero_share"])
    print("wrote", os.path.join(ART, "ablation.json"))


if __name__ == "__main__":
    main()