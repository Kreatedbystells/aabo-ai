"""Aabo AI — reads the structure of a URL and classifies it before the page is opened.

FastAPI application that serves the single-page interface and exposes the
classification API described in Chapter Three of the project document.

Run:  ml/bin/python -m uvicorn app:app --port 8077
"""
import json
import os
import re
import sqlite3
import time
import urllib.parse
from datetime import datetime
from domain_utils import (host_of, is_allowlisted, load_allowlist, on_restricted_registry,
                          registrable)

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from train import FEATURES, extract_features

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
# The scan log is a local SQLite file. A serverless filesystem is read-only apart
# from /tmp, so AABO_DB points the log there when the app is deployed; the bundled
# database is copied across once per instance so the demo starts with sample rows.
DB = os.environ.get("AABO_DB") or os.path.join(ART, "scans.db")
if os.environ.get("AABO_DB") and not os.path.exists(DB):
    import shutil
    shutil.copyfile(os.path.join(ART, "scans.db"), DB)
STATIC = os.path.join(HERE, "app")

app = FastAPI(title="Aabo AI", version="1.0")

def load_model():
    """Prefer the selected model, then the rebalanced one, then the original baseline."""
    for fn in ("model_selected.joblib", "model_rf_v2.joblib", "model_rf.joblib"):
        p = os.path.join(ART, fn)
        if os.path.exists(p):
            return joblib.load(p), fn
    raise SystemExit("no model artefact found in artifacts/")


MODEL, MODEL_FILE = load_model()


# Deployment configuration: the global popularity list plus the curated Nigerian list.
# The global list alone covers no Nigerian domain, so a Nigerian user gets no protection
# on the sites they use most; the second list closes that gap.
ALLOW_GLOBAL = load_allowlist(os.path.join(ART, "allowlist_top100k.txt"))
ALLOW_NG = load_allowlist(os.path.join(ART, "allowlist_ng.txt"))
ALLOW = ALLOW_GLOBAL | ALLOW_NG
# A deployment may also be configured with domains its operator knows first-hand to be
# legitimate (its own site, a client's site). That list is configuration rather than
# evidence, and it is reported separately so it never contaminates the measured tiers of
# Section 4.6.5.
ALLOW_OPERATOR = load_allowlist(os.path.join(ART, "allowlist_operator.txt"))
ALLOW_LOOKUP = ALLOW | ALLOW_OPERATOR
META = json.load(open(os.path.join(ART, "metrics.json")))
MODEL_ID = 1
MODEL_NAME = MODEL_FILE.replace(".joblib", "")
try:
    SELECTED = json.load(open(os.path.join(ART, "selected.json")))
except FileNotFoundError:
    SELECTED = {}
LABEL = {"baseline": "rf-v1", "rebalanced": "rf-v2",
         "rebalanced_no_path": "rf-v2-nopath", "rebalanced_balanced": "rf-v2-balanced"}
MODEL_VERSION = LABEL.get(SELECTED.get("variant", "baseline"), "rf-v1")
MODEL_ACCURACY = SELECTED.get("phiusiil_accuracy",
                              META["results"]["random_forest"]["accuracy"])


