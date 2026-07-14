-- ============================================================
-- Retail & E-Commerce Customer Intelligence Platform
-- Star-schema DDL. Written in ANSI SQL, compatible with
-- Snowflake / PostgreSQL (minor type tweaks noted inline).
-- ============================================================

CREATE TABLE dim_customers (
    customer_id         INTEGER PRIMARY KEY,
    signup_date          DATE,
    country               VARCHAR(50),
    gender                VARCHAR(10),
    age                   INTEGER,
    acquisition_channel   VARCHAR(50),
    ab_test_group         VARCHAR(20)          -- 'control' / 'treatment'
);

CREATE TABLE dim_products (
    product_id     INTEGER PRIMARY KEY,
    product_name   VARCHAR(100),
    category       VARCHAR(50),
    sub_category   VARCHAR(50),
    unit_cost      NUMERIC(10,2),
    unit_price     NUMERIC(10,2)
);

CREATE TABLE dim_date (
    date           DATE PRIMARY KEY,
    day            INTEGER,
    month          INTEGER,
    month_name     VARCHAR(10),
    quarter        INTEGER,
    year           INTEGER,
    day_of_week    VARCHAR(15),
    is_weekend     BOOLEAN
);

CREATE TABLE fact_orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER REFERENCES dim_customers(customer_id),
    order_date      DATE REFERENCES dim_date(date),
    order_status    VARCHAR(20),        -- Completed / Cancelled / Returned
    channel         VARCHAR(20),        -- Web / Mobile App
    ab_test_group   VARCHAR(20),
    in_ab_test      BOOLEAN,
    discount_pct    NUMERIC(5,2)
);

CREATE TABLE fact_order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER REFERENCES fact_orders(order_id),
    product_id      INTEGER REFERENCES dim_products(product_id),
    quantity        INTEGER,
    unit_price      NUMERIC(10,2),
    line_total      NUMERIC(10,2)
);

-- Helpful indexes for a warehouse this size
CREATE INDEX idx_orders_customer ON fact_orders(customer_id);
CREATE INDEX idx_orders_date ON fact_orders(order_date);
CREATE INDEX idx_items_order ON fact_order_items(order_id);
CREATE INDEX idx_items_product ON fact_order_items(product_id);
