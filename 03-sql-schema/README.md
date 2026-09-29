# 03 · Schema in a relational database

Store staff type in new products for the product catalog of a supermarket chain
(`new_products.csv`, [dataset](../inventory-data/)).

**Problem.** Manually entered records can have illegal values (`bottle` as a unit, a negative
price, the date `2025-13-02`), violate dependencies between attributes (a best-before date
before the delivery), reuse a key that already exists, or refer to a supplier that does not
exist. If these records get into the database, every system that uses the data gets them too.

**Idea.** Declare the expected structure as a schema (types, `CHECK` constraints, primary,
unique, and foreign keys) and let the database reject each record that does not match. Load
the good rows and send the bad rows back with a reason (a quarantine), instead of losing the
whole batch.

The schema declares the rules; the database enforces them on each insert (`schema.sql`):

```sql
GTIN VARCHAR(13) NOT NULL UNIQUE CHECK (length(GTIN) = 13),
UnitPrice DECIMAL(10, 2) NOT NULL CHECK (UnitPrice > 0),
Unit VARCHAR(5) NOT NULL CHECK (Unit IN ('count', 'kg', 'liter')),
CHECK (Category <> 'produce' OR Unit IN ('count', 'kg')),   -- a rule across columns
FOREIGN KEY (SupplierID) REFERENCES Suppliers(ID)
```

`load.py` inserts row by row, so one bad row does not stop the batch, and keeps each rejected
row with the reason for a quarantine:

```python
try:
    con.execute(INSERT, row)
    accepted.append(row)
except (duckdb.ConstraintException, duckdb.ConversionException) as e:
    rejected.append(row + [type(e).__name__, reason(e)])
```

## What the code shows

- `schema.sql`: products, suppliers, and deliveries with types, value constraints, a check
  across columns (produce is sold by count or kg), unique GTINs, and foreign keys.
- `load.py`:
  1. Row by row, the database names the constraint that each bad row breaks.
  2. A multi-row `INSERT` is one transaction: one bad row rejects the whole batch.
  3. Quarantine: the good rows are loaded, the bad rows go to `out/rejected.csv` with a reason.
  4. The schema is a low bar: `'75.5'` for a count is silently rounded to 76, and a cucumber
     sold by `kg` is a legal value.
- `sqlite_contrast.py`: the same schema in SQLite accepts the text `'twelve'` in an `INT`
  column and ignores foreign keys unless you turn them on; only `STRICT` tables enforce types.

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics (no server). Here: it
  enforces the schema and reports each violation (`ConstraintException`, `ConversionException`).
- [SQLite](https://sqlite.org), through Python's
  [`sqlite3`](https://docs.python.org/3/library/sqlite3.html) module: the most widely used
  embedded database. Here: a database that enforces less by default.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run load.py             # DuckDB enforces the schema
uv run sqlite_contrast.py  # the same schema in SQLite
```
