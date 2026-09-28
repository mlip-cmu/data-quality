"""Load a batch of new products into a database that enforces the schema."""

import csv
import re
from pathlib import Path

import duckdb

import inventory_data as d

OUT = Path("out")
OUT.mkdir(exist_ok=True)
COLS = "ID, GTIN, Name, Category, UnitPrice, QuantityInStock, Unit, SupplierID"
INSERT = f"INSERT INTO Products ({COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(Path("schema.sql").read_text())
    supplier_rows = d.suppliers()[["id", "name", "contact_name", "contact_phone"]]  # noqa: F841
    con.execute("INSERT INTO Suppliers SELECT * FROM supplier_rows")
    stock = d.inventory().query("date == date.max() and store_id == 1").set_index("product_id")
    catalog = d.products().assign(qty=lambda p: p.id.map(stock.on_hand_system).round())  # noqa: F841
    con.execute(
        "INSERT INTO Products SELECT id, gtin, name, category, unit_price, qty, unit, "
        "supplier_id FROM catalog"
    )
    return con


def reason(e: duckdb.Error) -> str:
    msg = str(e).splitlines()[0].split(": ", 1)[1]
    if m := re.search(r"with expression CHECK\((.*)\)$", msg):
        msg = f"CHECK {m.group(1)}"
    return msg.replace(" in the referenced table", "")[:80]


def count(con) -> int:
    return con.sql("SELECT count(*) FROM Products").fetchone()[0]


with open("new_products.csv") as f:
    batch = [
        [v if v != "" else None for v in row]
        for row in csv.DictReader(f)
        for row in [list(row.values())]
    ]

print("1. Insert the new rows one by one\n")
con = connect()
accepted, rejected = [], []
for row in batch:
    try:
        con.execute(INSERT, row)
        accepted.append(row)
        print(f"   ok        {row[0]:>4} {row[2]}")
    except (duckdb.ConstraintException, duckdb.ConversionException) as e:
        rejected.append(row + [type(e).__name__, reason(e)])
        print(f"   REJECTED  {row[0]:>4} {row[2] or '(no name)':<20} {reason(e)}")
qty = con.sql("SELECT QuantityInStock FROM Products WHERE ID = 163").fetchone()[0]
print(
    f"\n   Note: row 163 has QuantityInStock '75.5' for a count unit. It was accepted and "
    f"silently stored as {qty}."
)

print("\n2. Insert the whole batch in one statement (a database transaction)\n")
con = connect()
before = count(con)
values = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?)"] * len(batch))
try:
    con.execute(f"INSERT INTO Products ({COLS}) VALUES {values}", [v for r in batch for v in r])
except duckdb.Error as e:
    print(f"   {type(e).__name__}: {reason(e)}")
assert count(con) == before
print(f"   Products before: {before}, after: {count(con)}: all {len(batch)} rows were rejected")

print("\n3. Quarantine: load the good rows, keep the bad rows for a human to fix\n")
with open(OUT / "rejected.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS.split(", ") + ["error", "reason"])
    w.writerows(rejected)
print(f"   {len(accepted)} rows loaded, {len(rejected)} rows written to out/rejected.csv")

print("\n4. Dates and dependencies between attributes (Deliveries)\n")
con = connect()
for row in [
    (1, 101, "2025-06-02", "2025-06-09", 18.0),
    (2, 101, "2025-13-02", "2025-06-09", 18.0),
    (3, 123, "2025-06-02", "2025-05-28", 12.0),
    (4, 999, "2025-06-02", "2025-06-09", 5.0),
]:
    try:
        con.execute("INSERT INTO Deliveries VALUES (?, ?, ?, ?, ?)", row)
        print(f"   ok        {row}")
    except duckdb.Error as e:
        print(f"   REJECTED  {row}  {reason(e)}")

print("\n5. Not every problem is a schema problem")
con.execute("UPDATE Products SET Unit = 'kg' WHERE ID = 102")
print("   Cucumbers (sold by count) set to unit 'kg': accepted, because 'kg' is a legal value")
