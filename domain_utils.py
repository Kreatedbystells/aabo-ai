"""Shared domain utilities for the reputation layer.

Two problems had to be fixed before any allow-list could be trusted:

1. Naive "last two labels" extraction is wrong for multi-part public suffixes.
   `foo.com.br` was being read as registrable domain `com.br`, which would have
   put every Brazilian commercial domain on the allow-list. The Public Suffix
   List is the correct mechanism, so `publicsuffix2` is used here.

2. Free-hosting and shortener domains are popular because anyone can publish
   under them. Allow-listing `github.io`, `vercel.app`, `weebly.com` and the
   like clears genuine phishing, so they are excluded from the allow-list even
   when they appear in the popularity ranking.
"""
from functools import lru_cache

import publicsuffix2 as psl

# Popularity is not trustworthiness: content under these hosts is published by
# third parties, so a hostile page can live on a "popular" domain.
PLATFORM_HOSTS = {
    # free hosting and app platforms
    "github.io", "gitlab.io", "githubusercontent.com", "googleapis.com",
    "googleusercontent.com", "appspot.com", "firebaseapp.com", "web.app",
    "vercel.app", "netlify.app", "pages.dev", "workers.dev", "herokuapp.com",
    "onrender.com", "glitch.me", "repl.co", "replit.app", "weebly.com",
    "wixsite.com", "wordpress.com", "blogspot.com", "blogger.com", "tumblr.com",
    "sites.google.com", "myshopify.com", "webflow.io", "notion.site",
    "readthedocs.io", "sourceforge.io", "smugmug.com", "canva.site",
    "000webhostapp.com", "hostinger.site", "awardspace.com", "byethost.com",
    "infinityfreeapp.com", "epizy.com", "rf.gd", "42web.io",
    # dynamic dns
    "duckdns.org", "no-ip.org", "ddns.net", "hopto.org", "sytes.net",
    "zapto.org", "myftp.org", "servebeer.com", "dyndns.org", "dyndns.tv",
    # cloud storage and CDN buckets
    "amazonaws.com", "cloudfront.net", "azurewebsites.net", "blob.core.windows.net",
    "secureserver.net", "r2.dev", "backblazeb2.com",
    # shorteners and link pages
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "rb.gy", "cutt.ly",
    "is.gd", "shorturl.at", "tiny.cc", "rebrand.ly", "s.id", "linktr.ee",
    "beacons.ai", "linkin.bio", "carrd.co", "forms.gle", "typeform.com",
    "tally.so", "substack.com", "siteseal.com",
    # file and form hosts
    "dropbox.com", "drive.google.com", "box.com", "wetransfer.com", "we.tl",
    "onedrive.live.com", "sharepoint.com", "scribd.com", "docsend.com",
}


# .gov.ng and .edu.ng are restricted second-level registries: registration is limited to
# verified government agencies and accredited institutions, which raises the cost of
# planting a deceptive domain under them. A weaker signal than an explicit list entry,
# because an institution host can still be compromised, so it is only ever used to soften
# an accusation, never to silence one.
RESTRICTED_SUFFIXES = (".gov.ng", ".edu.ng", ".mil.ng")


def on_restricted_registry(host):
    """True when the host sits under a NIRA-restricted second-level registry."""
    return (host or "").lower().endswith(RESTRICTED_SUFFIXES)


@lru_cache(maxsize=200_000)
def registrable(host):
    """Registrable domain via the Public Suffix List, falling back to last two labels."""
    if not host:
        return ""
    host = host.lower().strip().rstrip(".")
    if host.count(".") < 1:
        return host
    try:
        return psl.get_sld(host, strict=True) or host
    except Exception:
        parts = [p for p in host.split(".") if p]
        return ".".join(parts[-2:]) if len(parts) >= 2 else host


def host_of(url):
    """Host name of a URL, without scheme, credentials or port."""
    u = url.strip()
    for scheme in ("https://", "http://", "//"):
        if u.lower().startswith(scheme):
            u = u[len(scheme):]
            break
    return u.split("/")[0].split("@")[-1].split(":")[0].lower()


def on_platform_host(host):
    """True if the host IS a platform host or sits under one (storage.googleapis.com)."""
    host = (host or "").lower()
    parts = host.split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in PLATFORM_HOSTS:
            return True
    return False


def is_allowlisted(url_or_host, allow_set):
    """True when the URL's registrable domain is on the list and not a platform host."""
    host = host_of(url_or_host) if ("://" in url_or_host or "/" in url_or_host) else url_or_host
    host = (host or "").lower()
    if not host or on_platform_host(host):
        return False
    if on_restricted_registry(host):
        return True
    reg = registrable(host)
    if not reg or on_platform_host(reg) or reg in PLATFORM_HOSTS:
        return False
    return reg in allow_set


def load_allowlist(path):
    """Read a reputation list, ignoring blank lines and '#' comments."""
    try:
        return {l.strip() for l in open(path)
                if l.strip() and not l.strip().startswith("#")}
    except FileNotFoundError:
        return set()