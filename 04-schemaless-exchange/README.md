# 04 · Schema-less data exchange

**Slides:** *Modern Databases: Schema-Less* · *Schema-Less Data Exchange* · *CSV Schema* ·
*Many Schema Libraries/Formats*

The systems of the supermarket chain and its suppliers exchange files
([dataset](../inventory-data/)). This folder has four of them: `products_export.csv` (the CSV
from the slide, plus more rows of the same export), `stock_export.csv` (from a store system),
`supplier_feed.json` (the product feed of a supplier), and `suppliers.csv`. `pitfalls.py`
reads the files without a schema; `validate.py` checks them against a schema.

**Problem.** A CSV or JSON file carries no types and no rules. The program that reads it must
infer the type of each column, the meaning of an empty cell, and the format of each date.
Wrong guesses often produce no error: the data loads, and the problem shows up much later, as
a failed join or a wrong sum.

**Idea.** Exchange a schema together with the data, and validate each file when it arrives.
For CSV, a [Frictionless](https://framework.frictionlessdata.io) Table Schema
(`datapackage.yaml`) lists the columns, their types, constraints, the primary key, and
foreign keys to other files. For JSON, a [JSON Schema](https://json-schema.org)
(`feed.schema.json`) does the same for each record. When reading without a validator, at
least give the types explicitly.

The store export has GTINs (barcode numbers) with a leading zero. `pitfalls.py` reads it
with pandas, which infers the type of each column from its values:

```python
stock = pd.read_csv("stock_export.csv")
catalog = d.products()
print(f"GTIN read as {stock.gtin.dtype}: {stock.gtin[0]} (leading zero lost)")
...
fixed = stock.astype({"gtin": str}).merge(catalog, on="gtin")
...
ok = pd.read_csv("stock_export.csv", dtype={"gtin": str}).merge(catalog, on="gtin")
```

The CSV Schema from the slide and the same rules as a Table Schema (`datapackage.yaml`):

```text
version 1.1                               fields:
@totalColumns 5                             - {name: ProductID, type: integer, constraints: {minimum: 1}}
id: positiveInteger                         - {name: Product Name, type: string, constraints: {minLength: 1, maxLength: 255}}
name: length(1,255)                         - {name: Quantity, type: number, constraints: {minimum: 0}}
quantity: numericLiteral                    - {name: Unit, type: string, constraints: {enum: [count, kg, liter]}}
unit: is("count") or is("kg") or is("liter")  - {name: SupplierID, type: integer}
supplierId: positiveInteger                 primaryKey + foreignKeys to suppliers.csv
```

## What the code shows

`pitfalls.py` (what pandas does without a schema):

1. **Guessed types.** In the 3 rows of the slide, one value `75.5` makes `Quantity` a float
   for all rows, also for products sold by count.
2. **Extra fields.** In the full export, one row has 6 fields. `read_csv` stops with
   `Expected 5 fields in line 11, saw 6`; with `on_bad_lines='warn'`, the row is silently
   dropped.
3. **One typo changes a column.** The quantity `7O` (letter O) makes `Quantity` a text column,
   and `Quantity.sum()` joins the strings (`'5075.53012.57O-4144848'`). The missing name and
   quantity become NaN, and the duplicate product ID 108 loads too. None of these problems
   raises an error.
4. **Implicit type conversion breaks joins.** The GTIN is read as an integer
   (`702010001014`). The join with the catalog fails with a type error; after
   `astype(str)`, 0 of 6 rows match, because the zero is gone. With
   `dtype={'gtin': str}` in `read_csv`, 6 of 6 rows match.
5. **Missing values and formats are ambiguous.** `N/A` becomes NaN; `38,2` (decimal comma)
   and `7O` stay text. `06/03/2025` is parsed as June 3, but it means March 6 in most
   countries outside the US.
6. **Schema-less JSON.** `json_normalize` flattens the 5 records of the supplier feed into 8
   columns: the price mixes numbers and strings, one record has the key `title` for the name,
   one GTIN is a number without the leading zero, one pack has no unit, units differ in case
   (`kg`, `KG`), and one record has an extra key `organic`. Document stores and REST APIs
   return such data.

`validate.py` (the same files with a schema):

7. **A schema for CSV.** Frictionless validates the data package and finds 9 errors in
   `products_export.csv`: 2 unknown suppliers (foreign keys `502`, `283`), a type error
   (`7O`), a negative quantity, a missing name, the unit `lbs`, a duplicate primary key, an
   extra cell, and a missing quantity. Frictionless checks foreign keys only when it validates
   the whole package.
8. **A schema for JSON.** JSON Schema finds 9 errors in 4 of the 5 records of the supplier
   feed (only the first record is valid): strings in place of numbers, `KG`, the GTIN as a
   number, the missing `name`, the unexpected keys `title` and `organic`, and the missing
   unit.

## Tools

- [pandas](https://pandas.pydata.org): data frames. Here: `read_csv` and `json_normalize`
  infer the types of the exchanged files.
- [Frictionless](https://framework.frictionlessdata.io): a framework to describe and validate
  tabular data (Table Schema, Data Package). Here: validates the CSV files against
  `datapackage.yaml`, from Python and from the command line.
- [jsonschema](https://python-jsonschema.readthedocs.io): validates JSON documents against a
  [JSON Schema](https://json-schema.org). Here: validates the supplier feed against
  `feed.schema.json` (draft 2020-12).
- [`inventory_data`](../inventory-data/): the shared dataset of this repository. Here: the
  product catalog for the join on the GTIN.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run pitfalls.py                              # what pandas does without a schema
uv run validate.py                              # Frictionless (CSV) and JSON Schema
uv run frictionless validate datapackage.yaml   # the same check from the command line
```
