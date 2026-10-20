# 14 · Data documentation and defensive monitoring

**Slides:** *Data Documentation* · *Data Quality is a System-Wide Concern* · *Data Quality
Documentation* · *Data Card* · *Entries in data card* · *Poor Cross-organizational
Documentation*

The forecasting team of the supermarket chain trains its model on daily sales from the POS
(point of sale, the checkout system), which another team runs. This folder has a data card
for the dataset of this repository (`DATACARD.md`), a script that keeps its statistics
current, and the tests that the forecasting team runs on each new batch of POS data.

**Problem.** Data moves between teams, and the assumptions about it are rarely written down:
the unit of a column, the meaning of the label, the sources and how reliable they are. When
the producing team changes something (for example a software update that records weights in
pounds), nobody tells the consumers. The values still have the right type, so the change
passes unnoticed, and the model trains on wrong data.

**Idea.** Document the dataset in a data card: who made it and why, the fields with their
units, an example, the sources, the labeling, the distributions, and the known problems.
Generate the statistics from the data so that they stay correct. On the consumer side, write
the expectations down as code: a schema for the structure and a check of the distribution.
Run both as tests on each new batch before training (defensive monitoring).

The expectations of the forecasting team about the structure, as a
[Pandera](https://pandera.readthedocs.io) schema (`pos_checks.py`):

```python
class DailySales(pa.DataFrameModel):
    date: pa.typing.Series[pd.Timestamp]
    store_id: pa.typing.Series[int] = pa.Field(ge=1)
    product_id: pa.typing.Series[int] = pa.Field(ge=101)
    quantity: pa.typing.Series[float] = pa.Field(ge=0)
    unit_price: pa.typing.Series[float] = pa.Field(gt=0)
    promo: pa.typing.Series[bool]

    class Config:
        unique = ["date", "store_id", "product_id"]
```

## What the code shows

1. **A data card.** `DATACARD.md` describes the dataset of this repository with the sections
   of a data card: creator and purpose, how to use it, the fields with units (case
   dimensions in cm, `gtin` as text with the leading zero), an example datapoint, the
   sources and their reliability, labeling, distributions, noise, drift, biases, curation,
   and maintenance.
2. **The label is a proxy.** The section "Labeling process" states that the label is the
   recorded sales, a proxy for demand: on a day with a stock-out, the sales show only what
   was on the shelf.
3. **Documentation that stays correct.** `datacard_stats.py` computes the section "Data
   distribution" from the data and writes it between two marker lines in `DATACARD.md`:
   the size of each table (`sales` has 350,880 rows), the products and share of revenue per
   category, the sales per day by unit, and the injected errors per table and type. For
   example, 6.2 % of the product-days are on promotion, and on 1.1 % of the
   store-product-days the system stock is zero (the recorded sales are censored).
4. **Expectations at the interface.** `pos_checks.py` has the schema above and the function
   `distribution_problems`. For each store, it compares the mean quantity of kg items and of
   count items in the new batch with the same month of the last year; a ratio outside
   0.65 to 1.35 is a problem. It also reports a store with less than 95 % of the expected
   rows (products × days).
5. **Local tests of structure and distribution.** `tests/test_incoming_pos_data.py` runs
   both checks on a batch of one month for stores 1 to 8. The clean batch of September 2025
   passes the schema and has no distribution problems.
6. **A schema change without notice.** In the drift scenario, a POS update in stores 7 and 8
   records weights in lb from 2025-09-01. The batch of September 2025 (14,400 rows) passes
   the schema, because the types and ranges do not change. The distribution check reports
   "store 7: mean kg quantity is 2.14 x the usual" and 2.22 for store 8. The forecasting
   team can call the POS team before the bad data reaches the model.
7. **Other problems found by the same tests.** In the dirty data, the POS outage in February
   2025 gives "store 6: only 1500 of 1680 rows (missing days?)". The double upload in May
   2025 repeats the 60 rows of store 3 on 2025-05-05, and the schema validation fails
   because `date`, `store_id`, `product_id` are no longer unique.

All 5 tests pass (`uv run pytest -q`).

## Tools

- [Data Cards](https://sites.research.google/datacardsplaybook/): a template for dataset
  documentation from Google Research. Here: the sections of `DATACARD.md`.
- [Pandera](https://pandera.readthedocs.io): schemas for data frames, with types, ranges,
  and uniqueness. Here: the schema `DailySales` of the POS batches.
- [pandas](https://pandas.pydata.org) with [tabulate](https://github.com/astanin/python-tabulate):
  data frames, and Markdown tables from them (`to_markdown`). Here: the statistics of the
  data card and the distribution check.
- [pytest](https://docs.pytest.org): a test framework. Here: the checks on each new batch.
- [`inventory-data`](../inventory-data/): the shared dataset. Here: the clean, dirty, and
  drift sales, and the unit of each product.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run datacard_stats.py   # update the generated statistics in DATACARD.md
uv run pytest              # the checks of the forecasting team on each new POS batch
```
