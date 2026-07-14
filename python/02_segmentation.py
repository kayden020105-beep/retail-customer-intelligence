"""
02_segmentation.py
K-means customer segmentation on RFM features (standardized).
Outputs: ../data/customer_segments.csv, elbow chart, cluster profile table.
"""
import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("../data/retail.db")
rfm_sql = open("../sql/02_rfm.sql").read()
rfm = pd.read_sql_query(rfm_sql, con)

features = rfm[["recency_days", "frequency", "monetary"]].copy()
# log-transform monetary/frequency to reduce skew before scaling
features["frequency"] = np.log1p(features["frequency"])
features["monetary"] = np.log1p(features["monetary"])

scaler = StandardScaler()
X = scaler.fit_transform(features)

# Elbow method to justify k
inertias = []
K_range = range(2, 9)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)

plt.figure(figsize=(6, 4))
plt.plot(list(K_range), inertias, marker="o")
plt.xlabel("k (clusters)")
plt.ylabel("Inertia")
plt.title("Elbow Method for Optimal k")
plt.tight_layout()
plt.savefig("../data/elbow_chart.png", dpi=120)
plt.close()

# Fit final model with k=5 (chosen from elbow + business interpretability)
K_FINAL = 5
km_final = KMeans(n_clusters=K_FINAL, random_state=42, n_init=10)
rfm["cluster"] = km_final.fit_predict(X)

# Profile each cluster and assign a business-friendly label based on RFM means
profile = rfm.groupby("cluster")[["recency_days", "frequency", "monetary"]].mean().round(1)
profile["customers"] = rfm.groupby("cluster").size()
profile = profile.sort_values("monetary", ascending=False)
print(profile)

label_order = ["VIP / Champions", "Loyal Regulars", "Promising", "At Risk", "Dormant / Lost"]
cluster_rank = profile.index.tolist()
label_map = dict(zip(cluster_rank, label_order))
rfm["segment_label"] = rfm["cluster"].map(label_map)

rfm.to_csv("../data/customer_segments.csv", index=False)
profile.to_csv("../data/segment_profile.csv")
print("\nSaved customer_segments.csv and segment_profile.csv")
