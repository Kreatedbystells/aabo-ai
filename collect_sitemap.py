"""Second legitimate-URL collector: sitemaps.

Home pages increasingly publish few plain <a href> links because navigation is
rendered in JavaScript. Sitemaps do not have that problem: a site publishes them
precisely so that crawlers can find its pages. This pass reads robots.txt for a
Sitemap: directive, falls back to /sitemap.xml, and keeps same-registrable-domain
URLs that actually carry a path or a query.

Output: data/legit_sitemap.json
"""
import gzip
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "legit_sitemap.json")
# UA string exactly as sent during collection (project renamed afterwards; kept verbatim)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120 Safari/537.36 PhishGuard-academic-research/1.0"

N_DOMAINS = int(os.environ.get("N_DOMAINS", "3000"))
MAX_URLS = 40
TIMEOUT = 10
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
SM = re.compile(r"(?im)^\s*Sitemap:\s*(\S+)\s*$")
SKIP_TLDS = re.compile(r"\.(gov|mil|edu)$", re.I)


def registrable(host):
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def fetch(url, limit=600_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read(limit)
    if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(limit)
    return raw.decode("utf-8", "ignore")


def collect(domain):
    reg = registrable(domain)
    base = f"https://{domain}"
    candidates = []
    try:
        rb = fetch(base + "/robots.txt", 200_000)
        candidates += [m.strip() for m in SM.findall(rb)][:3]
    except Exception:
        pass
    candidates += [base + "/sitemap.xml", base + "/sitemap_index.xml"]

    urls, seen = [], set()
    for sm in candidates:
        if len(urls) >= MAX_URLS:
            break
        try:
            xml = fetch(sm)
        except Exception:
            continue
        locs = LOC.findall(xml)
        # a sitemap index points at other sitemaps: follow the first child
        if locs and all(l.endswith(".xml") or ".xml?" in l for l in locs[:5]):
            for child in locs[:2]:
                try:
                    xml2 = fetch(child)
                    locs += LOC.findall(xml2)
                except Exception:
                    pass
        for loc in locs:
            try:
                p = urllib.parse.urlsplit(loc)
            except Exception:
                continue
            host = (p.netloc or "").lower().split(":")[0]
            if not host or registrable(host) != reg:
                continue
            if (p.path in ("", "/")) and not p.query:
                continue
            clean = urllib.parse.urlunsplit((p.scheme or "https", p.netloc, p.path, p.query, ""))
            if clean in seen:
                continue
            seen.add(clean)
            urls.append(clean)
            if len(urls) >= MAX_URLS:
                break
    return domain, urls


def main():
    rows = []
    with open(os.path.join(HERE, "data", "top-1m.csv"), errors="ignore") as fh:
        for line in fh:
            rank, _, dom = line.strip().partition(",")
            if not dom or not dom.isascii() or SKIP_TLDS.search(dom):
                continue
            r = int(rank)
            if r < 1000 or r > 200_000:
                continue
            rows.append(dom)
            if len(rows) >= N_DOMAINS:
                break

    print(f"sitemap pass over {len(rows)} domains ...", flush=True)
    domains, t0 = {}, time.time()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(collect, d): d for d in rows}
        for i, fu in enumerate(as_completed(futs), 1):
            dom, urls = fu.result()
            if urls:
                domains[dom] = urls
            if i % 100 == 0:
                print(f"  {i}/{len(rows)} domains, "
                      f"{sum(len(v) for v in domains.values())} URLs, {time.time()-t0:.0f}s",
                      flush=True)

    meta = {
        "source": "Cisco Umbrella top-1M, ranks 1,000-200,000",
        "method": "robots.txt Sitemap directive, falling back to /sitemap.xml; "
                  "same-registrable-domain URLs with a path or query kept, up to 40 per domain",
        "domains_attempted": len(rows), "domains_with_urls": len(domains),
        "urls_collected": sum(len(v) for v in domains.values()),
        "collected_on": time.strftime("%Y-%m-%d"),
    }
    json.dump({"meta": meta, "domains": domains}, open(OUT, "w"), indent=1)
    print(json.dumps(meta, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()