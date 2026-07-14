-- ============================================================
-- (A) Month-over-month & YoY revenue growth using window functions
-- ============================================================

WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        ROUND(SUM(oi.line_total), 2)    AS revenue
    FROM fact_orders o
    JOIN fact_order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY strftime('%Y-%m', o.order_date)
)
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month)  AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue, 1) OVER (ORDER BY month))
          / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0), 1) AS mom_growth_pct,
    LAG(revenue, 12) OVER (ORDER BY month) AS revenue_12mo_ago,
    ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (ORDER BY month))
          / NULLIF(LAG(revenue, 12) OVER (ORDER BY month), 0), 1) AS yoy_growth_pct
FROM monthly_revenue
ORDER BY month;


-- ============================================================
-- (B) A/B test readout: control vs. treatment (15% promo)
--     Compares conversion rate, AOV, and revenue per customer
-- ============================================================

WITH test_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.ab_test_group,
        SUM(oi.line_total) AS order_value
    FROM fact_orders o
    JOIN fact_order_items oi ON oi.order_id = o.order_id
    WHERE o.in_ab_test = 1 AND o.order_status = 'Completed'
    GROUP BY o.order_id, o.customer_id, o.ab_test_group
),

group_summary AS (
    SELECT
        ab_test_group,
        COUNT(DISTINCT customer_id)         AS customers_who_ordered,
        COUNT(order_id)                     AS total_orders,
        ROUND(AVG(order_value), 2)          AS avg_order_value,
        ROUND(SUM(order_value), 2)          AS total_revenue
    FROM test_orders
    GROUP BY ab_test_group
)

SELECT * FROM group_summary;
