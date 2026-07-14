"""
04_churn_prediction.py
Predicts whether a customer will churn (no order in the 90 days
following their observation window), using XGBoost + SHAP for
interpretability.

Churn label: customer had >=1 order in days 0-180 since signup,
but 0 orders in days 181-270 (defines an "active-then-lapsed" cohort).
"""
import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("../data/retail.db")
orders = pd.read_sql_query("SELECT * FROM fact_orders WHERE order_status='Completed'", con,
                            parse_dates=["order_date"])
items = pd.read_sql_query("SELECT * FROM fact_order_items", con)
customers = pd.read_sql_query("SELECT * FROM dim_customers", con, parse_dates=["signup_date"])

order_val = items.groupby("order_id")["line_total"].sum().rename("order_value")
orders = orders.join(order_val, on="order_id")
orders = orders.merge(customers[["customer_id", "signup_date"]], on="customer_id")
orders["days_since_signup"] = (orders["order_date"] - orders["signup_date"]).dt.days

# Only customers with enough tenure to observe both windows
cutoff_date = customers["signup_date"].max() - pd.Timedelta(days=271)
eligible = customers[customers["signup_date"] <= cutoff_date].copy()

window1 = orders[orders["days_since_signup"].between(0, 180)]
window2 = orders[orders["days_since_signup"].between(181, 270)]

feat = window1.groupby("customer_id").agg(
    orders_0_180=("order_id", "count"),
    spend_0_180=("order_value", "sum"),
    avg_order_value=("order_value", "mean"),
    channel_web_share=("channel", lambda s: (s == "Web").mean()),
).reset_index()

churned_flag = window2.groupby("customer_id").size().rename("orders_181_270")

data = eligible[["customer_id", "age", "acquisition_channel", "country"]].merge(feat, on="customer_id", how="left")
data = data.merge(churned_flag, on="customer_id", how="left")
data["orders_0_180"] = data["orders_0_180"].fillna(0)
data["spend_0_180"] = data["spend_0_180"].fillna(0)
data["avg_order_value"] = data["avg_order_value"].fillna(0)
data["channel_web_share"] = data["channel_web_share"].fillna(0)
data["orders_181_270"] = data["orders_181_270"].fillna(0)

# Only model customers who were active in window 1 (churn is meaningless for never-active customers)
data = data[data["orders_0_180"] > 0].copy()
data["churned"] = (data["orders_181_270"] == 0).astype(int)

print("Churn rate in eligible active cohort:", round(data["churned"].mean(), 3))

data_enc = pd.get_dummies(data, columns=["acquisition_channel", "country"], drop_first=True)
X = data_enc.drop(columns=["customer_id", "orders_181_270", "churned"])
y = data_enc["churned"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# handle class imbalance
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

model = xgb.XGBClassifier(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    scale_pos_weight=scale_pos_weight, eval_metric="auc", random_state=42
)
model.fit(X_train, y_train)

pred_proba = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, pred_proba)
print(f"Test AUC-ROC: {auc:.3f}")
print(classification_report(y_test, (pred_proba > 0.5).astype(int)))

# SHAP explainability
explainer = shap.TreeExplainer(model)
shap_values = explainer(X_test)

plt.figure()
shap.summary_plot(shap_values, X_test, show=False, max_display=10)
plt.tight_layout()
plt.savefig("../data/churn_shap_summary.png", dpi=120, bbox_inches="tight")
plt.close()

# Score all eligible active customers and export a risk list
data_enc["churn_probability"] = model.predict_proba(X)[:, 1].round(3)
output = data_enc[["customer_id", "churn_probability"]].merge(
    data[["customer_id", "orders_0_180", "spend_0_180"]], on="customer_id"
).sort_values("churn_probability", ascending=False)
output.to_csv("../data/churn_predictions.csv", index=False)

with open("../data/churn_model_metrics.txt", "w") as f:
    f.write(f"XGBoost churn classifier\n")
    f.write(f"Active cohort size: {len(data)}\n")
    f.write(f"Base churn rate: {data['churned'].mean():.3f}\n")
    f.write(f"Test AUC-ROC: {auc:.3f}\n")

print("Saved churn_predictions.csv, churn_shap_summary.png, churn_model_metrics.txt")
