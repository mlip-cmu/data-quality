# inventory-data: the shared dataset

A synthetic, deterministic dataset of a supermarket chain with 8 stores in Pennsylvania and Ohio
(plus 2 new stores in Florida in the drift scenario), 60 products, and 12 suppliers. An ML model
predicts future sales, and the chain uses the forecasts to decide what to restock, when, and how
many. The data covers two years (2024-01-01 to 2025-12-31).

Because the data is synthetic, the truth is known: the table `truth` has the true demand,
lost sales, waste, shrinkage, and stock; `errors()` lists every error injected into the dirty
tables; and `drift_events()` lists the events of the drift scenario with their dates.

Every other project uses this package as a local path dependency. The data is generated on
first use (about 10 s) and cached as Parquet in `data/`. The same data is committed as CSV, so
you can look at it on GitHub:

- `data/clean/`: the true data (13 tables; the largest, `deliveries.csv`, is 31 MB);
  `data/dirty/`: the same tables with injected errors, plus `errors.csv` (a log of each
  error); `data/drift/`: the drift scenario.
- `data/preview/`: files that are small enough for the table view of GitHub. Small tables
  are complete. Large tables are an extract of store 1 in March 2025 (drift: store 7 from
  2025-08-15 to 2025-09-15, around the POS switch to lb).

The generator uses fixed random seeds, so the files are the same each time. The timestamps in
`pos_events` (`event_time`, `ingested_at`) are whole milliseconds, stored in UTC. The
generator rounds them (the function `_ms` in `src/inventory_data/pos.py`), because the
nanoseconds of a time computed from floating-point seconds can differ between CPUs. With the
rounding, the generated files are the same on every platform.

```sh
uv run inventory-data          # generate (or show) the cached files
uv run inventory-data --force  # regenerate (the CSV files are the same each time)
uv run pytest                  # checks: deterministic, clean data meets all rules, errors logged
```

```python
import inventory_data as d

d.products()  # clean master data (pandas DataFrame)
d.products(dirty=True)  # the same table with injected errors (read from CSV)
d.errors()  # ground truth: table, row_id, column, error_type, clean/dirty value
```

## How the data is made

`sim.py` simulates the chain day by day (2024-01-01 to 2025-12-31):

**true demand** (weekday, season, temperature, promotions, holidays, trend)
→ **shelves** (stock arrives after the supplier's lead time)
→ **recorded sales** = min(demand, stock on the shelf)
→ **orders** from a reorder policy that uses the shelf capacity
→ **deliveries**.

The shelf capacity is computed from the case dimensions in the product master data, so
errors in the master data change what the system orders (see `12-data-cascades`). Stock also
spoils (perishables) and disappears without a record (theft, damage). A weekly manual count
resets the system stock.

## Tables

Rows of the clean tables, as committed in `data/` (rows of the dirty copy in parentheses where
the count differs).

| Table | Rows | Source (reliability) | Notes |
|---|---|---|---|
| `products`, `suppliers`, `stores` | 60, 12, 8 (64, 13) | manual entry | GTIN-13, units `count`/`kg`/`liter`, case dimensions in cm |
| `zip_codes`, `planogram` | 12, 480 | master data | city of each ZIP code; shelf volume per store and product |
| `sales` | 350,880 (350,760) | POS (IT system) | daily per store and product; censored by stock-outs |
| `deliveries` | 198,421 (198,815) | manual receipt entry | denormalized as typed by the clerk; `received_at` vs `entered_at` |
| `stock_counts`, `stock_audit` | 49,920, 998 | manual count, independent re-count | 2 % of counts are audited |
| `inventory` | 350,880 | system | the stock on the shelf according to the system records |
| `weather` | 4,386 | external API | per weather station |
| `oos_reports` | 1,246 | crowdsourced (customer app) | "shelf is empty" reports, incomplete and noisy |
| `pos_events` | 3,228 | event stream | line level, 3 days (2025-06-02 to 2025-06-04), 3 stores |
| `checkout_lines` | 21,539 | POS + later corrections | weighed items; `was_corrected` = past repairs |
| `truth` | 350,880 | not observable | true demand, lost sales, waste, shrinkage, true stock |

`pos_events` and `checkout_lines` exist only in `data/dirty/`.

## Dirty data (`dirty=True`, `errors()`)

`corrupt.py` injects typical data quality problems and logs each one in `errors.csv` (5,824
rows, 21 error types): illegal values, wrong format, missing values, placeholders
(`999-9999999`, `1900-01-01`, shelf life `9999`), misspellings (`Pittsburg`, `Cauliflour`),
misfielded values (`city=USA`), violated dependencies (ZIP ↔ city, unit ↔ category), duplicate
keys and near-duplicate products, dangling references (supplier `502`, `283`), wrong but valid
references, wrong units (case dimensions in inches, grams as kg), wrong field order, an
80,000 kg banana delivery, duplicate and missing deliveries, outdated POS prices, a POS outage,
a double upload, transposed digits in stock counts, late and duplicated POS events, and a
terminal clock in UTC.

## Drift scenario (`drift_*()`)

The tables `sales` (376,560 rows), `stores` (10), `truth`, `weather`, and `scale_readings`
(the mean weight of the banana lines at the checkout, per store and day) are in `data/drift/`.

| Start | Kind | Event |
|---|---|---|
| 2025-01-15 | concept drift | fad diet: cucumber demand more than doubles |
| 2025-03-01 | sensor drift | store 2 scales read a little higher every day (until 2025-08-31) |
| 2025-04-01 | concept drift | a competitor opens next to store 3 (−30 % demand) |
| 2025-06-01 | data drift | two new stores in Florida |
| 2025-07-10 | data drift | heatwave in PA and OH (+8 °C, 3 weeks) |
| 2025-09-01 | schema drift | POS update in stores 7 and 8 records weights in lb |
| 2025-10-15 | schema drift | the weather API reports `temp_c` in °F |

## Tools

- [NumPy](https://numpy.org): arrays and random numbers. Here: the seeded simulation.
- [pandas](https://pandas.pydata.org): data frames. Here: all tables and the CSV export.
- [PyArrow](https://arrow.apache.org/docs/python/): reads and writes the Parquet cache.
- [pytest](https://pytest.org): the Python test framework. Here: checks that the data is
  deterministic, that the clean data meets all rules, and that each injected error is logged.
