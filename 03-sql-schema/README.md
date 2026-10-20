# 03 · Schema in a relational database

**Slides:** *Schema in Relational Databases* · *Data Schema* · *Schema Problems: Uniqueness,
data format, integrity* · *What Happens When New Data Violates Schema?*

The supermarket chain keeps its products and suppliers in a relational database
([dataset](../inventory-data/)). Store staff type in new products, and the database loads
them. This folder has the schema (`schema.sql`), a batch of 14 new products typed in by the
staff (`new_products.csv`), and two scripts that load the batch: `load.py` with DuckDB and
`sqlite_contrast.py` with SQLite.

**Problem.** Data entered by hand has typos, wrong units, missing values, and IDs that do not
exist. If the database stores such rows, every system that reads the data later must deal
with them, and many of these systems process them without any error.

**Idea.** Write the expectations about the data down as a schema, and let the database
enforce it when it stores each row. A schema is an explicit interface between the systems
that write the data and those that read it: types, required values (`NOT NULL`), allowed
values (`CHECK`), unique keys (`PRIMARY KEY`, `UNIQUE`), and references to other tables
(`FOREIGN KEY`). Then decide what happens to rows that violate it.

`schema.sql` is the schema from the slide, plus a unique GTIN (the barcode number) of 13
digits, a price check, a check across two columns (produce is sold by count or kg), and a
`Deliveries` table with a date dependency:

```sql
CREATE TABLE Products (
    ID INT PRIMARY KEY,
    GTIN VARCHAR(13) NOT NULL UNIQUE CHECK (length(GTIN) = 13),
    Name VARCHAR(255) NOT NULL,
    Category VARCHAR(50),
    UnitPrice DECIMAL(10, 2) NOT NULL CHECK (UnitPrice > 0),
    QuantityInStock INT NOT NULL CHECK (QuantityInStock >= 0),
    Unit VARCHAR(5) NOT NULL CHECK (Unit IN ('count', 'kg', 'liter')),
    SupplierID INT,
    CHECK (Category <> 'produce' OR Unit IN ('count', 'kg')),
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(ID)
);
```

## What the code shows

`load.py` creates the schema in [DuckDB](https://duckdb.org) and loads the 12 suppliers and
60 products of the dataset. Then:

1. **Insert the rows one by one.** 3 rows are accepted, 11 are rejected, each with the name of
   the broken constraint:
   - illegal attribute values: unit `bottle`, price `-4.99`, no name, a price with a decimal
     comma (`4,99`), a quantity `twelve`, and a GTIN of 12 digits (the leading zero is lost);
   - a violated dependency between attributes: produce sold by the liter (oat milk in the
     category `produce`);
   - uniqueness: product ID 101 and the GTIN of the banana already exist;
   - referential integrity: the suppliers `283` and `502` do not exist.
2. **Insert the whole batch in one statement.** One multi-row `INSERT` is a transaction: the
   conversion error of `4,99` rejects all 14 rows, and the table still has 60 products.
3. **Quarantine.** The 3 good rows are loaded, and the 11 bad rows go to `out/rejected.csv`
   with the error and the reason, for a human to fix.
4. **Dates and dependencies in `Deliveries`.** The date `2025-13-02` does not exist, a
   best-before date before the delivery date breaks the `CHECK`, and product 999 does not
   exist; only the correct delivery is accepted.
5. **The schema is a low bar.** In step 1, the quantity `75.5` for a product sold by count is
   accepted and silently stored as 76. Cucumbers (sold by count) set to unit `kg` are
   accepted, because `kg` is a legal value. Project [08](../08-quality-rules-and-repair/)
   detects such errors with rules.

`sqlite_contrast.py` inserts the tahini row (quantity `twelve`, supplier 999) into the same
schema in SQLite:

6. **Databases enforce schemas differently.**
   - SQLite default: accepted; the quantity is stored as the text `'twelve'`, and the unknown
     supplier 999 is stored too.
   - With `PRAGMA foreign_keys = ON`: rejected (`FOREIGN KEY constraint failed`).
   - With `STRICT` tables and foreign keys: rejected
     (`cannot store TEXT value in INT column Products.QuantityInStock`); only `STRICT` tables
     enforce the types.

   Neither DuckDB nor SQLite enforces the length in `VARCHAR(n)`, so the schema has an
   explicit `length(GTIN) = 13` check.

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics. Here: it enforces
  the schema and reports the broken constraint (`ConstraintException`,
  `ConversionException`).
- [SQLite](https://www.sqlite.org) through Python's
  [`sqlite3`](https://docs.python.org/3/library/sqlite3.html) module: a small embedded SQL
  database. Here: the same schema, with weaker enforcement by default.
- [`inventory_data`](../inventory-data/): the shared dataset of this repository. Here: the
  existing suppliers and products, and the stock of store 1.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run load.py             # DuckDB enforces the schema; writes out/rejected.csv
uv run sqlite_contrast.py  # the same schema in SQLite
```
