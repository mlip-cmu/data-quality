# 04 · Schema-less data exchange

**Slides:** *Modern Databases: Schema-Less* · *Schema-Less Data Exchange* · *CSV Schema* ·
*Many Schema Libraries/Formats*

Files that systems exchange: `products_export.csv` (the CSV from the slide, plus more rows of
the same export), `stock_export.csv` (a store system), `supplier_feed.json` (the product feed
of a supplier), and `suppliers.csv`.

## What this project illustrates

| Point | Where to see it |
|---|---|
| Without a schema, the reader guesses the types, and wrong guesses fail silently | `pitfalls.py`: one value `75.5` makes all quantities floats; one typo `7O` makes the column text, and `sum()` then joins strings. |
| Implicit type conversion breaks joins | `pitfalls.py`: the GTIN is read as a number, the leading zero is lost, and the join with the catalog finds nothing, also after `astype(str)`. |
| Missing values and formats are ambiguous | `pitfalls.py`: `N/A` becomes NaN, a decimal comma stays text, `06/03/2025` can be March or June. |
| Wrong field order and extra fields | `pitfalls.py`: a row with an extra field stops the whole read, or `on_bad_lines` drops it. |
| Schema-less JSON (document stores, REST) | `pitfalls.py`: the records of the supplier feed have different keys, types, and nesting (`json_normalize`). |
| Enforce a schema on CSV (CSV Schema) | `datapackage.yaml` + `validate.py`: a Frictionless Table Schema finds type errors, constraint errors, duplicate primary keys, unknown suppliers (foreign keys), and extra cells. |
| Enforce a schema on JSON | `feed.schema.json` + `validate.py`: JSON Schema finds each bad record of the supplier feed. |

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

Frictionless checks foreign keys only when it validates the whole package.

## Run

```sh
uv run pitfalls.py                              # what pandas does without a schema
uv run validate.py                              # Frictionless (CSV) and JSON Schema
uv run frictionless validate datapackage.yaml   # the same check from the command line
```
