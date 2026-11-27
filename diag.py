
import joblib, numpy as np, pandas as pd
from train import extract_features, FEATURES
M = joblib.load("artifacts/model_rf.joblib")
classes = list(M.classes_); pi = classes.index(1)

u = "https://www.paypal.com/signin"
f = extract_features(u); v = np.array([f[k] for k in FEATURES], dtype=float)
print("vector:", dict(zip(FEATURES, v)))
print("p_phish base:", M.predict_proba([v])[0][pi])

# what does the training data say about each feature, by class?
df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", usecols=["URL","label"], low_memory=False).drop_duplicates(subset=["URL"])
rows, ys = [], []
for url, lab in zip(df["URL"].values, df["label"].values):
    ft = extract_features(url)
    if ft: rows.append([ft[k] for k in FEATURES]); ys.append(1-int(lab))
A = pd.DataFrame(rows, columns=FEATURES); A["y"] = ys
print("\nclass medians:")
print(A.groupby("y")[["url_length","hostname_length","path_length","query_length","hostname_depth",
                      "subdomain_count","hyphen_count","digit_ratio","suspicious_token_count",
                      "suspicious_tld","is_https","encoded_char_count","brand_in_subdomain"]].median().T)
print("\nis_https share by class:", A.groupby("y")["is_https"].mean().to_dict())

# single-feature counterfactuals on the paypal vector
print("\nppaypal sensitivity (each feature set to the legit-class median):")
leg = A[A.y==0][FEATURES].median().values
for i, name in enumerate(FEATURES):
    w = v.copy(); w[i] = leg[i]
    print(f"  {name:24s} -> p={M.predict_proba([w])[0][pi]*100:6.2f}%")
