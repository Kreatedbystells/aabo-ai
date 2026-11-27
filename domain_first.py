"""Domain-first experiment: does judging the main domain (before the slash) fix the false positives?

For every URL in the study's field test, compare the deployed model's verdict on
  (a) the whole address, and
  (b) the domain alone (scheme + host, path and query stripped)
and report what a policy of "let the domain decide, not the path" would buy and cost.
Writes artifacts/domain_first.json.
"""
import json
import os
import random
import urllib.parse as up

import joblib
import numpy as np
from sklearn.model_selection import train_test_split

import retrain as R
from train import FEATURES, extract_features

TAU = 0.5


def domain_only(url):
    """The main domain: scheme and host, with everything after the slash removed."""
    p = up.urlsplit(url.strip())
    return f"{p.scheme}://{p.netloc}" if p.netloc else url


def featurise_urls(urls, transform=lambda u: u):
    X, keep = [], []
    for u in urls:
        f = extract_features(transform(u))
        if f is None:
            continue
        X.append([f[k] for k in FEATURES])
        keep.append(u)
    return np.asarray(X, dtype=float), keep


def accused(model, X):
    """1 where the model accuses (p >= 0.5)."""
    return (model.predict_proba(X)[:, list(model.classes_).index(1)] >= TAU).astype(int)


def main():
    print("loading data ...", flush=True)
    Xp, yp, up_all = R.load_phiusiil()
    legit_tr, legit_te, tr_doms, te_doms, n_doms = R.load_legit()
    phish_full, phish_bare = R.load_phishing_feeds()
    print(f"PhiUSIIL {len(Xp):,} | legit {len(legit_tr) + len(legit_te):,} over {n_doms:,} domains",
          flush=True)

    Xp_tr, Xp_te, yp_tr, yp_te, up_tr, up_te = train_test_split(
        Xp, yp, up_all, test_size=0.2, stratify=yp, random_state=R.SEED)
    Xl_te, kept_te = R.featurise(legit_te)
    rng = random.Random(R.SEED)
    bare_idx = [i for i in range(len(yp_te)) if yp_te[i] == 0]
    bare_idx = rng.sample(bare_idx, min(5_000, len(bare_idx)))
    Xf_full, kept_full = R.featurise(phish_full)
    Xf_bare, kept_bare = R.featurise(phish_bare)

    field_urls = kept_te + [up_te[i] for i in bare_idx] + kept_full + kept_bare
    n_path, n_bare = len(kept_te), len(bare_idx)
    n_phish = len(kept_full) + len(kept_bare)
    print(f"field test: {n_path:,} legit with paths | {n_bare:,} legit bare | "
          f"{n_phish:,} hostile ({len(kept_full)} full + {len(kept_bare)} bare)", flush=True)

    model = joblib.load(os.path.join(R.ART, "model_selected.joblib"))
    print("model loaded; featurising the domain-only form of every field URL ...", flush=True)
    Xd, kept_d = featurise_urls(field_urls, domain_only)
    assert kept_d == field_urls, "dropped rows would misalign the comparison"

    full = accused(model, R.featurise(field_urls)[0])
    dom = accused(model, Xd)

    out = {}

    def block(name, lo, hi):
        f, d = full[lo:hi], dom[lo:hi]
        n = hi - lo
        cleared = int(((f == 1) & (d == 0)).sum())
        created = int(((f == 0) & (d == 1)).sum())
        out[name] = {
            "n": n,
            "accused_by_full_address": int(f.sum()),
            "accused_by_domain_alone": int(d.sum()),
            "false_positive_rate_full": round(float(f.mean()) * 100, 2),
            "false_positive_rate_domain_only": round(float(d.mean()) * 100, 2),
            "accusations_a_domain_only_verdict_would_clear": cleared,
            "accusations_the_domain_only_verdict_would_add": created,
        }
        print(name, json.dumps(out[name], indent=1), flush=True)

    block("legit_with_paths", 0, n_path)
    block("legit_bare_domains", n_path, n_path + n_bare)
    block("hostile", n_path + n_bare, len(field_urls))

    hp = full[n_path + n_bare:]
    dp = dom[n_path + n_bare:]
    out["hostile_detail"] = {
        "caught_by_full_address": int(hp.sum()),
        "caught_by_domain_alone": int(dp.sum()),
        "caught_by_full_but_lost_by_domain_alone": int(((hp == 1) & (dp == 0)).sum()),
        "recall_full": round(float(hp.mean()) * 100, 2),
        "recall_domain_only": round(float(dp.mean()) * 100, 2),
    }
    print("hostile_detail", json.dumps(out["hostile_detail"], indent=1), flush=True)

    # the policy applied: an accusation stands only if the domain alone is also accused
    policy = full.copy()
    policy[(full == 1) & (dom == 0)] = 0
    legit_all = policy[:n_path + n_bare]
    phish_all = policy[n_path + n_bare:]
    tp = int(phish_all.sum())
    fp = int(legit_all.sum())
    fn = n_phish - tp
    precision = tp / max(1, tp + fp) * 100
    recall = tp / max(1, n_phish) * 100
    out["policy_whole_field"] = {
        "false_positives": fp, "true_positives": tp, "false_negatives": fn,
        "false_positive_rate": round(fp / max(1, len(legit_all)) * 100, 2),
        "recall": round(recall, 2), "precision": round(precision, 2),
        "f1": round(2 * precision * recall / max(1e-9, precision + recall), 2),
    }
    print("policy_whole_field", json.dumps(out["policy_whole_field"], indent=1), flush=True)

    json.dump(out, open(os.path.join(R.ART, "domain_first.json"), "w"), indent=1)
    print("SAVED artifacts/domain_first.json", flush=True)


if __name__ == "__main__":
    main()
