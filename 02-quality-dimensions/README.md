# 02 · Data quality dimensions

**Slides:** *What do we mean by clean data?* · *Data comes from many sources* · *Data is noisy*.
**Paper:** Sambasivan et al., CHI'21 (practitioners need measures of goodness-of-data next to
goodness-of-fit).

The supermarket chain collects data from many sources ([dataset](../inventory-data/)): store
staff type in products, suppliers, deliveries, and stock counts; the checkout (POS, point of
sale) system records sales and a stream of POS events; a weather API reports temperatures; and
customers report empty shelves in an out-of-stock app. This folder has one script,
`scorecard.py`, that scores each source on each quality dimension.

**Problem.** "Clean data" has many meanings. A table can be complete but wrong, or correct but
late. The sources differ in how reliable they are: a system that records each sale
automatically has other errors than a person who types in a stock count at the end of a shift,
or a customer who taps a button in an app. One overall quality number hides where the
problems are.

**Idea.** Measure quality per dimension (accuracy, completeness, uniqueness, consistency,
timeliness, validity) and per source. Each check is a small query that returns the share of
good records. Some dimensions can be measured within one table; accuracy and consistency need
a second, trusted source to compare with (an audit, a reference table, the catalog).

`scorecard.py` lists each check as a tuple (source, origin, dimension, description, SQL). The
SQL runs in [DuckDB](https://duckdb.org) directly on the CSV and Parquet files of the dataset.
Two examples, a validity check within one table and an accuracy check against the audit:

```python
CHECKS = [
    (
        "suppliers",
        "manual entry",
        "validity",
        "phone looks like 412-555-0101",
        r"SELECT avg(regexp_full_match(contact_phone, '\d{3}-555-\d{4}')::int) FROM suppliers",
    ),
    # ... one entry for each source and dimension
    (
        "stock counts",
        "manual entry",
        "accuracy",
        "count within 5 % of the audit",
        "SELECT avg((abs(c.counted_qty - a.audited_qty) <= 0.05 * a.audited_qty + 0.5)::int) "
        "FROM stock_counts c JOIN stock_audit a USING (date, store_id, product_id)",
    ),
]
```

## What the code shows

The script first creates one DuckDB view per file (the dirty copies of the tables that the
staff and systems produce, and clean reference tables), then runs 21 checks and prints the
share of good records for each.

1. **Accuracy.** 96.89 % of the manual stock counts are within 5 % of the independent audit
   re-count. Only 40.85 % of the reports from the out-of-stock app match a real stock-out.
2. **Completeness.** Name and category are present for 98.44 % of the products. 99.95 % of the
   store-days have POS sales (store 6 had a POS outage for three days). The weather API has
   one reading per station and day (100 %). The app users report only 14.09 % of the real
   stock-out days.
3. **Uniqueness.** Product IDs are 98.44 % unique, POS rows (store, product, day) 99.98 %, and
   POS event IDs 99.60 % (terminals re-send events). 99.64 % of the deliveries have no
   identical second copy.
4. **Consistency.** The city matches the ZIP code (with a ZIP reference table) for only
   62.50 % of the stores. The product name in a delivery matches the product ID in 99.51 % of
   the deliveries. The regular POS price equals the catalog price in 99.84 % of the sales.
5. **Timeliness.** 97.07 % of the deliveries are entered within 24 h of receipt. 99.16 % of the
   POS events arrive less than 60 s after they happen.
6. **Validity.** Allowed units in the products (96.88 %), positive prices (95.31 %), the phone
   number format (84.62 %), unit spelling in the deliveries (99.50 %), and temperatures between
   -40 and 45 °C (100 %). Only 93.00 % of the 3,228 POS events have an event time before their
   arrival: the clock of terminal T4 in store 2 is set to UTC, so all its 226 events carry a
   time 4 h after the real one.
7. **Many sources, different reliability.** The scorecard (one row per source, one column per
   dimension, the worst check in each cell) shows the pattern of the slides. The POS sales and
   the weather API score 99.8 % or more everywhere. Manual entry has problems in every
   dimension. The crowdsourced app reports are correct in only about 40 % of the cases and
   miss most stock-outs.
8. **Some checks need a second source.** The accuracy checks join with the audit (`stock_audit`)
   and the true stock-outs (`truth`); the consistency checks join with the ZIP reference table
   (`zip_codes`) and the clean product catalog (`catalog`).

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics. Here: it queries the
  CSV and Parquet files directly (`read_csv`, `read_parquet`), with no loading step and no
  schema, and computes each score.
- [pandas](https://pandas.pydata.org): data frames. Here: the table of checks and the
  scorecard (`pivot_table`).
- [`inventory_data`](../inventory-data/): the shared dataset of this repository. Here: the
  paths of the dirty and clean files (`d.path`).

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run scorecard.py   # print the 21 checks and the scorecard
```
