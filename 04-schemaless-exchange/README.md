# 04 · Schema-less data exchange

Systems of a supermarket chain exchange files: a product export (`products_export.csv`), a
stock export of a store system (`stock_export.csv`), the product feed of a supplier
(`supplier_feed.json`), and a supplier list (`suppliers.csv`) ([dataset](../inventory-data/)).

**Problem.** CSV, JSON, and data frames have no enforced schema. A reader guesses the types,
and when the guess is wrong, nothing fails: numbers become text, IDs lose leading zeros,
joins find nothing, and records with other keys or nesting are read without an error.

**Idea.** Write the expected structure down as an explicit schema next to the data, and
validate each file against it before it is used: a Table Schema for CSV, a JSON Schema for
JSON.

The schema is a separate file next to the data (`datapackage.yaml`). It gives each column a
type and constraints, and declares the keys between the files:

```yaml
- name: Unit
  type: string
  constraints: {required: true, enum: [count, kg, liter]}
...
primaryKey: [ProductID]
foreignKeys:
  - fields: [SupplierID]
    reference: {resource: suppliers, fields: [id]}
```

One call validates all files of the package and reports each problem with its row and field
(`validate.py`):

```python
report = Package("datapackage.yaml").validate()
for row, field, kind, note in report.flatten(["rowNumber", "fieldName", "type", "note"]):
    print(f"  row {row or '-':>3}  {field or '':<13} {kind:<17} {note}")
```

## What the code shows

- `pitfalls.py`, what pandas does without a schema:
  - one value `75.5` makes all quantities floats; one typo `7O` makes the column text, and
    `sum()` then joins strings;
  - the GTIN is read as a number, the leading zero is lost, and the join with the catalog
    finds nothing, also after `astype(str)`;
  - `N/A` becomes NaN, a decimal comma stays text, and `06/03/2025` can be March or June;
  - a row with an extra field stops the whole read, or `on_bad_lines` drops it silently;
  - the JSON records have different keys, types, and nesting.
- `datapackage.yaml` + `validate.py`: the Table Schema finds type errors, constraint errors,
  duplicate keys, unknown suppliers (foreign keys), and extra cells in the CSV files.
  Frictionless checks foreign keys only when it validates the whole package.
- `feed.schema.json` + `validate.py`: JSON Schema reports each bad record of the supplier feed.

The same rules in [CSV Schema](https://digital-preservation.github.io/csv-schema/) (another
schema language for CSV) and in the Table Schema of `datapackage.yaml`:

```text
version 1.1                               fields:
@totalColumns 5                             - {name: ProductID, type: integer, constraints: {minimum: 1}}
id: positiveInteger                         - {name: Product Name, type: string, constraints: {minLength: 1, maxLength: 255}}
name: length(1,255)                         - {name: Quantity, type: number, constraints: {minimum: 0}}
quantity: numericLiteral                    - {name: Unit, type: string, constraints: {enum: [count, kg, liter]}}
unit: is("count") or is("kg") or is("liter")  - {name: SupplierID, type: integer}
supplierId: positiveInteger                 primaryKey + foreignKeys to suppliers.csv
```

## Tools

- [pandas](https://pandas.pydata.org): data frames. Here: `read_csv` and `json_normalize`
  without a schema.
- [Frictionless](https://framework.frictionlessdata.io): validates tabular data against a
  [Table Schema](https://specs.frictionlessdata.io/table-schema/) (types, constraints, keys),
  from Python or the command line.
- [jsonschema](https://python-jsonschema.readthedocs.io): validates JSON data against a
  [JSON Schema](https://json-schema.org).

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run pitfalls.py                              # what pandas does without a schema
uv run validate.py                              # Frictionless (CSV) and JSON Schema
uv run frictionless validate datapackage.yaml   # the same check from the command line
```
