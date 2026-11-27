"""Cost of the domain-first rule on the shape that matters: a plausible hostile domain carrying a path.

The PDB feed is dominated by IP-literal hosts, which the domain alone already condemns, so it cannot
show what the rule costs. Phishing Army's list is bare hostile domains, and the modern campaign shape
is one of those domains carrying a path — the shape that "aldi.pelrexo.shop/verify/account" has.
For a fixed sample, compare the bare reading with the reading once a path is present, and count how
many hostile addresses the rule would downgrade from Phishing to Unverified.
"""
import json
import random
import urllib.parse as up

import joblib
from train import FEATURES, extract_features

N = 2000
PATH = "/verify/account"

model = joblib.load("artifacts/model_selected.joblib")
ci = list(model.classes_).index(1)


def p(url):
    f = extract_features(url)
    if f is None:
        return None
    return float(model.predict_proba([[f[k] for k in FEATURES]])[0][ci])


doms = [l.strip() for l in open("data/pa.txt", errors="ignore")]
doms = [d for d in doms if d and not d.lower().startswith("http")]
print(f"hostile bare domains in Phishing Army: {len(doms):,}", flush=True)
rng = random.Random(42)
sample = rng.sample(doms, N)

bare_legit = with_path_accused = flipped = 0
examples = []
for i, d in enumerate(sample):
    if i and i % 500 == 0:
        print(f"  {i:,} done", flush=True)
    pb = p("https://" + d)
    pp = p("https://" + d + PATH)
    if pb is None or pp is None:
        continue
    if pb < 0.5:
        bare_legit += 1
    if pp >= 0.5:
        with_path_accused += 1
        if pb < 0.5:
            flipped += 1
            if len(examples) < 8:
                examples.append((d, pb, pp))

out = {
    "hostile_bare_domains_in_list": len(doms),
    "sample": N,
    "read_legitimate_on_its_own": bare_legit,
    "read_legitimate_on_its_own_pct": round(bare_legit / N * 100, 2),
    "accused_once_it_carries_a_path": with_path_accused,
    "accused_which_the_rule_downgrades": flipped,
    "downgraded_pct_of_path_accusations": round(flipped / max(1, with_path_accused) * 100, 2),
    "downgraded_pct_of_sample": round(flipped / N * 100, 2),
    "examples": [{"host": d, "bare": round(b * 100, 2), "with_path": round(a * 100, 2)}
                 for d, b, a in examples],
}
print(json.dumps(out, indent=1), flush=True)
json.dump(out, open("artifacts/domain_first_cost.json", "w"), indent=1)
print("SAVED artifacts/domain_first_cost.json", flush=True)
