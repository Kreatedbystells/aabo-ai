
import json, random, sqlite3, urllib.request
import pandas as pd, joblib, numpy as np
from train import extract_features, FEATURES

M = joblib.load("artifacts/model_rf.joblib")
df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", usecols=["URL","label"], low_memory=False)
df = df.drop_duplicates(subset=["URL"])
df["y"] = 1 - df["label"]          # 1 = phishing
rng = random.Random(42)
idx = rng.sample(range(len(df)), 3000)
X, y = [], []
for i in idx:
    f = extract_features(df["URL"].iloc[i])
    if f is None: continue
    X.append([f[k] for k in FEATURES]); y.append(int(df["y"].iloc[i]))
y = np.array(y)
proba = M.predict_proba(X)
classes = list(M.classes_)
p = proba[:, classes.index(1)]
pred = (p >= 0.5).astype(int)
print("n", len(y), "acc", round((pred==y).mean()*100,2))
print("confusion", int(((pred==0)&(y==0)).sum()), int(((pred==1)&(y==0)).sum()), int(((pred==0)&(y==1)).sum()), int(((pred==1)&(y==1)).sum()))

# what does a plain legit URL look like to the model?
for u in ["https://www.paypal.com/signin", "https://www.google.com", "https://autozone.com",
          "https://github.com/login", "https://www.paypal.com/", "https://paypal.com/signin"]:
    f = extract_features(u)
    v = [f[k] for k in FEATURES]
    pr = M.predict_proba([v])[0][classes.index(1)]
    print(f"{u:42s} p_phish={pr*100:6.2f}%", {k:f[k] for k in ("url_length","path_length","is_https","subdomain_count","hostname_depth")})
