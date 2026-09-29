# 08 · Data quality rules and repair

The product, supplier, store, delivery, and sales tables of a supermarket chain contain
injected errors, and a log records each error ([dataset](../inventory-data/)).

**Problem.** Many errors pass a schema: each value is legal alone, but wrong together with
other values, rows, or tables. Examples: the city does not fit the ZIP code (`Pittsburg`,
`city=USA`), a bigger pack is cheaper than a smaller one, or a store sells more than it has
received. When an error is found, it is often not clear which value is wrong.

**Idea.** Write invariants as named rules that return the rows that break them, each with an
action (reject, repair, flag). Repair only where the correct value is known with confidence;
otherwise compute a probability for each repair and send the uncertain cases to a human.

Each rule is a name, a kind, an action, and an SQL query that returns the rows that break it
(`rules.py`). A rule across two rows of the same table:

```python
Rule(
    "Bigger pack of the same product is not cheaper",
    "denial constraint",
    "flag",
    """SELECT big.id AS row_id FROM products small JOIN products big
       ON small.family = big.family AND small.size < big.size
       WHERE try_cast(big.unit_price AS DOUBLE) < try_cast(small.unit_price AS DOUBLE)""",
    "products",
)
```

The probabilistic repair (`repair.py`) scores each frequent combination of values as a
candidate for a rare combination: frequent candidates and small, typo-like differences get a
high probability. Only repairs with p ≥ 0.9 are applied:

```python
logp = math.log(support) + sum(
    math.log(1 - EPS) if a == b else math.log(EPS * similarity(a, b, c))
    for c, a, b in zip(entity, observed, tup, strict=True)
)
...
target = applied if p >= 0.9 else review
```

## What the code shows

- `rules.py`: 12 rules as SQL queries, for example ZIP code ↔ city, the supplier exists,
  unique GTINs with a valid check digit, unit allowed for the category, placeholders
  (`999-9999999`, `1900-01-01`) as missing values, no second identical delivery, POS price =
  catalog price, and "a bigger pack of the same product is not cheaper" (a rule across two
  rows). For each rule, the script shows how many violations are injected errors.
- `rules.py`: the rule "you cannot sell more than the stock plus the deliveries" combines three
  sources. It finds forgotten and wrong delivery records, and also errors in the stock counts:
  a rule shows *that* something is wrong, not *what*.
- `repair.py`:
  1. A repair rule ("take the city from the ZIP code") fixes two stores and breaks one, where
     the ZIP code was the wrong value.
  2. Fuzzy matching against the catalog fixes typos in product names. When the name matches a
     different product than the ID, a human decides.
  3. A probabilistic repair in the style of [HoloClean](https://holoclean.github.io) learns the
     frequent combinations of product ID, name, category, unit, and supplier from the data
     (no reference data), scores repair candidates, and applies repairs with p ≥ 0.9. The rest
     go to a human. It is sometimes wrong.

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics. Here: each rule is
  one SQL query over the tables, also across tables.
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz): fast fuzzy string matching. Here: it
  matches misspelled product names to the catalog.
- [pandas](https://pandas.pydata.org): data frames. Here: the results and the repair
  candidates.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run rules.py    # 12 named rules, compared with the injected errors
uv run repair.py   # repair rules, fuzzy matching, probabilistic repair
```
