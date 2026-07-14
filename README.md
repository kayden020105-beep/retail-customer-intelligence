# Retail & E-Commerce Customer Intelligence Platform

An end-to-end analytics pipeline: SQL warehouse → Python ML models → Power BI + Tableau
dashboards → Excel exec workbook. Built to demonstrate the full analyst toolkit on one
coherent business problem: understanding and growing customer value for an online retailer.

Targets: Data Analyst, Business Analyst, Marketing Analyst, Customer Insights Analyst,
Product Analyst, BI Analyst, Data Consultant roles.

## What's inside

```
data/            Generated CSVs + SQLite database (retail.db) + all analysis outputs
sql/             Star-schema DDL and 4 analysis queries (RFM, cohort retention, growth, A/B test)
python/          5 scripts: data generation, segmentation, CLV, churn, A/B test stats
excel/           Retail_Analytics_Workbook.xlsx (live formulas, charts, scenario model)
BI_BUILD_GUIDE.md   Exact DAX measures (Power BI) and calculated fields (Tableau)
```

## How to reproduce this end-to-end

```bash
cd python
pip install numpy pandas scikit-learn xgboost shap matplotlib openpyxl --break-system-packages

python3 01_generate_data.py        # generates 5 CSVs into ../data
# load into SQLite (or point at Snowflake/Postgres using sql/01_schema.sql instead)
python3 -c "
import pandas as pd, sqlite3
con = sqlite3.connect('../data/retail.db')
for t in ['dim_customers','dim_products','dim_date','fact_orders','fact_order_items']:
    pd.read_csv(f'../data/{t}.csv').to_sql(t, con, if_exists='replace', index=False)
"
python3 02_segmentation.py         # K-means RFM segments -> customer_segments.csv
python3 03_clv_prediction.py       # 90-day forward CLV model -> clv_predictions.csv
python3 04_churn_prediction.py     # XGBoost churn model + SHAP -> churn_predictions.csv
python3 05_ab_test_analysis.py     # promo A/B test significance -> ab_test_results.csv

cd ../excel
python3 build_excel_workbook.py    # builds Retail_Analytics_Workbook.xlsx
```

Then follow `BI_BUILD_GUIDE.md` to build the Power BI and Tableau dashboards on top of the
same tables.

## Results summary (what to say in an interview)

| Analysis | Result |
|---|---|
| RFM segmentation (K-means, k=5) | 5 segments from "VIP/Champions" to "Dormant/Lost"; Champions are 23% of customers but ~57% of revenue |
| CLV model (Gradient Boosting) | Predicts 90-day forward spend from first-90-day behavior; R² = 0.18, MAE ≈ $1,870 — realistic for behavioral CLV, not inflated |
| Churn model (XGBoost + SHAP) | AUC-ROC = 0.69 predicting 90-day lapse; SHAP shows early order count and spend are the top drivers |
| A/B test (15% promo) | Conversion lift was **not** statistically significant (p=0.67); AOV actually **fell** significantly (p<0.001) — the discount cost more than it generated. Recommendation: don't roll out this promo as-is |

That last result is deliberately a "the test failed" story — being able to read and act on
a null/negative result is exactly what separates a junior analyst from someone who just
reports whatever number looks good.

## Suggested resume bullets

- Built an end-to-end customer analytics pipeline on a 730K-row e-commerce transaction
  dataset (SQL star schema, Python ML, Power BI + Tableau dashboards) to segment customers
  and predict lifetime value and churn.
- Applied K-means clustering on RFM features to segment 14,000+ customers into 5 tiers;
  identified that the top 23% of customers drove ~57% of total revenue.
- Built a Gradient Boosting CLV model and an XGBoost churn classifier (AUC 0.69) with SHAP
  explainability, surfacing early purchase behavior as the strongest churn predictor.
- Designed and analyzed an A/B test on a promotional discount using two-proportion z-tests
  and Welch's t-tests; found no significant conversion lift and a significant AOV decline,
  preventing an unprofitable promo rollout.
- Built parallel Power BI and Tableau dashboards (DAX time-intelligence measures, cohort
  retention heatmaps) and an Excel scenario model with live formulas for discount/margin
  sensitivity analysis.

## GitHub repo structure suggestion

Rename this folder and push as-is — the `/sql`, `/python`, `/excel`, and root README
structure is already interview-ready. Add screenshots of the Power BI and Tableau
dashboards to the README once built (GitHub renders images inline).
