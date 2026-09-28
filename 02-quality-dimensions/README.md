# 02 · Data quality dimensions

**Slides:** *What do we mean by clean data?* · *Data comes from many sources* · *Data is noisy*.
**Paper:** goodness-of-data, not only goodness-of-fit.

`scorecard.py` runs one SQL check for each source and each quality dimension. DuckDB queries
the CSV and Parquet files directly (no loading step, no schema). The script prints the share of
good records for each check and a scorecard (source × dimension).

## What this project illustrates

| Point | Where to see it |
|---|---|
| Accuracy | Manual stock counts vs the independent audit re-count; crowdsourced out-of-stock reports vs the real stock-outs. |
| Completeness | Product name and category present; every open store reports every day (the POS outage); one weather reading per station and day; stock-outs that the app users reported. |
| Uniqueness | Unique product IDs, POS rows, and POS event IDs; no second identical delivery. |
| Consistency | City vs ZIP code (with a ZIP reference table); product name vs product ID in the deliveries; POS price vs catalog price. |
| Timeliness | Deliveries entered within 24 h of receipt; POS events that arrive in order. |
| Validity | Allowed units, positive prices, phone number format, unit spelling, a temperature range, and POS event times that are after their arrival (a terminal clock in UTC). |
| Data comes from many sources, with different reliability | The scorecard rows: the POS and the weather API are almost perfect; manual entry has problems in every dimension; the crowdsourced app reports are correct in only about 40 % of cases. |
| Some checks need a second source | Accuracy needs the audit; consistency needs the reference table or the catalog. |

## Run

```sh
uv run scorecard.py
```
