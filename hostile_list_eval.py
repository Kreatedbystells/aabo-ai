"""What the bundled hostile blocklist actually restores - measured on independent feeds.

Section 4.6.8 measured the domain-first rule's cost on 2,000 hostile domains drawn from
Phishing Army, the very list now bundled. Scoring its restoration on that same sample would be
circular: the sample came from the list, so coverage would be near 100 per cent by construction.
That number is computed here anyway, and labelled coverage-of-itself.

The informative measurement uses hostile domains from two sources that did not supply the bundled
list:

  A. Phishing.Database (data/pdb_active.txt) - a different aggregator from Phishing Army. Both
     draw on community reports, so overlap is an empirical fact measured here, not an assumption.
  B. the PhiUSIIL corpus's own phishing class (data/PhiUSIIL_Phishing_URL_Dataset.csv) - the
     corpus this project trains on, and wholly independent of either blocklist. Its domains are in
     the training data, so the classifier's accusation rate on them is optimistic; that affects the
     cost column, not the restoration ratio, which is measured on the same accusations.

Shape is identical to Section 4.6.8: score the bare domain, score it with /verify/account appended,
and count the accusations the domain-first rule would weaken. A weakened accusation whose
registrable domain is on the bundled list is one the list restores.

Writes artifacts/hostile_list_eval.json.
"""
import csv
import json
import random
import sys
import urllib.parse as up

import joblib
import numpy as np

HERE = "/Users/amarachi/Downloads/Stella_Project"
sys.path.insert(0, HERE)
from domain_utils import registrable                              # noqa: E402
from train import FEATURES, extract_features                      # noqa: E402

N = 2000
PATH = "/verify/account"          # same suffix as Section 4.6.8
SEED = 42
ART = f"{HERE}/artifacts"

BLOCKED = {l.strip() for l in open(f"{ART}/blocklist_hostile.txt") if l.strip()}
print(f"bundled hostile list: {len(BLOCKED):,} registrable domains", flush=True)

model = joblib.load(f"{ART}/model_selected.joblib")
CI = list(model.classes_).index(1)


def p(url):
    f = extract_features(url)
    if f is None:
        return None
    return float(model.predict_proba([[f[k] for k in FEATURES]])[0][CI])


def domains_from(urls):
    out, seen = [], set()
    for u in urls:
        h = (up.urlsplit(u).hostname or "").lower()
        reg = registrable(h) if h else None
        if reg and reg not in seen:
            seen.add(reg)
            out.append(reg)
    return out


def measure(name, domains, rng, provenance):
    sample = rng.sample(domains, min(N, len(domains)))
    bare_legit = accused_with_path = lowered = restored = 0
    examples = []
    for i, d in enumerate(sample, 1):
        if i % 500 == 0:
            print(f"  {name}: {i:,}/{len(sample):,}", flush=True)
        pb, pp = p("https://" + d), p("https://" + d + PATH)
        if pb is None or pp is None:
            continue
        if pb < 0.5:
            bare_legit += 1
        if pp >= 0.5:
            accused_with_path += 1
            if pb < 0.5:
                lowered += 1
                hit = d in BLOCKED
                restored += hit
                if len(examples) < 6:
                    examples.append({"host": d, "bare_pct": round(pb * 100, 2),
                                     "with_path_pct": round(pp * 100, 2),
                                     "on_bundled_list": hit})
    out = {
        "source": name,
        "provenance": provenance,
        "pool_domains": len(domains),
        "sample": len(sample),
        "read_legitimate_on_its_own": bare_legit,
        "accused_once_it_carries_a_path": accused_with_path,
        "weakened_by_the_domain_first_rule": lowered,
        "restored_by_bundled_list": restored,
        "restored_pct_of_weakened": round(restored / max(1, lowered) * 100, 2),
        "restored_pct_of_sample": round(restored / max(1, len(sample)) * 100, 2),
        "examples": examples,
    }
    print(f"  {name}: weakened {lowered}, restored {restored} "
          f"({out['restored_pct_of_weakened']}%)", flush=True)
    return out


# --- A. Phishing.Database: full hostile URLs -> registrable domains -------------------------
pdb = [l.strip() for l in open(f"{HERE}/data/pdb_active.txt", errors="ignore")]
pdb = [u if "://" in u else "http://" + u for u in pdb if u]
A_doms = domains_from(pdb)
print(f"Phishing.Database: {len(pdb):,} feed entries -> {len(A_doms):,} registrable domains",
      flush=True)

# --- B. PhiUSIIL phishing class ------------------------------------------------------------
with open(f"{HERE}/data/PhiUSIIL_Phishing_URL_Dataset.csv", errors="ignore") as fh:
    rd = csv.DictReader(fh)
    ucol = "URL" if "URL" in rd.fieldnames else rd.fieldnames[0]
    lcol = "label" if "label" in rd.fieldnames else rd.fieldnames[-1]
    phish_urls = [r[ucol] for r in rd if r[lcol].strip() in ("1", "1.0")]
B_doms = domains_from(phish_urls)
print(f"PhiUSIIL phishing class: {len(phish_urls):,} URLs -> {len(B_doms):,} registrable domains",
      flush=True)

# --- C. coverage-of-itself: the Section 4.6.8 sample, drawn FROM the bundled list ----------
pa = [l.strip() for l in open(f"{HERE}/data/pa.txt", errors="ignore")]
pa = [d for d in pa if d and not d.lower().startswith("http")]
pa_doms = domains_from(["http://" + d for d in pa])
C = measure("Phishing Army (the bundled list's own source)",
            pa_doms, random.Random(SEED),
            "coverage-of-itself: this sample supplied the bundled list, so a high figure is "
            "arithmetic, not evidence")

res = {
    "bundled_list_domains": len(BLOCKED),
    "path_suffix": PATH,
    "seed": SEED,
    "independent_sources": [measure("Phishing.Database", A_doms, random.Random(SEED),
                                   "independent aggregator; the feed the field test's 500 hostile "
                                   "full URLs came from"),
                            measure("PhiUSIIL phishing class", B_doms, random.Random(SEED),
                                    "the corpus this project trains on; independent of both "
                                    "blocklists, but present in training data")],
    "coverage_of_itself": C,
}
json.dump(res, open(f"{ART}/hostile_list_eval.json", "w"), indent=1)
print("\nSAVED artifacts/hostile_list_eval.json", flush=True)
for s in res["independent_sources"]:
    print(f"{s['source']}: sample {s['sample']}, weakened {s['weakened_by_the_domain_first_rule']}, "
          f"restored {s['restored_by_bundled_list']} ({s['restored_pct_of_weakened']}%)")
