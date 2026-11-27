"""Collect a legitimate URL corpus that includes paths, queries and depth.

The finding in Section 4.5.3 is that every legitimate URL in PhiUSIIL is a bare
domain, so the classifier never learns what a legitimate URL with a path looks
like. This script fixes the input data rather than the algorithm.

Method: for each popular domain (Cisco Umbrella top-1M ranks 1..N), fetch the
home page once, extract the same-registrable-domain links from its navigation,
and keep the resulting URLs. One request per domain, respectfully rate limited,
robots.txt respected, no page content stored - only the URLs that the site's own
navigation publishes.

Output: data/legit_collected.json  = {"domains": {domain: [url, ...]}, "meta": {...}}
"""
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "legit_collected.json")
# UA string exactly as sent during collection (project renamed afterwards; kept verbatim)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120 Safari/537.36 PhishGuard-academic-research/1.0"

N_DOMAINS = int(os.environ.get("N_DOMAINS", "420"))
MAX_LINKS = 40
TIMEOUT = 10
SKIP_TLDS = re.compile(r"\.(gov|mil|edu)$", re.I)
SKIP_SUB = re.compile(r"^(mail|webmail|owa|vpn|remote|intranet|portal)\.", re.I)
HREF = re.compile(r'href=["\']([^"\'#]+)["\']', re.I)


def registrable(host):
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def robots_allows(base, path="/"):
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        rp.read()
        return rp.can_fetch(UA, base + path)
    except Exception:
        return True                     # absence of robots.txt means allowed


def collect(domain):
    """Return (domain, [urls]) for one home page."""
    base = f"https://{domain}"
    if not robots_allows(base):
        return domain, []
    req = urllib.request.Request(base, headers={"User-Agent": UA,
                                                "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return domain, []
            ctype = r.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                return domain, []
            html = r.read(400_000).decode("utf-8", "ignore")
    except Exception:
        return domain, []

    reg = registrable(domain)
    seen, urls = set(), []
    for href in HREF.findall(html):
        if href.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = base + href
        elif not href.lower().startswith("http"):
            href = base + "/" + href.lstrip("./")
        try:
            p = urllib.parse.urlsplit(href)
        except Exception:
            continue
        if p.scheme not in ("http", "https"):
            continue
        host = (p.netloc or "").lower().split(":")[0]
        if not host or registrable(host) != reg:
            continue                                    # same site only
        if p.path in ("", "/") and not p.query:
            continue                                    # we want paths/queries
        clean = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
        if clean in seen:
            continue
        seen.add(clean)
        urls.append(clean)
        if len(urls) >= MAX_LINKS:
            break
    return domain, urls


def main():
    top = os.path.join(HERE, "data", "top-1m.csv")
    rows = []
    with open(top, errors="ignore") as fh:
        for line in fh:
            rank, _, dom = line.strip().partition(",")
            if not dom or not dom.isascii():
                continue
            if int(rank) < 1000 or int(rank) > 200_000:
                continue
            if SKIP_TLDS.search(dom) or SKIP_SUB.search(dom):
                continue
            rows.append((int(rank), dom))
            if len(rows) >= N_DOMAINS:
                break

    print(f"fetching {len(rows)} domains ...")
    domains = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(collect, d): d for _, d in rows}
        for i, fu in enumerate(as_completed(futs), 1):
            dom, urls = fu.result()
            if urls:
                domains[dom] = urls
            if i % 50 == 0:
                print(f"  {i}/{len(rows)} domains, {sum(len(v) for v in domains.values())} URLs, "
                      f"{time.time() - t0:.0f}s", flush=True)

    total = sum(len(v) for v in domains.values())
    meta = {
        "source": "Cisco Umbrella top-1M popularity list, ranks 1,000-200,000",
        "method": "one home-page fetch per domain; same-registrable-domain links extracted "
                  "from the published navigation; robots.txt respected; no page content stored",
        "domains_attempted": len(rows),
        "domains_with_links": len(domains),
        "urls_collected": total,
        "max_links_per_domain": MAX_LINKS,
        "collected_on": time.strftime("%Y-%m-%d"),
    }
    json.dump({"meta": meta, "domains": domains}, open(OUT, "w"), indent=1)
    print(json.dumps(meta, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()