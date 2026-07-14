"""
03_clv_prediction.py
Predicts 90-day forward customer spend (CLV proxy) using features
built from the customer's first 90 days of history — a standard
"early behavior predicts future value" CLV framing.

Model: Gradient Boosting Regressor (scikit-learn)
Output: ../data/clv_predictions.csv, feature importance chart
"""
import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
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

# ----- Build features from first-90-day window, label = next-90-day spend -----
first_window = orders[orders["days_since_signup"].between(0, 90)]
next_window = orders[orders["days_since_signup"].between(91, 180)]

feat = first_window.groupby("customer_id").agg(
    orders_first90=("order_id", "count"),
    spend_first90=("order_value", "sum"),
    avg_order_value_first90=("order_value", "mean"),
).reset_index()

label = next_window.groupby("customer_id")["order_value"].sum().rename("spend_next90").reset_index()

data = feat.merge(customers[["customer_id", "age", "acquisition_channel", "country"]], on="customer_id")
data = data.merge(label, on="customer_id", how="left")
data["spend_next90"] = data["spend_next90"].fillna(0)

# Only keep customers who had enough tenure to observe the next-90-day window
cutoff_date = customers["signup_date"].max() - pd.Timedelta(days=181)
eligible_customers = customers[customers["signup_date"] <= cutoff_date]["customer_id"]
data = data[data["customer_id"].isin(eligible_customers)]

data = pd.get_dummies(data, columns=["acquisition_channel", "country"], drop_first=True)

X = data.drop(columns=["customer_id", "spend_next90"])
y = data["spend_next90"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)
model.fit(X_train, y_train)

pred = model.predict(X_test)
mae = mean_absolute_error(y_test, pred)
r2 = r2_score(y_test, pred)
print(f"MAE: {mae:.2f}  |  R2: {r2:.3f}")

# Feature importance chart
importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=True)
plt.figure(figsize=(7, 5))
importance.tail(10).plot(kind="barh")
plt.title("CLV Model — Top 10 Feature Importances")
plt.tight_layout()
plt.savefig("../data/clv_feature_importance.png", dpi=120)
plt.close()

# Score ALL eligible customers and export
data["predicted_clv_90d"] = model.predict(X).round(2)
data[["customer_id", "spend_first90", "predicted_clv_90d"]].to_csv("../data/clv_predictions.csv", index=False)

with open("../data/clv_model_metrics.txt", "w") as f:
    f.write(f"Gradient Boosting Regressor — 90-day forward CLV prediction\n")
    f.write(f"Train rows: {len(X_train)}, Test rows: {len(X_test)}\n")
    f.write(f"MAE: {mae:.2f}\nR2: {r2:.3f}\n")

print("Saved clv_predictions.csv, clv_feature_importance.png, clv_model_metrics.txt")
