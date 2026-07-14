-- ============================================================
-- RFM (Recency, Frequency, Monetary) scoring per customer
-- Uses window functions (NTILE) to score each dimension 1-5
-- ============================================================

WITH order_revenue AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        SUM(oi.line_total) AS order_value
    FROM fact_orders o
    JOIN fact_order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.order_id, o.customer_id, o.order_date
),

customer_rfm_raw AS (
    SELECT
        customer_id,
        MAX(order_date)                         AS last_order_date,
        CAST(julianday((SELECT MAX(order_date) FROM order_revenue)) 
             - julianday(MAX(order_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT order_id)                AS frequency,
        ROUND(SUM(order_value), 2)              AS monetary
    FROM order_revenue
    GROUP BY customer_id
),

scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- lower recency_days = more recent = better score, so invert with 6 - ntile
        (6 - NTILE(5) OVER (ORDER BY recency_days))   AS r_score,
        NTILE(5) OVER (ORDER BY frequency)            AS f_score,
        NTILE(5) OVER (ORDER BY monetary)             AS m_score
    FROM customer_rfm_raw
)

SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2  THEN 'Lost'
        ELSE 'Needs Attention'
    END AS rfm_segment
FROM scored
ORDER BY rfm_total DESC;
