# 04 · Schema-less data exchange

**Slides:** *Schema-Less Data Exchange* (CSV, JSON, REST, DataFrames; benefits, drawbacks, how to
enforce a schema) · *CSV Schema* · *Many Schema Libraries/Formats*

Files exchanged between systems: `products_export.csv` (the CSV from the slide plus more rows
from the same export), `stock_export.csv` (a store system), `supplier_feed.json` (a supplier's
product feed), and `suppliers.csv`.

```sh
uv run pitfalls.py   # what pandas does without a schema
uv run validate.py   # enforce a schema: Frictionless Table Schema (CSV) and JSON Schema
uv run frictionless validate datapackage.yaml   # the same check from the command line
```

`pitfalls.py` shows that a reader without a schema guesses, and the guesses fail silently:
- one value `75.5` makes all quantities floats; one typo `7O` makes the column text, and
  `sum()` then concatenates strings;
- the GTIN is read as a number, so the leading zero is lost and the join with the catalog finds
  nothing, even after `astype(str)`;
- `N/A` becomes NaN, a decimal comma stays text, `06/03/2025` is ambiguous;
- a row with an extra field fails the whole read, or is dropped with `on_bad_lines`;
- JSON records have different keys, types, and nesting.

`validate.py` checks the same files against an explicit schema. The Table Schema in
`datapackage.yaml` is the Python-friendly equivalent of the CSV Schema on the slide:

```text
version 1.1                               fields:
@totalColumns 5                             - {name: ProductID, type: integer, constraints: {minimum: 1}}
id: positiveInteger                         - {name: Product Name, type: string, constraints: {minLength: 1, maxLength: 255}}
name: length(1,255)                         - {name: Quantity, type: number, constraints: {minimum: 0}}
quantity: numericLiteral                    - {name: Unit, type: string, constraints: {enum: [count, kg, liter]}}
unit: is("count") or is("kg") or is("liter")  - {name: SupplierID, type: integer}
supplierId: positiveInteger                 primaryKey + foreignKeys to suppliers.csv
```

Frictionless also checks the primary key, the foreign key to `suppliers.csv` (the slide's
suppliers `502` and `283` do not exist), and extra cells. Foreign keys are only checked when
you validate the whole package. `feed.schema.json` does the same for the JSON feed.
