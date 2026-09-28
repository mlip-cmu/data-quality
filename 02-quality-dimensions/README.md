# 02 · Data quality dimensions

**Slides:** *What do we mean by clean data?* (accuracy, completeness, uniqueness, consistency,
timeliness) · *Data comes from many sources* · *Data is noisy*. **Paper:** "goodness-of-data"
instead of only goodness-of-fit.

`scorecard.py` runs one SQL check per source and dimension with DuckDB directly on the CSV and
Parquet files (no loading step, no schema). It prints the share of good records and a scorecard.

```sh
uv run scorecard.py
```

What to look for:
- The sources have very different reliability. The IT system (POS) and the weather API are
  almost perfect. Manual entry has errors in every dimension. The crowdsourced app reports
  are right only in about 40 % of cases and cover only about 14 % of the real stock-outs.
- Some checks need a second source: accuracy needs the independent audit of the stock counts,
  consistency needs the ZIP reference table or the catalog.
- A terminal clock in UTC is not a timeliness problem (events do not arrive late), but it is
  a validity problem: events arrive before they happen.
