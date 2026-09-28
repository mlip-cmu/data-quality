# inventory-data: the shared dataset

A synthetic, deterministic dataset for the case study of the lecture: a supermarket chain
with 8 stores in Pennsylvania and Ohio (plus 2 new stores in Florida in the drift scenario),
60 products, and 12 suppliers. An ML model predicts future sales to decide what to restock,
when, and how many.

Every other project uses this package as a local path dependency. The data is generated on
first use (about 10 s) and cached as Parquet in `data/`.

The same data is committed as CSV, so you can look at it on GitHub:

- `data/clean/`: the true data; `data/dirty/`: the same tables with injected errors and
  `errors.csv` (a log of each error); `data/drift/`: the drift scenario.
- `data/preview/`: files that are small enough for the table view of GitHub. Small tables
  are complete. Large tables are an extract of store 1 in March 2025 (drift: store 7 from
  2025-08-15 to 2025-09-15, around the POS switch to lb).

```sh
uv run inventory-data          # generate (or show) the cached files
uv run inventory-data --force  # regenerate (the CSV files are the same each time)
uv run pytest                  # checks: deterministic, clean data meets all rules, errors logged
```

```python
import inventory_data as d

d.products()  # clean master data
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

| Table | Source (reliability) | Notes |
|---|---|---|
| `products`, `suppliers`, `stores` | manual entry | GTIN-13, units `count`/`kg`/`liter`, case dimensions in cm |
| `sales` | POS (IT system) | daily per store and product; censored by stock-outs |
| `deliveries` | manual receipt entry | denormalized as typed by the clerk; `received_at` vs `entered_at` |
| `stock_counts`, `stock_audit` | manual count, independent re-count | 2 % of counts are audited |
| `inventory` | system | stock the system believes is on the shelf |
| `weather` | external API | per weather station |
| `oos_reports` | crowdsourced (customer app) | "shelf is empty" reports, incomplete and noisy |
| `pos_events` | event stream | line level, 3 days, 3 stores |
| `checkout_lines` | POS + later corrections | weighed items; `was_corrected` = past repairs |
| `truth` | not observable | true demand, lost sales, waste, shrinkage, true stock |

## Dirty data (`dirty=True`, `errors()`)

`corrupt.py` injects the problems from the lecture and logs each one: illegal values, wrong
format, missing values, placeholders (`999-9999999`, `1900-01-01`, shelf life `9999`),
misspellings (`Pittsburg`, `Cauliflour`), misfielded values (`city=USA`), violated
dependencies (ZIP ↔ city, unit ↔ category), duplicate keys and near-duplicate products,
dangling references (supplier `502`, `283`), wrong but valid references, wrong units
(case dimensions in inches, grams as kg), wrong field order, an 80,000 kg banana delivery,
duplicate and missing deliveries, outdated POS prices, a POS outage, a double upload,
transposed digits in stock counts, late and duplicated POS events, and a terminal clock in UTC.

## Drift scenario (`drift_*()`)

| Start | Kind | Event |
|---|---|---|
| 2025-01-15 | concept drift | fad diet: cucumber demand more than doubles |
| 2025-03-01 | sensor drift | store 2 scales read a little higher every day (until 2025-08-31) |
| 2025-04-01 | concept drift | a competitor opens next to store 3 (−30 % demand) |
| 2025-06-01 | data drift | two new stores in Florida |
| 2025-07-10 | data drift | heatwave in PA and OH (+8 °C, 3 weeks) |
| 2025-09-01 | schema drift | POS update in stores 7 and 8 records weights in lb |
| 2025-10-15 | schema drift | the weather API reports `temp_c` in °F |
