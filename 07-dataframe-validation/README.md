# 07 · Schema checks after loading

**Slides:** *Schema Checks after Loading* · *Data Schema* · *What Happens When New Data
Violates Schema?* · *Detecting Data Drift* (distributions can be specified or learned)

Clerks in the stores type in each delivery, and an office keeps the product master data
([dataset](../inventory-data/), tables `deliveries` and `products`, each in a clean version and
a version with injected errors). This folder checks both tables after they are loaded into a
pandas data frame: the deliveries with Great Expectations (`gx_validate.py`), the products with
Pandera (`pandera_validate.py`).

**Problem.** Data often arrives as CSV files or from sources that do not enforce a schema. A
negative quantity, a unit spelled `KG`, or a supplier name in the category column loads
without any error, and the training pipeline uses it.

**Idea.** Write the expected schema as checks on a data frame and run them on each new batch,
before the pipeline uses it. The checks cover types, unique keys, ranges, allowed values,
relations between columns, and statistics of a column. A failing batch can stop the pipeline,
or the bad rows go to a quarantine and the good rows go on. Some bounds can be learned from
older data.

The checks from the slide, as Great Expectations classes (`gx_validate.py`):

```python
expectations = [
    gxe.ExpectColumnValuesToBeOfType(column="delivery_id", type_="int64"),
    gxe.ExpectColumnValuesToBeUnique(column="delivery_id"),
    gxe.ExpectColumnValuesToBeBetween(column="quantity", min_value=0, max_value=None),
    gxe.ExpectColumnValuesToBeInSet(column="unit", value_set=["count", "kg", "liter"]),
]
```

The schema of the product master data as a Python class (`pandera_validate.py`, trimmed):

```python
class ProductMaster(pa.DataFrameModel):
    id: Series[int] = pa.Field(unique=True, gt=100)
    gtin: Series[str] = pa.Field(str_matches=r"^\d{13}$", unique=True)
    unit: Series[str] = pa.Field(isin=["count", "kg", "liter"])
    unit_price: Series[float] = pa.Field(gt=0, le=500)

    @pa.check("gtin", name="gtin_check_digit")
    def check_digit(cls, gtin: Series[str]) -> Series[bool]:
        return gtin.map(gtin_is_valid)
```

## What the code shows

- `gx_validate.py`, on the deliveries entered in March 2025:
  1. **The checks from the slide.** Types, a unique `delivery_id`, quantities of at least 0,
     and the set of units.
  2. **More checks on the same batch.** Known suppliers and categories, a delivery date in
     2024 or 2025, `entered_at` ≥ `received_at`, unique combinations of date, store,
     product, and quantity, and the median, standard deviation, and maximum of the quantity:
     14 checks in total.
  3. **Clean data passes, entered data fails.** The clean month (8,047 deliveries) meets all
     14 checks. The same month as typed in by the clerks (8,071 deliveries) meets 7 of 14: 4
     negative quantities, a maximum of 80,000 (80,000 kg of bananas) and a standard
     deviation of about 1,687, 46 unit spellings (`KG`, `Kg`, `ct`, `Count`), 13 supplier
     names in the category column, 2 placeholder dates 1900-01-01, and 52 rows with the
     same date, store, product, and quantity as another row.
  4. **A unique ID does not mean unique records.** `delivery_id` passes the uniqueness check,
     but some deliveries are in the data two times, each with its own ID.
  5. **A report for humans.** GX Data Docs writes the results as HTML pages to
     `out/gx_docs/index.html`.
- `pandera_validate.py`, on the 64 rows of the product master data:
  1. **A schema as a Python class.** `ProductMaster` has types, ranges, allowed values, the
     GTIN check digit, and one check across columns (produce is sold by `count` or `kg`).
  2. **Quarantine for bad rows.** Lazy validation collects all failures at once. 17 rows go
     to `out/quarantine.csv` with a reason (for example `unit isin(...) [lbs]`, a price
     `2,99`, a supplier 502 that does not exist, shelf life 9999 days); the 47 good rows go
     on to `out/products_valid.parquet`. The pipeline does not stop.
  3. **The schema as the interface of a function.** `shelf_capacity` is decorated with
     `@pa.check_types`. Called with the raw data, it raises `SchemaErrors` with 63 failures;
     with the valid rows, it returns 47 values.
  4. **A learned schema.** `infer_schema` learns the range of `quantity` from the clean
     February data (2 to 126) and checks the March data as entered. It flags 23 deliveries:
     21 are injected errors, and 2 are normal values that are only larger than anything in
     February.
  5. **The limits of schema checks.** Single values that look plausible pass: most case
     heights in inches, a price that is too low, and a near-duplicate product name. These
     need rules across rows and tables ([08](../08-quality-rules-and-repair/),
     [09](../09-ml-error-detection/)).

## Tools

- [Great Expectations](https://greatexpectations.io) (GX Core 1.x): a library for data
  checks ("expectations") with HTML reports (Data Docs). Here: 14 expectations on one month
  of deliveries.
- [Pandera](https://pandera.readthedocs.io): schemas for data frames as Python classes. Here:
  the schema of the product master data, the quarantine, a typed function, and the inferred
  schema.
- [pandas](https://pandas.pydata.org): data frames. Here: loads the tables.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run gx_validate.py       # Great Expectations on one month of delivery records
uv run pandera_validate.py  # Pandera schema for the product master data, with a quarantine
```
