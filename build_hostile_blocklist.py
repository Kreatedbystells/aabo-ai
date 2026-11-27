"""Build the bundled hostile-domain blocklist used by the deployed application.

Source: Phishing Army (https://phishing.army/), a community blocklist aggregated from
PhishTank, OpenPhish, CERT.PL, Phishunt, urlscan.io, PhishStats, StalkPhish, URLAbuse and
AntiPhish.org. It is a *different* feed from the one the field test's hostile URLs came from
(Phishing.Database), which is what makes the cross-feed measurement in hostile_list_eval.py
informative rather than circular.

Normalisation matches build_allowlists.py: Public Suffix List extraction, so a subdomain entry
condemns its registrable domain. Two exclusions, both deliberate:

  * the list's own harmless filtering-test entries (amiprotected.it) — they exist to test that a
    filter is running, and treating them as hostile would be a false accusation by construction;
  * this project's PLATFORM_HOSTS (free hosting, shorteners): blocking one of those wholesale
    condemns every legitimate site on it, so an accusation against such a host is left to the
    classifier instead of being fortified by this list.

A hostile list may only ever *support* an accusation. It never creates one and never clears one.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from domain_utils import PLATFORM_HOSTS, on_platform_host, registrable   # noqa: E402

ART = os.path.join(HERE, "artifacts")
TEST_ENTRIES = {"amiprotected.it"}          # the list's own filtering test, not a report


def build():
    raw = []
    for line in open(os.path.join(HERE, "data", "pa.txt"), errors="ignore"):
        line = line.strip()
        if not line or line.startswith("#") or " " in line or line.lower().startswith("http"):
            continue
        raw.append(line.lower().rstrip("."))

    doms, dropped_test, dropped_platform, dropped_junk = set(), set(), set(), 0
    for h in raw:
        if any(c in h for c in "*") or ".." in h or "." not in h:
            dropped_junk += 1
            continue
        reg = registrable(h)
        if not reg or "." not in reg:
            dropped_junk += 1
            continue
        if reg in TEST_ENTRIES or h in TEST_ENTRIES:
            dropped_test.add(reg)
            continue
        # Only the platform apex is dropped, never the specific subdomain. `abc.web.app` is a
        # registrable domain of its own under the Public Suffix List, and it is the shape of the
        # modern campaign; listing it can only *support* an accusation the classifier already
        # made, never clear one, so excluding it would throw the list's value away.
        if reg in PLATFORM_HOSTS:
            dropped_platform.add(reg)
            continue
        doms.add(reg)

    path = os.path.join(ART, "blocklist_hostile.txt")
    open(path, "w").write("\n".join(sorted(doms)) + "\n")

    out = {
        "source": "Phishing Army (https://phishing.army/)",
        "licence": "see https://phishing.army/license/ - non-commercial use, attribution retained here",
        "raw_entries": len(raw),
        "registrable_domains": len(doms),
        "excluded_test_entries": sorted(dropped_test),
        "excluded_platform_apexes": sorted(dropped_platform),
        "dropped_malformed": dropped_junk,
        "file": "artifacts/blocklist_hostile.txt",
    }
    json.dump(out, open(os.path.join(ART, "blocklist_report.json"), "w"), indent=1)
    print(f"raw entries {len(raw):,} -> registrable domains {len(doms):,}")
    print(f"excluded test entries: {sorted(dropped_test)}")
    print(f"excluded platform apexes ({len(dropped_platform)}): {sorted(dropped_platform)}")
    print(f"dropped malformed: {dropped_junk}")
    print("wrote artifacts/blocklist_hostile.txt and artifacts/blocklist_report.json")


if __name__ == "__main__":
    build()
