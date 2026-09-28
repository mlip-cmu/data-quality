# 03 · Schema in a relational database

**Slides:** *Schema in Relational Databases* · *Data Schema* · *Schema Problems: Uniqueness, data
format, integrity* · *What Happens When New Data Violates Schema?*

`schema.sql` is the schema from the slide (with the missing comma after the `Unit` line
fixed), plus a unique GTIN, a price check, a cross-column check (produce is sold by count or
kg), and a `Deliveries` table with a date dependency. `new_products.csv` is a batch of new
products typed in by store staff.

```sh
uv run load.py             # DuckDB enforces the schema
uv run sqlite_contrast.py  # the same schema in SQLite
```

What to look for in `load.py`:
1. Row by row, the database names the constraint that each bad row breaks. These are the four
   schema problems from the slide: illegal values (`bottle`, `-4.99`, `2025-13-02`), violated
   attribute dependencies (produce sold by the liter, best-before date before the delivery),
   uniqueness (product 101, GTIN of the banana), and referential integrity (suppliers `283`
   and `502` from the slide's CSV do not exist).
2. One multi-row `INSERT` is a transaction: one bad row rejects the whole batch.
3. The usual answer is a quarantine: load the good rows and send the bad rows
   (`out/rejected.csv`) back with a reason.
4. The schema is a low bar. `'75.5'` for a count is silently rounded to 76, and a cucumber with
   unit `kg` is a legal value. These are "wrong and inconsistent data" (see `08`).

`sqlite_contrast.py`: SQLite accepts the text `'twelve'` in an `INT` column and ignores
foreign keys unless you turn them on. Only `STRICT` tables enforce the types. DuckDB and SQLite
also do not enforce `VARCHAR(n)` lengths, so the schema has an explicit `length(GTIN)` check.