def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS model_version (
        model_id      INTEGER PRIMARY KEY,
        version       VARCHAR(32),
        algorithm     VARCHAR(32),
        trained_on    DATE,
        accuracy      REAL,
        artefact_path VARCHAR(255),
        n_features    INTEGER
    );
    CREATE TABLE IF NOT EXISTS scan_record (
        scan_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        url        TEXT,
        verdict    VARCHAR(16),
        confidence REAL,
        model_id   INTEGER REFERENCES model_version(model_id),
        created_at TIMESTAMP
    );
    """)
    version = MODEL_VERSION
    con.execute("DELETE FROM model_version WHERE model_id = ?", (MODEL_ID,))
    con.execute("INSERT INTO model_version VALUES (?,?,?,?,?,?,?)",
                (MODEL_ID, version, "Random Forest",
                 datetime.now().strftime("%Y-%m-%d"),
                 MODEL_ACCURACY, "artifacts/" + MODEL_FILE, len(FEATURES)))
    con.commit()
    con.close()


init_db()


class ScanRequest(BaseModel):
    url: str


def contributions(vector):
    """Rank features by importance x deviation from the neutral value."""
    imp = np.array(MODEL.feature_importances_)
    neutral = np.array([60, 20, 15, 0, 1, 0, 0, 0, 0, 1, 0, 0.05, 0, 0, 0, 0], dtype=float)
    dev = np.abs(np.asarray(vector, dtype=float) - neutral) / (np.abs(neutral) + 1.0)
    score = imp * dev
    order = np.argsort(score)[::-1]
    out = []
    for i in order:
        if score[i] <= 0:
            continue
        out.append({"feature": FEATURES[i], "value": round(float(vector[i]), 4),
                    "importance": round(float(imp[i]), 4)})
        if len(out) == 5:
            break
    return out


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


def domain_only_reading(url):
    """p(phishing) for the main domain on its own: scheme and host, everything after the slash gone.

    The model's path features are an artefact of its training data, and on the field test they
    produce 41.59 per cent of false accusations against legitimate URLs that carry a path, while
    the domain alone produces 3.00 per cent and loses no hostile address (Section 4.6.8). This is
    that second opinion. Returns None when the address cannot be parsed.
    """
    parts = urllib.parse.urlsplit(url)
    if not parts.netloc:
        return None
    feats = extract_features(f"{parts.scheme}://{parts.netloc}")
    if feats is None:
        return None
    vector = [feats[f] for f in FEATURES]
    proba = MODEL.predict_proba([vector])[0]
    return float(proba[list(MODEL.classes_).index(1)])


@app.post("/api/classify")
def classify(req: ScanRequest):
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="A URL is required.")
    if "://" not in url:
        # An address typed without a scheme is read as https, the assumption a browser makes for a
        # bare hostname, and the interface shows the normalised address it analysed rather than
        # hiding the assumption. The cost is real and measured: assuming https removes the scheme
        # signal from a hostile http-only address typed without its scheme (Section 5.5).
        url = "https://" + url
    feats = extract_features(url)
    if feats is None:
        raise HTTPException(status_code=422, detail="The URL could not be parsed.")
    vector = [feats[f] for f in FEATURES]
    t0 = time.perf_counter()
    proba = MODEL.predict_proba([vector])[0]
    latency = (time.perf_counter() - t0) * 1000
    classes = list(MODEL.classes_)          # train.py recodes: 1 = phishing, 0 = legitimate
    p_phish = float(proba[classes.index(1)])
    verdict = "phishing" if p_phish >= 0.5 else "legitimate"
    conf = p_phish if verdict == "phishing" else 1 - p_phish

    con = sqlite3.connect(DB)
    con.execute("INSERT INTO scan_record (url, verdict, confidence, model_id, created_at) "
                "VALUES (?,?,?,?,?)",
                (url, verdict, conf, MODEL_ID, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()

    host = host_of(url)
    known = is_allowlisted(url, ALLOW_LOOKUP)
    if registrable(host) in ALLOW_OPERATOR:
        source = "operator"
    elif on_restricted_registry(host):
        source = "restricted-registry"
    elif registrable(host) in ALLOW_NG:
        source = "nigerian"
    elif registrable(host) in ALLOW_GLOBAL:
        source = "global"
    else:
        source = None

    # The second opinion: does the main domain, judged on its own, support the accusation?
    p_domain = domain_only_reading(url)
    path_driven = bool(verdict == "phishing" and p_domain is not None and p_domain < 0.5)

    NOTE = {
        "domain-first": ("The main domain — {domain} — reads as legitimate on its own, with "
                         "everything after the slash removed. The accusation therefore comes "
                         "from the rest of the address rather than from the domain itself, so "
                         "the verdict is shown as unverified rather than malicious."),
        "operator": ("The domain is in this deployment's own trusted-domain list, which the "
                     "operator maintains first-hand. The classifier accused it anyway, so "
                     "the verdict is shown as unverified rather than malicious."),
        "global": ("The domain is in the bundled list of the 100,000 most popular domain "
                   "names, but the classifier scored this URL as phishing. This pattern is "
                   "usually a false positive: treat it as unverified rather than malicious."),
        "nigerian": ("The domain is in the bundled Nigerian reputation list, but the "
                     "classifier scored this URL as phishing. The global popularity list does "
                     "not cover Nigerian domains at all, which is why this list is consulted "
                     "separately. Treat the verdict as unverified rather than malicious."),
        "restricted-registry": ("The host sits under a restricted Nigerian second-level "
                                "registry (.gov.ng or .edu.ng), where registration is limited "
                                "to verified institutions. That lowers the odds of a deceptive "
                                "domain, but a compromised host is still possible, so treat the "
                                "verdict as unverified rather than malicious."),
    }

    # An accusation is downgraded to "unverified" — never cleared to "legitimate" — for either of
    # two independent reasons: a curated list knows the domain, or the domain alone does not
    # support the accusation and it rests on the shape of the address instead.
    accuse = verdict == "phishing"
    if accuse and known and source:
        reason, note = source, NOTE[source]
    elif accuse and path_driven:
        reason, note = "domain-first", NOTE["domain-first"].format(domain=registrable(host))
    else:
        reason, note = None, None

    return JSONResponse({
        "url": url,
        "verdict": verdict,
        "reputation": {
            "known_domain": bool(known),
            "domain": registrable(host),
            "list": reason,
            "conflict": bool(reason is not None),
            "adjudication": "unverified" if reason is not None else None,
            "domain_only_probability_phishing": (None if p_domain is None
                                                 else round(p_domain * 100, 2)),
            "note": note,
        },
        "confidence": round(conf * 100, 2),
        "probability_phishing": round(p_phish * 100, 2),
        "latency_ms": round(latency, 2),
        "model": "Random Forest (" + MODEL_VERSION + ")",
        "evidence": contributions(vector),
        "features": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in feats.items()},
    })


@app.get("/api/history")
def history(limit: int = 20):
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT scan_id, url, verdict, confidence, created_at FROM scan_record "
        "ORDER BY scan_id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    def shown(u, v):
        """What the interface presented for this row — the same rule as /api/classify, so the
        log and the panel can never disagree."""
        if v != "phishing":
            return v
        if is_allowlisted(u, ALLOW_LOOKUP):
            return "unverified"
        p = domain_only_reading(u)
        return "unverified" if (p is not None and p < 0.5) else v

    return {"count": len(rows),
            "records": [{"scan_id": r[0], "url": r[1], "verdict": r[2],
                         "adjudication": shown(r[1], r[2]),
                         "confidence": round(r[3] * 100, 2), "created_at": r[4]}
                        for r in rows]}


@app.get("/api/metrics")
def metrics():
    return {"model_id": MODEL_ID, "algorithm": "Random Forest",
            "model_version": MODEL_VERSION, "variant": SELECTED.get("variant", "baseline"),
            "n_features": len(FEATURES),
            "allowlist_domains": len(ALLOW),
            "allowlist_operator": len(ALLOW_OPERATOR),
            "results": META["results"],
            "selected": SELECTED,
            "dataset": META["dataset"]}