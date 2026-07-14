-- ============================================================
-- Monthly cohort retention: % of each signup-month cohort that
-- placed an order in each subsequent month-index (0,1,2,...)
-- ============================================================

WITH first_order AS (
    SELECT
        c.customer_id,
        strftime('%Y-%m', c.signup_date) AS cohort_month
    FROM dim_customers c
),

monthly_orders AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS order_month
    FROM fact_orders o
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, strftime('%Y-%m', o.order_date)
),

cohort_activity AS (
    SELECT
        fo.cohort_month,
        mo.order_month,
        -- month index = number of calendar months between cohort month and order month
        (CAST(strftime('%Y', mo.order_month || '-01') AS INTEGER) * 12 +
         CAST(strftime('%m', mo.order_month || '-01') AS INTEGER))
        -
        (CAST(strftime('%Y', fo.cohort_month || '-01') AS INTEGER) * 12 +
         CAST(strftime('%m', fo.cohort_month || '-01') AS INTEGER))    AS month_index,
        mo.customer_id
    FROM first_order fo
    JOIN monthly_orders mo ON mo.customer_id = fo.customer_id
),

cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM first_order
    GROUP BY cohort_month
)

SELECT
    ca.cohort_month,
    ca.month_index,
    COUNT(DISTINCT ca.customer_id)                              AS active_customers,
    cs.cohort_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_customers, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs ON cs.cohort_month = ca.cohort_month
WHERE ca.month_index BETWEEN 0 AND 12
GROUP BY ca.cohort_month, ca.month_index, cs.cohort_customers
ORDER BY ca.cohort_month, ca.month_index;
