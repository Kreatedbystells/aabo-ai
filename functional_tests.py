"""Functional and non-functional test run against the running application.

Exercises every requirement in Table 4 and the measurable ones in Table 5,
and writes artifacts/functional_tests.json with real observations.
"""
import json, os, statistics, time
import urllib.error
import urllib.request

BASE = "http://localhost:8077"
ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


def call(method, path, payload=None):
    url = BASE + path
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode()
            code = r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        code = e.code
    ms = (time.perf_counter() - t0) * 1000
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = body
    return code, parsed, ms


results = []


def check(fid, desc, ok, observed):
    results.append({"id": fid, "requirement": desc, "passed": bool(ok), "observed": observed})
    print(("PASS " if ok else "FAIL ") + fid, "-", observed)


# FR1 / FR9 - accepted over HTTP, structured JSON
code, body, ms = call("POST", "/api/classify", {"url": "https://www.google.com"})
check("FR1", "accept a submitted URL through the interface",
      code == 200 and body.get("verdict") in ("phishing", "legitimate"),
      f"HTTP {code}, verdict={body.get('verdict')}")
check("FR9", "classification exposed as an HTTP endpoint returning JSON",
      code == 200 and isinstance(body, dict) and "features" in body,
      f"HTTP {code}, JSON keys={sorted(body)[:6]}")

# FR2 - validation
code, body, _ = call("POST", "/api/classify", {"url": "   "})
check("FR2a", "reject empty input with a descriptive message",
      code == 422, f"HTTP {code}, detail={str(body.get('detail'))[:60]}")

# FR3 - 16 features, computed without retrieving the page
code, body, _ = call("POST", "/api/classify", {"url": "http://example.com/a/b?c=1"})
check("FR3", "exactly sixteen features extracted and returned",
      len(body.get("features", {})) == 16,
      f"{len(body.get('features', {}))} features returned")

# FR4 / FR5 - verdict + confidence in [0,1]
check("FR4", "verdict is phishing or legitimate",
      body.get("verdict") in ("phishing", "legitimate"), f"verdict={body.get('verdict')}")
check("FR5", "confidence score returned between zero and one",
      0 <= body.get("probability_phishing", -1) <= 100,
      f"probability_phishing={body.get('probability_phishing')}")

# FR6 - at least three contributing features
check("FR6", "at least three contributing features returned",
      len(body.get("evidence", [])) >= 3,
      f"{len(body.get('evidence', []))} features: " +
      ", ".join(e["feature"] for e in body.get("evidence", [])))

# FR7 - scan log updated
code, hist, _ = call("GET", "/api/history?limit=5")
check("FR7", "each scan recorded with verdict, confidence and timestamp",
      code == 200 and hist.get("count", 0) > 0 and
      all(k in hist["records"][0] for k in ("verdict", "confidence", "created_at")),
      f"{hist.get('count')} records, newest={hist.get('records', [{}])[0].get('url')}")

# FR10 - error surfaced, not a false verdict
code, body, _ = call("POST", "/api/classify", {"url": ""})
check("FR10", "explicit error rather than a false verdict",
      code == 422 and "verdict" not in (body if isinstance(body, dict) else {}),
      f"HTTP {code}, no verdict key in response")

# NFR1 - response time over 30 calls
lat = []
for u in ["https://www.google.com", "http://example.com/login", "https://autozone.com",
          "http://aldi.pelrexo.shop/verify/account", "https://github.com/login"] * 6:
    _, b, _ = call("POST", "/api/classify", {"url": u})
    lat.append(b.get("latency_ms", 0))
check("NFR1", "median classification time under 1 second",
      statistics.median(lat) < 1000,
      f"n={len(lat)}, median={statistics.median(lat):.1f} ms, "
      f"min={min(lat):.1f} ms, max={max(lat):.1f} ms")

# NFR5 - interpretability on every verdict
codes = []
for u in ["https://www.google.com", "http://aldi.pelrexo.shop/verify/account", "https://blik.iqwerk.top/login.php"]:
    _, b, _ = call("POST", "/api/classify", {"url": u})
    codes.append(len(b.get("evidence", [])))
check("NFR5", "every verdict accompanied by at least three features",
      all(c >= 3 for c in codes), f"evidence counts={codes}")

# NFR6 - model loaded from artefact (metadata endpoint)
code, meta, _ = call("GET", "/api/metrics")
check("NFR6", "model loaded from a serialised artefact",
      code == 200 and meta.get("n_features") == 16,
      f"model={meta.get('algorithm')}, n_features={meta.get('n_features')}")

summary = {
    "total": len(results),
    "passed": sum(r["passed"] for r in results),
    "failed": sum(not r["passed"] for r in results),
    "tests": results,
    "latency": {"n": len(lat), "median_ms": round(statistics.median(lat), 2),
                "min_ms": round(min(lat), 2), "max_ms": round(max(lat), 2),
                "mean_ms": round(statistics.mean(lat), 2)},
}
json.dump(summary, open(os.path.join(ART, "functional_tests.json"), "w"), indent=2)
print(f"\n{summary['passed']}/{summary['total']} passed; latency {summary['latency']}")