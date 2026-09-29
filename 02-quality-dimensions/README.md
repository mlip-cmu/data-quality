# 02 · Data quality dimensions

A supermarket chain collects data from many sources: staff type in products, deliveries, and
stock counts; the checkout (POS) systems record sales; a weather API and a customer app add
more data ([dataset](../inventory-data/)).

**Problem.** "Clean data" is not one property. Data can be wrong (accuracy), missing
(completeness), duplicated (uniqueness), contradictory (consistency), late (timeliness), or
malformed (validity). Each source has different problems.

**Idea.** Write one small check for each source and each dimension, and show the result as a
scorecard. This makes the reliability of each source visible, and shows which checks need a
second source (an audit or a reference table).

Each check is one SQL query that returns the share of good records, directly on the files.
Accuracy needs a second, independent source (here an audit re-count); timeliness compares
two timestamps:

```sql
-- accuracy: a manual stock count is within 5 % of the independent audit
SELECT avg((abs(c.counted_qty - a.audited_qty) <= 0.05 * a.audited_qty + 0.5)::int)
FROM stock_counts c JOIN stock_audit a USING (date, store_id, product_id)

-- timeliness: a delivery is entered within 24 h of its receipt
SELECT avg((entered_at - received_at <= INTERVAL 24 HOUR)::int) FROM deliveries
```

## What the code shows (`scorecard.py`)

- The share of good records for about 20 checks, for example: stock counts vs an independent
  re-count (accuracy), store-days without POS data (completeness), duplicate deliveries
  (uniqueness), city vs ZIP code and POS price vs catalog price (consistency), deliveries
  entered more than 24 h late (timeliness), and POS events with a time after their arrival,
  from a terminal clock in UTC (validity).
- The scorecard: the POS and the weather API are almost perfect; manual entry has problems in
  every dimension; only about 40 % of the crowdsourced out-of-stock reports are correct.

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics (no server). It can
  query CSV, Parquet, and JSON files directly. Here: each check is one SQL query on the files,
  with no loading step and no schema.
- [pandas](https://pandas.pydata.org): data frames. Here: the scorecard table.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run scorecard.py
```
