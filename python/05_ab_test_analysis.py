"""
05_ab_test_analysis.py
Statistical significance testing on the promo A/B test embedded in the data:
control vs. treatment (15% discount) during Jan-Mar 2026.

Tests:
  1. Conversion rate (did the customer order at all during the window?) -> two-proportion z-test
  2. Average Order Value -> Welch's t-test
  3. Revenue per customer -> Welch's t-test
  4. Minimum Detectable Effect / power check
"""
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

con = sqlite3.connect("../data/retail.db")

customers = pd.read_sql_query("SELECT customer_id, ab_test_group FROM dim_customers", con)
orders = pd.read_sql_query(
    "SELECT * FROM fact_orders WHERE in_ab_test=1 AND order_status='Completed'", con
)
items = pd.read_sql_query("SELECT * FROM fact_order_items", con)

order_val = items.groupby("order_id")["line_total"].sum().rename("order_value")
orders = orders.join(order_val, on="order_id")

# ---------- 1. Conversion rate ----------
converted = orders.groupby("customer_id").size().reset_index(name="orders_in_window")
merged = customers.merge(converted, on="customer_id", how="left")
merged["orders_in_window"] = merged["orders_in_window"].fillna(0)
merged["converted"] = (merged["orders_in_window"] > 0).astype(int)

conv_summary = merged.groupby("ab_test_group")["converted"].agg(["sum", "count", "mean"])
print("=== Conversion Rate ===")
print(conv_summary)

count = conv_summary["sum"].values
nobs = conv_summary["count"].values
# two-proportion z-test
p_pool = count.sum() / nobs.sum()
se = np.sqrt(p_pool * (1 - p_pool) * (1 / nobs[0] + 1 / nobs[1]))
z = (conv_summary["mean"].iloc[1] - conv_summary["mean"].iloc[0]) / se
p_val_conv = 2 * (1 - stats.norm.cdf(abs(z)))
print(f"z-stat: {z:.3f}, p-value: {p_val_conv:.4f}")

# ---------- 2. Revenue per customer (treat non-orderers as 0 spend) ----------
customer_revenue = orders.groupby("customer_id")["order_value"].sum().reset_index()
rev_merged = customers.merge(customer_revenue, on="customer_id", how="left")
rev_merged["order_value"] = rev_merged["order_value"].fillna(0)

control_rev = rev_merged.loc[rev_merged.ab_test_group == "control", "order_value"]
treat_rev = rev_merged.loc[rev_merged.ab_test_group == "treatment", "order_value"]

t_stat, p_val_rev = stats.ttest_ind(treat_rev, control_rev, equal_var=False)  # Welch's t-test
print("\n=== Revenue per Customer ===")
print(f"Control mean: {control_rev.mean():.2f} | Treatment mean: {treat_rev.mean():.2f}")
print(f"t-stat: {t_stat:.3f}, p-value: {p_val_rev:.4f}")

# ---------- 3. Average Order Value (orders only) ----------
orders_grp = orders.drop(columns=["ab_test_group"]).merge(customers, on="customer_id")
control_aov = orders_grp[orders_grp.ab_test_group == "control"]["order_value"]
treat_aov = orders_grp[orders_grp.ab_test_group == "treatment"]["order_value"]

t_stat_aov, p_val_aov = stats.ttest_ind(treat_aov, control_aov, equal_var=False)
print("\n=== Average Order Value ===")
print(f"Control AOV: {control_aov.mean():.2f} | Treatment AOV: {treat_aov.mean():.2f}")
print(f"t-stat: {t_stat_aov:.3f}, p-value: {p_val_aov:.4f}")

# ---------- 4. Minimum Detectable Effect (for a future test of this size) ----------
baseline_p = conv_summary["mean"].iloc[0]
n_per_group = nobs[0]
# MDE at 80% power, alpha=0.05, two-sided
z_alpha = stats.norm.ppf(0.975)
z_beta = stats.norm.ppf(0.80)
mde = (z_alpha + z_beta) * np.sqrt(2 * baseline_p * (1 - baseline_p) / n_per_group)
print(f"\n=== Power Check ===\nWith n={n_per_group} per group and baseline conversion "
      f"{baseline_p:.1%}, this test could reliably detect an absolute lift of >= {mde:.1%}.")

# ---------- Save summary ----------
summary = pd.DataFrame({
    "metric": ["Conversion Rate", "Revenue per Customer", "Average Order Value"],
    "control": [conv_summary["mean"].iloc[0], control_rev.mean(), control_aov.mean()],
    "treatment": [conv_summary["mean"].iloc[1], treat_rev.mean(), treat_aov.mean()],
    "p_value": [p_val_conv, p_val_rev, p_val_aov],
    "significant_at_0.05": [p_val_conv < 0.05, p_val_rev < 0.05, p_val_aov < 0.05],
})
summary.to_csv("../data/ab_test_results.csv", index=False)
print("\nSaved ab_test_results.csv")
