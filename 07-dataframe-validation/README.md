# 07 · Schema checks after loading

Receiving clerks of a supermarket chain type in the deliveries, and staff maintain the
product master data ([dataset](../inventory-data/)).

**Problem.** Data often arrives as files or data frames, without a database that enforces a
schema. Errors such as negative quantities, a supplier name in the category column, or the
placeholder date `1900-01-01` then go into the training data unnoticed.

**Idea.** Check each new batch after loading and before it is used: declare expectations about
types, ranges, allowed values, uniqueness, and distributions. Report all failures at once,
send the bad rows to a quarantine, and let the good rows go on. The expectations can be
written by hand or learned from older data.

In Pandera, the schema is a class (`pandera_validate.py`). Fields declare types and value
constraints; methods add custom checks, also across columns:

```python
class ProductMaster(pa.DataFrameModel):
    gtin: Series[str] = pa.Field(str_matches=r"^\d{13}$", unique=True)
    unit: Series[str] = pa.Field(isin=["count", "kg", "liter"])
    unit_price: Series[float] = pa.Field(gt=0, le=500)

    @pa.check("gtin", name="gtin_check_digit")
    def check_digit(cls, gtin: Series[str]) -> Series[bool]:
        return gtin.map(gtin_is_valid)

    @pa.dataframe_check(name="produce_is_sold_by_count_or_kg")
    def produce_unit(cls, df: pd.DataFrame) -> Series[bool]:
        return (df.category != "produce") | df.unit.isin(["count", "kg"])
```

In Great Expectations (`gx_validate.py`), the checks are expectation objects in a suite, and
one validation run reports all failed expectations of a batch:

```python
for expectation in [
    gxe.ExpectColumnValuesToBeUnique(column="delivery_id"),
    gxe.ExpectColumnValuesToBeInSet(column="unit", value_set=["count", "kg", "liter"]),
    gxe.ExpectCompoundColumnsToBeUnique(
        column_list=["delivery_date", "store_id", "product_id", "quantity"]
    ),
    gxe.ExpectColumnMaxToBeBetween(column="quantity", max_value=2000),
]:
    suite.add_expectation(expectation)
```

## What the code shows

- `gx_validate.py` checks one month of deliveries with 14 expectations: types, a unique ID, a
  range, allowed values, a date range, `entered_at` ≥ `received_at`, unique combinations of
  columns, and the median, standard deviation, and maximum of the quantity.
  - The clean month passes. The month as typed in by the clerks fails 7 of 14 (negative
    quantities, an 80,000 kg banana delivery, unit spellings, a supplier name in the category
    column, `1900-01-01`, duplicate deliveries).
  - `delivery_id` is unique, but the same delivery is in the data two times: a unique ID does
    not mean unique records.
  - The HTML report is in `out/gx_docs/index.html`.
- `pandera_validate.py` checks the product master data:
  1. The schema is a Python class with types, ranges, allowed values, the GTIN check digit,
     and a check across columns (produce is sold by count or kg).
  2. Lazy validation collects all failures; bad rows go to `out/quarantine.csv` with a reason.
  3. `@pa.check_types` makes the schema the interface of a function: bad input fails at the call.
  4. `infer_schema` learns the ranges from February and checks March: it finds the errors, but
     also flags normal values that are only a bit larger.
- The limits: plausible single values (case dimensions in inches, a price that is too low,
  near-duplicate products) pass. See `08` and `09`.

## Tools

- [Great Expectations](https://greatexpectations.io) (GX Core): a framework for data tests
  ("expectations") on data frames and databases, with HTML reports (Data Docs).
- [Pandera](https://pandera.readthedocs.io): schemas for data frames as Python classes, with
  type checks, value checks, lazy validation, and schema inference.
- [pandas](https://pandas.pydata.org): data frames. Here: the batches that are checked.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run gx_validate.py       # Great Expectations on one month of delivery records
uv run pandera_validate.py  # Pandera schema for the product master data, with a quarantine
```
