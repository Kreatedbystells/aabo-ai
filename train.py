"""Model training pipeline for the phishing URL classifier.

Reads the PhiUSIIL dataset, extracts the sixteen lexical/structural features
defined in Chapter Three of the project, trains a Random Forest and a Logistic
Regression classifier on an identical split, evaluates both, and writes:
  artifacts/metrics.json          measured results used in Chapter Four
  artifacts/cm_rf.png             Random Forest confusion matrix
  artifacts/cm_lr.png             Logistic Regression confusion matrix
  artifacts/feature_importance.csv
  artifacts/model_rf.joblib / model_lr.joblib / scaler_lr.joblib
  artifacts/features.json         feature order + metadata for the API
"""
import json, os, re, time
import numpy as np
import joblib
from urllib.parse import urlparse

# pandas and matplotlib are imported inside main(), not here: app.py imports this
# module for FEATURES and extract_features only, and a web service has no business
# pulling a plotting library into its runtime (it also keeps the deployed function
# bundle inside Vercel's size limit).
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
os.makedirs(ART, exist_ok=True)

SUSPICIOUS_TOKENS = ["login", "signin", "sign-in", "verify", "secure", "account",
                     "update", "confirm", "auth", "password", "billing", "wallet",
                     "support", "alert"]

BRANDS = ["gtbank", "guarantytrust", "zenith", "accessbank", "firstbank", "ubagroup",
          "unionbank", "sterling", "wema", "fidelity", "polaris", "stanbic", "ecobank",
          "kuda", "opay", "palmpay", "moniepoint", "paystack", "flutterwave",
          "interswitch", "jamb", "nysc", "waec", "cbn", "binance", "paypal",
          "facebook", "instagram", "whatsapp", "microsoft", "apple", "amazon",
          "netflix", "google", "dhl", "fedex"]

SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "cc", "tk", "ml", "ga", "cf", "gq",
                   "work", "click", "link", "live", "site", "online", "shop", "icu",
                   "cyou", "rest", "monster", "buzz", "loan", "cn", "ru", "su"}

IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
FEATURES = ["url_length", "hostname_length", "path_length", "query_length",
            "hostname_depth", "subdomain_count", "has_ip_address", "has_at_symbol",
            "has_double_slash", "is_https", "hyphen_count", "digit_ratio",
            "suspicious_token_count", "suspicious_tld", "encoded_char_count",
            "brand_in_subdomain"]


