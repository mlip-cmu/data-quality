"""Data quality rules: invariants within and across tables, written as SQL."""

from dataclasses import dataclass

import duckdb
import pandas as pd

import inventory_data as d
from inventory_data.master import gtin_is_valid


@dataclass
class Rule:
    name: str
    kind: str
    action: str
    sql: str  # returns one column `row_id` with the rows that break the rule
    table: str


RULES = [
    Rule(
        "ZIP code and city correspond",
        "integrity constraint",
        "flag",
        """
        SELECT s.id AS row_id FROM stores s
        LEFT JOIN zip_codes z ON lpad(s.zip::VARCHAR, 5, '0') = z.zip
        WHERE z.city IS DISTINCT FROM s.city""",
        "stores",
    ),
    Rule(
        "Supplier ID refers to an existing supplier",
        "referential integrity",
        "reject",
        """
        SELECT p.id AS row_id FROM products p ANTI JOIN suppliers s ON p.supplier_id = s.id""",
        "products",
    ),
    Rule(
        "GTIN is unique",
        "uniqueness",
        "reject",
        """
        SELECT id AS row_id FROM products QUALIFY count(*) OVER (PARTITION BY gtin) > 1
        AND row_number() OVER (PARTITION BY gtin ORDER BY id) > 1""",
        "products",
    ),
    Rule(
        "GTIN has a valid check digit",
        "format",
        "reject",
        """
        SELECT id AS row_id FROM products WHERE NOT gtin_valid(lpad(gtin::VARCHAR, 13, '0'))""",
        "products",
    ),
    Rule(
        "Unit fits the category",
        "conditional constraint",
        "reject",
        """
        SELECT id AS row_id FROM products WHERE NOT CASE category
            WHEN 'produce' THEN unit IN ('count', 'kg')
            WHEN 'meat' THEN unit IN ('count', 'kg') WHEN 'seafood' THEN unit IN ('count', 'kg')
            WHEN 'refill' THEN unit = 'liter' ELSE unit = 'count' END""",
        "products",
    ),
    Rule(
        "Bigger pack of the same product is not cheaper",
        "denial constraint",
        "flag",
        """
        SELECT big.id AS row_id FROM products small JOIN products big
        ON small.family = big.family AND small.size < big.size
        WHERE try_cast(big.unit_price AS DOUBLE) < try_cast(small.unit_price AS DOUBLE)""",
        "products",
    ),
    Rule(
        "Placeholder values are missing values",
        "missing value",
        "repair",
        """
        SELECT id AS row_id FROM suppliers WHERE contact_phone IN ('999-9999999', '000-0000000')
        UNION ALL SELECT id FROM products WHERE shelf_life_days IN (0, 999, 9999)""",
        "suppliers|products",
    ),
    Rule(
        "Delivery: product name matches the product ID",
        "integrity constraint",
        "flag",
        """
        SELECT dl.delivery_id AS row_id FROM deliveries dl JOIN catalog c ON dl.product_id = c.id
        WHERE dl.product_name <> c.name""",
        "deliveries",
    ),
    Rule(
        "Delivery: no second identical delivery",
        "uniqueness",
        "flag",
        """
        SELECT delivery_id AS row_id FROM deliveries
        QUALIFY row_number() OVER (PARTITION BY store_id, product_id, delivery_date, quantity
                                   ORDER BY entered_at) > 1""",
        "deliveries",
    ),
    Rule(
        "Delivery date is a real date in the data period",
        "illegal value",
        "reject",
        """
        SELECT delivery_id AS row_id FROM deliveries
        WHERE delivery_date NOT BETWEEN DATE '2024-01-01' AND DATE '2025-12-31'""",
        "deliveries",
    ),
    Rule(
        "Cannot sell more than the stock plus the deliveries",
        "cross-source invariant",
        "flag",
        """
        WITH arrived AS (SELECT delivery_date AS date, store_id, product_id, sum(quantity) AS qty
                         FROM deliveries WHERE unit IN ('count', 'kg', 'liter')
                         GROUP BY ALL),
             stock AS (SELECT date, store_id, product_id,
                              lag(on_hand_system) OVER (PARTITION BY store_id, product_id
                                                        ORDER BY date) AS before FROM inventory)
        SELECT s.date::DATE || '|' || s.store_id || '|' || s.product_id AS row_id
        FROM sales s JOIN stock USING (date, store_id, product_id)
        LEFT JOIN arrived a USING (date, store_id, product_id)
        WHERE s.quantity > stock.before + coalesce(a.qty, 0) + 1""",
        "sales",
    ),
    Rule(
        "POS price equals the catalog price (without promotion)",
        "consistency",
        "flag",
        """
        SELECT s.date::DATE || '|' || s.store_id || '|' || s.product_id AS row_id
        FROM sales s JOIN catalog c ON s.product_id = c.id
        WHERE NOT s.promo AND abs(s.unit_price - c.unit_price) > 0.005""",
        "sales",
    ),
]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.create_function("gtin_valid", gtin_is_valid, ["VARCHAR"], "BOOLEAN")
    for name, df in {
        "products": d.products(dirty=True),
        "suppliers": d.suppliers(dirty=True),
        "stores": d.stores(dirty=True),
        "deliveries": d.deliveries(dirty=True),
        "sales": d.sales(dirty=True),
        "inventory": d.inventory(),
        "catalog": d.products(),
        "zip_codes": d.zip_codes(),
    }.items():
        con.register(name, df)
    return con


def check_all() -> pd.DataFrame:
    con = connect()
    errors = d.errors()
    rows = []
    for rule in RULES:
        found = set(con.sql(rule.sql).df().row_id.astype(str))
        truth = errors[errors.table.isin(rule.table.split("|"))]
        hits = len(found & set(truth.row_id))
        rows.append((rule.name, rule.kind, rule.action, len(found), hits))
    return pd.DataFrame(
        rows, columns=["rule", "kind", "action", "violations", "of them injected errors"]
    )


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    print(check_all().to_string(index=False))
    print("\nWhy does the cross-source invariant fire? (compare with the injected errors)")
    con = connect()
    found = set(con.sql(RULES[10].sql).df().row_id)
    errors = d.errors().query("table == 'deliveries'")
    clean = d.deliveries().set_index("delivery_id")
    clean["key"] = (
        clean.delivery_date.dt.date.astype(str)
        + "|"
        + clean.store_id.astype(str)
        + "|"
        + clean.product_id.astype(str)
    )
    ids = errors.row_id.astype(int)
    by_kind = errors.assign(key=clean.key.reindex(ids).to_numpy()).dropna(subset=["key"])
    missing = set(by_kind.query("error_type == 'missing_record'").key)
    other = set(by_kind.query("error_type != 'missing_record'").key) - missing
    print(f"  {len(found & missing):>4} days with a forgotten delivery record")
    print(f"  {len(found & other):>4} days with a delivery entered wrongly (unit, date, product)")
    print(f"  {len(found - missing - other):>4} other days (errors in the manual stock counts)")
