# Power BI & Tableau Build Guide
## Retail & E-Commerce Customer Intelligence Platform

Both tools connect to the same star-schema tables: `dim_customers`, `dim_products`,
`dim_date`, `fact_orders`, `fact_order_items` (CSV files in `/data`, or point either
tool at `data/retail.db` via ODBC/SQLite connector).

Load all 5 tables, then build these relationships (both tools auto-detect most of these
from the FK-style column names, but verify):
- `fact_orders[customer_id]` → `dim_customers[customer_id]` (many-to-one)
- `fact_orders[order_date]` → `dim_date[date]` (many-to-one)
- `fact_order_items[order_id]` → `fact_orders[order_id]` (many-to-one)
- `fact_order_items[product_id]` → `dim_products[product_id]` (many-to-one)

---

## Power BI — Executive Dashboard

### DAX measures (create these in a new "Measures" table for organization)

```dax
Total Revenue = SUMX(fact_order_items, fact_order_items[quantity] * fact_order_items[unit_price])

Completed Revenue =
CALCULATE([Total Revenue], fact_orders[order_status] = "Completed")

Total Orders = DISTINCTCOUNT(fact_orders[order_id])

Average Order Value = DIVIDE([Completed Revenue], [Total Orders])

Total Customers = DISTINCTCOUNT(dim_customers[customer_id])

Revenue MTD = TOTALMTD([Completed Revenue], dim_date[date])

Revenue Prior Month =
CALCULATE([Completed Revenue], DATEADD(dim_date[date], -1, MONTH))

MoM Growth % =
DIVIDE([Completed Revenue] - [Revenue Prior Month], [Revenue Prior Month])

Revenue Same Month Last Year =
CALCULATE([Completed Revenue], SAMEPERIODLASTYEAR(dim_date[date]))

YoY Growth % =
DIVIDE([Completed Revenue] - [Revenue Same Month Last Year], [Revenue Same Month Last Year])

Repeat Purchase Rate =
VAR CustomersWithMultipleOrders =
    CALCULATE(
        DISTINCTCOUNT(fact_orders[customer_id]),
        FILTER(
            SUMMARIZE(fact_orders, fact_orders[customer_id], "OrderCount", COUNT(fact_orders[order_id])),
            [OrderCount] > 1
        )
    )
RETURN DIVIDE(CustomersWithMultipleOrders, [Total Customers])
```

### What-if parameter (discount sensitivity)
Modeling ribbon → New Parameter → "Discount %", range 0 to 0.30, increment 0.01.
This creates a `Discount %` disconnected table with a `Discount % Value` measure you can
multiply into a custom "Projected Revenue at Discount" measure — same modeling logic as the
Excel Promo_Scenario tab, but interactive with a slicer.

### Dashboard layout (one page)
1. KPI cards across the top: Total Revenue, Total Orders, AOV, Total Customers, YoY Growth %
2. Line chart: Completed Revenue by month (`dim_date[year-month]` on axis)
3. Bar chart: Revenue by `dim_products[category]`
4. Donut/bar: Customers by RFM segment (import `customer_segments.csv` as a 6th table, relate on `customer_id`)
5. Table with drill-through: click a segment → drill into individual customer list
6. Slicer panel: country, acquisition channel, date range

---

## Tableau — Cohort Retention & Segmentation Dashboard

### Calculated fields

```
// Order Revenue (per line item)
[quantity] * [unit_price]

// Days Since Signup (blend fact_orders with dim_customers)
DATEDIFF('day', [signup_date], [order_date])

// Cohort Month
DATETRUNC('month', [signup_date])

// Order Month
DATETRUNC('month', [order_date])

// Month Index (for cohort retention curve)
DATEDIFF('month', [Cohort Month], [Order Month])

// Retention % (table calculation)
// Drop this on a crosstab: rows = Cohort Month, columns = Month Index, measure = COUNTD(customer_id)
// Then add a Quick Table Calculation → Percent of Total, computing along "Cohort Month" (across each row)
```

### Dashboard layout
1. **Cohort retention heatmap**: rows = signup cohort month, columns = month index (0-12),
   color = retention %, label = retention %. Built directly from the "Retention %" table calc above.
2. **Segment scatter**: import `customer_segments.csv` as a data source, plot Recency (x) vs.
   Monetary (y), color by `segment_label`, size by Frequency.
3. **Segment revenue treemap**: `segment_label` as the dimension, `SUM(monetary)` as size.
4. **Filters**: country, acquisition channel, signup date range — applied to all sheets via
   a dashboard-level filter action.

### Publishing note
Tableau Public/Desktop can connect directly to the CSVs in `/data`, or to `retail.db` via
the generic ODBC/SQLite driver if you want it querying live rather than extracting.

---

## Why two BI tools instead of one
Recruiters screening for BI Analyst roles often standardize on one tool or the other —
having both dashboards (built from the *same* underlying model) demonstrates you can adapt
to whichever stack an employer already has, not just that you learned one tool's UI.
