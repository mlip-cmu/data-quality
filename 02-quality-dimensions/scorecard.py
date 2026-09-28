"""Goodness-of-data scorecard: one score per data source and quality dimension."""

import duckdb
import pandas as pd

import inventory_data as d

d.ensure()
con = duckdb.connect()
for kind, name in [("dirty", "products.csv"), ("dirty", "suppliers.csv"), ("dirty", "stores.csv"),
                   ("dirty", "deliveries.parquet"), ("dirty", "sales.parquet"),
                   ("dirty", "stock_counts.parquet"), ("dirty", "pos_events.parquet"),
                   ("clean", "stock_audit.parquet"), ("clean", "zip_codes.parquet"),
                   ("clean", "products.parquet"), ("clean", "truth.parquet"),
                   ("clean", "oos_reports.parquet"), ("clean", "weather.parquet")]:
    table, ext = name.split(".")
    reader = "read_csv" if ext == "csv" else "read_parquet"
    view = table if kind == "dirty" or table not in ("products",) else "catalog"
    con.sql(f"CREATE VIEW {view} AS SELECT * FROM {reader}('{d.path(kind, name)}')")

# (source, origin, dimension, check, SQL returning the share of good records)
CHECKS = [
    ("product master", "manual entry", "validity", "unit in (count, kg, liter)",
     "SELECT avg((unit IN ('count','kg','liter'))::int) FROM products"),
    ("product master", "manual entry", "validity", "price is a positive number",
     "SELECT avg(coalesce(try_cast(unit_price AS DOUBLE) > 0, false)::int) FROM products"),
    ("product master", "manual entry", "completeness", "name and category present",
     "SELECT avg((name IS NOT NULL AND category IS NOT NULL)::int) FROM products"),
    ("product master", "manual entry", "uniqueness", "product id is unique",
     "SELECT count(DISTINCT id) / count(*) FROM products"),
    ("suppliers", "manual entry", "validity", "phone looks like 412-555-0101",
     r"SELECT avg(regexp_full_match(contact_phone, '\d{3}-555-\d{4}')::int) FROM suppliers"),
    ("stores", "manual entry", "consistency", "city matches the ZIP code",
     "SELECT avg((s.city = z.city)::int) FROM stores s LEFT JOIN zip_codes z "
     "ON lpad(s.zip::VARCHAR, 5, '0') = z.zip"),
    ("deliveries", "manual entry", "uniqueness", "no second identical delivery",
     "SELECT 1 - (count(*) - (SELECT count(*) FROM (SELECT DISTINCT store_id, product_id, "
     "supplier_id, delivery_date, quantity FROM deliveries))) / count(*) FROM deliveries"),
    ("deliveries", "manual entry", "consistency", "product name matches the product id",
     "SELECT avg((dl.product_name = c.name)::int) FROM deliveries dl "
     "JOIN catalog c ON dl.product_id = c.id"),
    ("deliveries", "manual entry", "validity", "unit spelled correctly",
     "SELECT avg((unit IN ('count','kg','liter'))::int) FROM deliveries"),
    ("deliveries", "manual entry", "timeliness", "entered within 24 h of receipt",
     "SELECT avg((entered_at - received_at <= INTERVAL 24 HOUR)::int) FROM deliveries"),
    ("stock counts", "manual entry", "accuracy", "count within 5 % of the audit",
     "SELECT avg((abs(c.counted_qty - a.audited_qty) <= 0.05 * a.audited_qty + 0.5)::int) "
     "FROM stock_counts c JOIN stock_audit a USING (date, store_id, product_id)"),
    ("POS sales", "IT system", "completeness", "every open store reported every day",
     "SELECT count(DISTINCT (date, store_id)) / (SELECT count(DISTINCT date) * "
     "count(DISTINCT store_id) FROM sales) FROM sales"),
    ("POS sales", "IT system", "uniqueness", "one row per store, product, and day",
     "SELECT count(DISTINCT (date, store_id, product_id)) / count(*) FROM sales"),
    ("POS sales", "IT system", "consistency", "regular price equals the catalog price",
     "SELECT avg((abs(s.unit_price - c.unit_price) < 0.005)::int) FROM sales s "
     "JOIN catalog c ON s.product_id = c.id WHERE NOT s.promo"),
    ("POS events", "event stream", "uniqueness", "event id is unique",
     "SELECT count(DISTINCT event_id) / count(*) FROM pos_events"),
    ("POS events", "event stream", "validity", "event time is not after its arrival",
     "SELECT avg((event_time <= ingested_at)::int) FROM pos_events"),
    ("POS events", "event stream", "timeliness", "arrives in order (< 60 s late)",
     "SELECT avg((ingested_at - event_time < INTERVAL 60 SECOND)::int) FROM pos_events"),
    ("weather API", "external", "completeness", "one reading per station and day",
     "SELECT count(*) / (SELECT count(DISTINCT date) * count(DISTINCT station) FROM weather) "
     "FROM weather WHERE temp_c IS NOT NULL"),
    ("weather API", "external", "validity", "temperature between -40 and 45 °C",
     "SELECT avg((temp_c BETWEEN -40 AND 45)::int) FROM weather"),
    ("out-of-stock app", "crowdsourced", "accuracy", "report matches a real stock-out",
     "SELECT avg((t.lost > 0)::int) FROM oos_reports r JOIN truth t ON "
     "t.store_id = r.store_id AND t.product_id = r.product_id AND t.date = r.reported_at::DATE"),
    ("out-of-stock app", "crowdsourced", "completeness", "stock-out days that were reported",
     "SELECT avg((r.report_id IS NOT NULL)::int) FROM truth t LEFT JOIN oos_reports r ON "
     "t.store_id = r.store_id AND t.product_id = r.product_id AND t.date = r.reported_at::DATE "
     "WHERE t.lost > 0"),
]

rows = [(src, origin, dim, check, con.sql(sql).fetchone()[0])
        for src, origin, dim, check, sql in CHECKS]
report = pd.DataFrame(rows, columns=["source", "origin", "dimension", "check", "score"])

pd.set_option("display.width", 120)
print("Checks (share of good records):\n")
print(report.assign(score=report.score.map("{:.2%}".format)).to_string(index=False))
card = report.pivot_table(index=["source", "origin"], columns="dimension", values="score",
                          aggfunc="min", sort=False)
print("\nScorecard (worst check per cell):\n")
print(card.map(lambda v: "" if pd.isna(v) else f"{v:.2%}").to_string())
