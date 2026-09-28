# 03 · Schema in a relational database

**Slides:** *Schema in Relational Databases* · *Data Schema* · *Schema Problems: Uniqueness,
data format, integrity* · *What Happens When New Data Violates Schema?*

`schema.sql` is the schema from the slide, plus a unique GTIN, a price check, a check across
columns (produce is sold by count or kg), and a `Deliveries` table with a date dependency.
`new_products.csv` is a batch of new products typed in by store staff.

## What this project illustrates

| Point | Where to see it |
|---|---|
| A schema is an explicit, enforced interface | `schema.sql`: types, `NOT NULL`, `CHECK`, `PRIMARY KEY`, `UNIQUE`, `FOREIGN KEY`. |
| Illegal attribute values | `load.py`, step 1: `bottle`, `-4.99`, and `2025-13-02` are rejected with the name of the broken constraint. |
| Violated attribute dependencies | `load.py`, step 1: produce sold by the liter; a best-before date before the delivery date. |
| Uniqueness | `load.py`, step 1: product ID 101 and the GTIN of the banana already exist. |
| Referential integrity | `load.py`, step 1: suppliers `283` and `502` do not exist. |
| What happens when new data violates the schema | `load.py`, step 2: one multi-row `INSERT` is a transaction, so one bad row rejects the whole batch. Step 3: the good rows are loaded and the bad rows go to a quarantine (`out/rejected.csv`) with a reason. |
| The schema is a low bar | `load.py`, step 4: `'75.5'` for a count is silently rounded to 76; a cucumber with unit `kg` is a legal value (see `08` for such errors). |
| Databases enforce schemas differently | `sqlite_contrast.py`: SQLite accepts the text `'twelve'` in an `INT` column and ignores foreign keys unless you turn them on; only `STRICT` tables enforce the types. Neither database enforces `VARCHAR(n)`, so the schema has an explicit `length(GTIN)` check. |

## Run

```sh
uv run load.py             # DuckDB enforces the schema
uv run sqlite_contrast.py  # the same schema in SQLite
```
