"""
01_generate_data.py
Generates a realistic synthetic e-commerce dataset:
  dim_customers, dim_products, dim_date, fact_orders, fact_order_items
Also embeds a promo A/B test (control vs treatment) inside fact_orders.

Run: python3 01_generate_data.py
Output: CSVs in ../data/
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

OUT = "../data/"

N_CUSTOMERS = 15000
N_PRODUCTS = 400
N_ORDERS = 260000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2026, 6, 30)
DAYS = (END_DATE - START_DATE).days

# ---------- dim_customers ----------
countries = np.random.choice(
    ["India", "USA", "UK", "UAE", "Singapore", "Australia", "Canada"],
    N_CUSTOMERS, p=[0.35, 0.25, 0.12, 0.08, 0.08, 0.07, 0.05]
)
channels = np.random.choice(
    ["Organic Search", "Paid Social", "Email", "Referral", "Direct", "Affiliate"],
    N_CUSTOMERS, p=[0.28, 0.22, 0.15, 0.12, 0.15, 0.08]
)
# signup skewed toward earlier dates (more tenured customers) using beta distribution
signup_offset = (np.random.beta(2, 3, N_CUSTOMERS) * DAYS).astype(int)
signup_dates = [START_DATE + timedelta(days=int(d)) for d in signup_offset]

customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUSTOMERS + 1),
    "signup_date": signup_dates,
    "country": countries,
    "gender": np.random.choice(["M", "F", "Other"], N_CUSTOMERS, p=[0.48, 0.48, 0.04]),
    "age": np.random.randint(18, 65, N_CUSTOMERS),
    "acquisition_channel": channels,
    # random assignment to A/B test cohort (only relevant for orders placed during test window)
    "ab_test_group": np.random.choice(["control", "treatment"], N_CUSTOMERS, p=[0.5, 0.5]),
})

# Latent, persistent customer heterogeneity: some customers are simply higher-value
# (buy more often AND spend more per order) than others. This is what makes CLV / churn
# models learnable -- without it, future spend is pure noise relative to past behavior.
customers["purchase_propensity"] = np.random.gamma(shape=1.3, scale=1.8, size=N_CUSTOMERS)
customers["spend_multiplier"] = np.random.lognormal(mean=0.0, sigma=0.55, size=N_CUSTOMERS)
customers.to_csv(OUT + "dim_customers.csv", index=False)

# ---------- dim_products ----------
categories = {
    "Electronics": ["Headphones", "Smartwatch", "Charger", "Speaker", "Laptop Bag"],
    "Apparel": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Cap"],
    "Home & Kitchen": ["Cookware", "Bedding", "Lamp", "Storage Box", "Blender"],
    "Beauty": ["Skincare Set", "Perfume", "Hair Dryer", "Makeup Kit", "Trimmer"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Running Shoes", "Cycling Gear", "Water Bottle"],
    "Books & Stationery": ["Notebook", "Planner", "Pen Set", "Novel", "Backpack"],
}
prod_rows = []
pid = 1
for cat, subs in categories.items():
    for _ in range(N_PRODUCTS // len(categories)):
        sub = np.random.choice(subs)
        unit_cost = round(np.random.uniform(5, 150), 2)
        margin = np.random.uniform(1.4, 3.2)
        prod_rows.append({
            "product_id": pid,
            "product_name": f"{sub} {pid}",
            "category": cat,
            "sub_category": sub,
            "unit_cost": unit_cost,
            "unit_price": round(unit_cost * margin, 2),
        })
        pid += 1
products = pd.DataFrame(prod_rows)
products.to_csv(OUT + "dim_products.csv", index=False)

# ---------- fact_orders ----------
# Controlled growth trend: steady ~3.5%/month compounding growth in order volume,
# with a mild plateau in the final 2 months (S-curve realism) + weekly seasonality.
day_index = np.arange(DAYS + 1)
month_index = day_index / 30.4
growth_weight = 1.03 ** month_index
growth_weight[-45:] *= np.linspace(1.0, 0.85, 45)  # plateau/cool-off near the end
dow = np.array([(START_DATE + timedelta(days=int(d))).weekday() for d in day_index])
weekly_seasonality = np.where(dow >= 5, 1.25, 1.0)  # weekend bump
day_weights = growth_weight * weekly_seasonality
day_weights = day_weights / day_weights.sum()

order_offset = np.random.choice(day_index, size=N_ORDERS, p=day_weights)
order_dates = np.array([START_DATE + timedelta(days=int(d)) for d in order_offset])

cust_lookup = customers.set_index("customer_id")
order_weights = (customers["purchase_propensity"] / customers["purchase_propensity"].sum()).values
order_customers = np.random.choice(customers["customer_id"], N_ORDERS, p=order_weights)

AB_TEST_START = datetime(2026, 1, 1)
AB_TEST_END = datetime(2026, 3, 31)

order_status = np.random.choice(
    ["Completed", "Cancelled", "Returned"], N_ORDERS, p=[0.88, 0.07, 0.05]
)
order_channel = np.random.choice(
    ["Web", "Mobile App"], N_ORDERS, p=[0.55, 0.45]
)

orders = pd.DataFrame({
    "order_id": np.arange(1, N_ORDERS + 1),
    "customer_id": order_customers,
    "order_date": order_dates,
    "order_status": order_status,
    "channel": order_channel,
})
orders["ab_test_group"] = orders["customer_id"].map(cust_lookup["ab_test_group"])
in_test_window = (orders["order_date"] >= AB_TEST_START) & (orders["order_date"] <= AB_TEST_END)
orders["in_ab_test"] = in_test_window

# Treatment group gets a 15% promo during the test window -> lifts conversion rate & AOV slightly
orders["discount_pct"] = 0.0
treat_mask = in_test_window & (orders["ab_test_group"] == "treatment")
orders.loc[treat_mask, "discount_pct"] = 0.15

orders.to_csv(OUT + "fact_orders.csv", index=False)

# ---------- fact_order_items ----------
# each order gets 1-5 line items; treatment group during test window has a higher avg basket size
items_per_order = np.random.poisson(1.8, N_ORDERS) + 1
items_per_order = np.clip(items_per_order, 1, 6)
uplift_mask = treat_mask.values
items_per_order = items_per_order + np.where(uplift_mask, np.random.binomial(1, 0.35, N_ORDERS), 0)

order_id_repeated = np.repeat(orders["order_id"].values, items_per_order)
discount_repeated = np.repeat(orders["discount_pct"].values, items_per_order)
n_items = len(order_id_repeated)

item_products = np.random.choice(products["product_id"], n_items)
prod_lookup = products.set_index("product_id")
unit_price = prod_lookup.loc[item_products, "unit_price"].values
quantity = np.random.randint(1, 4, n_items)

# apply each item's customer-level spend multiplier (higher-value customers buy pricier baskets)
customer_repeated = np.repeat(orders["customer_id"].values, items_per_order)
spend_mult_repeated = cust_lookup.loc[customer_repeated, "spend_multiplier"].values
line_total = np.round(unit_price * quantity * spend_mult_repeated * (1 - discount_repeated), 2)

order_items = pd.DataFrame({
    "order_item_id": np.arange(1, n_items + 1),
    "order_id": order_id_repeated,
    "product_id": item_products,
    "quantity": quantity,
    "unit_price": unit_price,
    "line_total": line_total,
})
order_items.to_csv(OUT + "fact_order_items.csv", index=False)

# ---------- dim_date ----------
dates = pd.date_range(START_DATE, END_DATE, freq="D")
dim_date = pd.DataFrame({
    "date": dates,
    "day": dates.day,
    "month": dates.month,
    "month_name": dates.strftime("%b"),
    "quarter": dates.quarter,
    "year": dates.year,
    "day_of_week": dates.strftime("%A"),
    "is_weekend": dates.dayofweek >= 5,
})
dim_date.to_csv(OUT + "dim_date.csv", index=False)

print(f"customers: {len(customers):,}")
print(f"products: {len(products):,}")
print(f"orders: {len(orders):,}")
print(f"order_items: {len(order_items):,}")
print(f"dim_date: {len(dim_date):,}")
print("A/B test orders in window:", in_test_window.sum())
