import pandas as pd
import sqlite3

con = sqlite3.connect('../data/retail.db')
tables = ['dim_customers', 'dim_products', 'dim_date', 'fact_orders', 'fact_order_items']
for t in tables:
    df = pd.read_csv(f'../data/{t}.csv')
    df.to_sql(t, con, if_exists='replace', index=False)
    print(t, 'loaded:', len(df), 'rows')
con.close()
print('done loading into retail.db')