def extract_features(url: str):
    """Compute the sixteen features for one URL. Returns None if unparseable."""
    if not isinstance(url, str) or not url.strip():
        return None
    u = url.strip()
    try:
        p = urlparse(u)
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    if not host:
        return None
    path = p.path or ""
    if path == "/":
        # RFC 3986 section 6.2.2.3: for an HTTP origin an empty path is equivalent to "/",
        # so a bare trailing slash carries no information about the resource. Leaving it in
        # taught the first model that "a path means an attack"; normalising it here keeps the
        # innocuous form https://example.com/ identical to https://example.com.
        path = ""
        u = u.rstrip("/")
    query = p.query or ""
    labels = [l for l in host.split(".") if l]
    tld = labels[-1] if labels else ""
    registrable_span = labels[-2:] if len(labels) >= 2 else labels
    host_without_registrable = labels[:-2] if len(labels) > 2 else []
    low_all = (host + path).lower()
    return {
        "url_length": len(u),
        "hostname_length": len(host),
        "path_length": len(path),
        "query_length": len(query),
        "hostname_depth": host.count("."),
        "subdomain_count": max(0, len(labels) - 2),
        "has_ip_address": int(bool(IP_RE.match(host))),
        "has_at_symbol": int("@" in (p.netloc or "")),
        "has_double_slash": int("//" in path),
        "is_https": int(p.scheme == "https"),
        "hyphen_count": host.count("-"),
        "digit_ratio": round(sum(c.isdigit() for c in host) / len(host), 4) if host else 0.0,
        "suspicious_token_count": sum(1 for t in SUSPICIOUS_TOKENS if t in low_all),
        "suspicious_tld": int(tld in SUSPICIOUS_TLDS),
        "encoded_char_count": u.count("%"),
        "brand_in_subdomain": int(any(b in lab for lab in host_without_registrable for b in BRANDS)),
    }


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    t0 = time.time()
    df = pd.read_csv(os.path.join(HERE, "data", "PhiUSIIL_Phishing_URL_Dataset.csv"),
                     usecols=["URL", "label"], low_memory=False)
    raw_n = len(df)
    df = df.drop_duplicates(subset="URL")
    dup_n = raw_n - len(df)

    rows, labels, dropped = [], [], 0
    for url, lab in zip(df["URL"].values, df["label"].values):
        f = extract_features(url)
        if f is None:
            dropped += 1
            continue
        rows.append(f)
        labels.append(1 - int(lab))          # recode: 1 = phishing, 0 = legitimate
    X = pd.DataFrame(rows, columns=FEATURES)
    y = np.array(labels)
    X = X.replace([np.inf, -np.inf], np.nan).dropna()
    y = y[X.index.values]
    print(f"kept {len(X)} of {raw_n} (duplicates removed {dup_n}, unparseable {dropped})")
    print("class balance:", dict(zip(*np.unique(y, return_counts=True))))

    X_tr, X_te, y_tr, y_te = train_test_split(
        X.values, y, test_size=0.20, random_state=42, stratify=y)
    print(f"train {len(X_tr)} / test {len(X_te)}  (features: {len(FEATURES)})")

    scaler = StandardScaler().fit(X_tr)

    rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=1,
                                max_features="sqrt", n_jobs=-1, random_state=42)
    t = time.time(); rf.fit(X_tr, y_tr); rf_train_s = time.time() - t

    lr = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs", random_state=42)
    t = time.time(); lr.fit(scaler.transform(X_tr), y_tr); lr_train_s = time.time() - t

    res = {}
    for name, model, Xu in (("random_forest", rf, X_te),
                            ("logistic_regression", lr, scaler.transform(X_te))):
        yp = model.predict(Xu)
        cm = confusion_matrix(y_te, yp)
        tn, fp, fn, tp = cm.ravel()
        res[name] = {
            "accuracy": round(float(accuracy_score(y_te, yp)), 4),
            "precision": round(float(precision_score(y_te, yp)), 4),
            "recall": round(float(recall_score(y_te, yp)), 4),
            "f1": round(float(f1_score(y_te, yp)), 4),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        }
        # confusion matrix figure
        fig, ax = plt.subplots(figsize=(4.6, 4.0), dpi=200)
        im = ax.imshow(cm, cmap="Blues")
        labels_ = ["Legitimate", "Phishing"]
        ax.set_xticks([0, 1], labels_); ax.set_yticks([0, 1], labels_)
        ax.set_xlabel("Predicted class"); ax.set_ylabel("Actual class")
        title = "Random Forest" if name == "random_forest" else "Logistic Regression"
        ax.set_title(f"{title} confusion matrix")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "#122a4d",
                        fontsize=11, fontweight="bold")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        out = os.path.join(ART, "cm_rf.png" if name == "random_forest" else "cm_lr.png")
        fig.savefig(out); plt.close(fig)
        res[name]["confusion_matrix_png"] = out
        res[name]["classification_report"] = classification_report(
            y_te, yp, target_names=["Legitimate", "Phishing"], digits=4)

    # per-prediction latency
    sample = X_te[:1000]
    t = time.time(); [rf.predict(sample[i:i + 1]) for i in range(200)]; rf_ms = (time.time() - t) / 200 * 1000
    s_sample = scaler.transform(sample)
    t = time.time(); [lr.predict(s_sample[i:i + 1]) for i in range(200)]; lr_ms = (time.time() - t) / 200 * 1000

    # feature importance (RF impurity) and coefficients (LR)
    imp = pd.DataFrame({"feature": FEATURES,
                        "rf_importance": rf.feature_importances_,
                        "lr_coefficient": lr.coef_[0]}).sort_values(
                            "rf_importance", ascending=False)
    imp.to_csv(os.path.join(ART, "feature_importance.csv"), index=False)

    joblib.dump(rf, os.path.join(ART, "model_rf.joblib"))
    joblib.dump(lr, os.path.join(ART, "model_lr.joblib"))
    joblib.dump(scaler, os.path.join(ART, "scaler_lr.joblib"))
    json.dump({"features": FEATURES, "positive_class": "phishing",
               "label_map": {"0": "legitimate", "1": "phishing"},
               "suspicious_tokens": SUSPICIOUS_TOKENS, "brands": BRANDS,
               "suspicious_tlds": sorted(SUSPICIOUS_TLDS)},
              open(os.path.join(ART, "features.json"), "w"), indent=2)

    summary = {"dataset": {"raw_rows": raw_n, "duplicate_urls_removed": dup_n,
                           "unparseable_dropped": dropped, "usable_rows": int(len(X)),
                           "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
                           "test_size": 0.20, "random_state": 42,
                           "phishing": int((y == 1).sum()), "legitimate": int((y == 0).sum())},
               "training_seconds": {"random_forest": round(rf_train_s, 1),
                                    "logistic_regression": round(lr_train_s, 1)},
               "latency_ms_per_prediction": {"random_forest": round(rf_ms, 3),
                                             "logistic_regression": round(lr_ms, 3)},
               "results": res,
               "feature_importance": imp.to_dict(orient="records"),
               "total_seconds": round(time.time() - t0, 1)}
    json.dump(summary, open(os.path.join(ART, "metrics.json"), "w"), indent=2)
    print(json.dumps({k: summary[k] for k in
                      ("dataset", "training_seconds", "latency_ms_per_prediction", "results")}, indent=2)[:2600])
    print("done in", summary["total_seconds"], "s")


if __name__ == "__main__":
    main()