
import sys, urllib.parse as up, joblib
from train import FEATURES, extract_features
m = joblib.load("artifacts/model_selected.joblib")
ci = list(m.classes_).index(1)
def p(url):
    f = extract_features(url)
    if f is None: return None
    return float(m.predict_proba([[f[k] for k in FEATURES]])[0][ci])
def d_only(u):
    s = up.urlsplit(u); return f"{s.scheme}://{s.netloc}"
urls = [l.strip() for l in open("data/pdb_active.txt", errors="ignore")]
urls = [u for u in urls if u.lower().startswith("http")]
print(f"full hostile URLs: {len(urls):,}", flush=True)
lost, kept, miss = [], 0, 0
for i, u in enumerate(urls):
    if i and i % 1000 == 0: print(f"  {i:,} done", flush=True)
    pf = p(u)
    if pf is None or pf < 0.5: miss += 1; continue
    pd = p(d_only(u))
    if pd is not None and pd < 0.5: lost.append((u, pf, pd))
    else: kept += 1
tot = kept + len(lost)
print(f"accused by the whole address: {tot:,} of {len(urls):,}")
print(f"  still accused by the domain alone: {kept:,}")
print(f"  downgraded to UNVERIFIED by the rule: {len(lost):,} ({len(lost)/max(1,tot)*100:.2f}% of accusations)", flush=True)
for u, pf, pd in lost[:15]: print(f"    {u[:68]:<70} full={pf:.3f} domain={pd:.3f}")
