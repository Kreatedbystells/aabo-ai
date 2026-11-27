
import json, urllib.parse as up, joblib, numpy as np
from train import FEATURES, extract_features
m = joblib.load("artifacts/model_selected.joblib")
def d_only(u):
    p = up.urlsplit(u); return f"{p.scheme}://{p.netloc}"
def p(u):
    f = extract_features(u)
    v = [f[k] for k in FEATURES]
    pr = float(m.predict_proba([v])[0][list(m.classes_).index(1)])
    return pr, {k: f[k] for k in ("url_length","path_length","query_length","is_https","hostname_length")}
for u in ["https://www.gtbank.com/personal-banking", "https://www.gtbank.com",
          "https://www.paypal.com/signin", "https://www.paypal.com",
          "https://chairdoctorng.com/services", "https://chairdoctorng.com",
          "https://www.jumia.com.ng/phones-tablets/", "https://www.jumia.com.ng",
          "https://en.wikipedia.org/wiki/Phishing", "https://en.wikipedia.org",
          "https://www.nou.edu.ng/student-portal", "https://www.nou.edu.ng"]:
    a, fa = p(u); b, fb = p(d_only(u))
    flag = "" if round(a,4)==round(b,4) else "   <-- differs"
    print(f"{u:<46} full={a:.4f} dom={b:.4f}  path_len {fa['path_length']}->{fb['path_length']}  url_len {fa['url_length']}->{fb['url_length']}{flag}")
