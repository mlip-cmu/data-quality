# 14 · Data documentation and defensive monitoring

The forecasting team of a supermarket chain trains its model on the daily sales from the POS
team ([dataset](../inventory-data/)).

**Problem.** Data moves between teams without documentation of what it means, how it was
collected, or what the consumers assume about it. When the producer changes something (for
example, the POS systems switch weights from kg to lb), the data still looks valid, and the
consumer finds out late, from a bad model.

**Idea.** Document the dataset in a data card (purpose, fields and units, sources, known
problems), and generate its statistics from the data so that they stay correct. On the
consumer side, write the assumptions about the received data down as tests (structure and
distribution), and run them on each new batch before training. A failed test is a reason to
talk to the producing team.

The structure that the consumer expects is a Pandera schema (`pos_checks.py`):

```python
class DailySales(pa.DataFrameModel):
    store_id: pa.typing.Series[int] = pa.Field(ge=1)
    quantity: pa.typing.Series[float] = pa.Field(ge=0)
    unit_price: pa.typing.Series[float] = pa.Field(gt=0)

    class Config:
        unique = ["date", "store_id", "product_id"]
```

The switch to lb passes this schema. A distribution check against the same period of the last
year finds it:

```python
ratio = (now / before).dropna()  # mean quantity per store, now vs history
for store, r in ratio[(ratio < 1 - tolerance) | (ratio > 1 + tolerance)].items():
    problems.append(f"store {store}: mean {kind} quantity is {r:.2f} x the usual")
```

## What the code shows

- `DATACARD.md`: a data card for the dataset of this repository: creator and purpose, how to
  use it, fields with units, an example record, sources and their reliability, how the labels
  are made (the recorded sales are only a proxy for demand), distributions, noise, drift,
  biases, and curation.
- `datacard_stats.py`: generates the statistics section of `DATACARD.md` from the data.
- `tests/test_incoming_pos_data.py`: the tests of the forecasting team on each new batch.
  - The POS switch to lb in stores 7 and 8 passes the schema but fails the distribution check.
  - The same tests find a POS outage (missing store-days) and a double upload (duplicate keys).

## Tools

- [Pandera](https://pandera.readthedocs.io): schemas for data frames as Python classes, with
  type and value checks. Here: the expected structure of the POS data.
- [pytest](https://pytest.org): the Python test framework. Here: the consumer-side data tests.
- [pandas](https://pandas.pydata.org): data frames. Here: the POS batches and the statistics;
  [tabulate](https://github.com/astanin/python-tabulate) formats them as Markdown tables.
- [Data Cards](https://sites.research.google/datacardsplaybook/): a template from Google for
  the documentation of datasets. `DATACARD.md` uses its sections.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run datacard_stats.py   # update the generated statistics in DATACARD.md
uv run pytest              # the checks of the forecasting team on each new POS batch
```
