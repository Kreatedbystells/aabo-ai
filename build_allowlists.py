"""Build the reputation allow-lists used by the application and the evaluation.

Public Suffix List extraction, platform hosts removed, two tiers written:
  artifacts/allowlist_top10k.txt    domains in Umbrella ranks 1-10,000
  artifacts/allowlist_top100k.txt   domains in Umbrella ranks 1-100,000
Also reports how many hostile test domains each tier would wrongly clear.
"""
import collections
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from domain_utils import PLATFORM_HOSTS, host_of, on_platform_host, registrable   # noqa: E402

ART = os.path.join(HERE, "artifacts")


def build(limit):
    doms = set()
    with open(os.path.join(HERE, "data", "top-1m.csv"), errors="ignore") as fh:
        for line in fh:
            rank, _, dom = line.strip().partition(",")
            if int(rank) > limit:
                break
            if not dom:
                continue
            reg = registrable(dom)
            if reg and not on_platform_host(reg) and reg not in PLATFORM_HOSTS:
                doms.add(reg)
    return doms


def hostile_overlap(allow):
    pdb = [l.strip() for l in open(os.path.join(HERE, "data", "pdb_active.txt"),
                                   errors="ignore") if l.lower().startswith("http")]
    pa = ["https://" + l.strip() for l in open(os.path.join(HERE, "data", "pa.txt"),
                                               errors="ignore")
          if l.strip() and not l.lower().startswith("http")]
    rng = random.Random(42)
    sample = rng.sample(pdb, 500) + rng.sample(pa, 500)
    hits = collections.Counter()
    for u in sample:
        h = host_of(u)
        reg = registrable(h)
        if reg and reg in allow and not on_platform_host(h) and not on_platform_host(reg):
            hits[reg] += 1
    return sum(hits.values()), hits.most_common(10)


if __name__ == "__main__":
    out = {}
    for tier, limit in (("top10k", 10_000), ("top100k", 100_000)):
        doms = build(limit)
        path = os.path.join(ART, f"allowlist_{tier}.txt")
        open(path, "w").write("\n".join(sorted(doms)))
        n_hostile, top = hostile_overlap(doms)
        out[tier] = {"domains": len(doms), "hostile_urls_cleared_of_1000": n_hostile,
                     "worst_offenders": top}
        print(f"{tier}: {len(doms):,} domains after PSL + platform exclusions; "
              f"clears {n_hostile}/1000 hostile test URLs")
        print("   ", top)
    json.dump(out, open(os.path.join(ART, "allowlist_report.json"), "w"), indent=2)
    print("\nwrote artifacts/allowlist_report.json")