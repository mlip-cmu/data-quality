# 08 · Data quality rules and repair

**Slides:** *Wrong and Inconsistent Data* · *Discussion: error detection and repair* ·
*Example Tool: Great Expectations* (invariants across attributes and sources) · *Example:
HoloClean*

The tables of the supermarket chain ([dataset](../inventory-data/)) have errors that pass a
schema check: a misspelled city, a delivery record with the name of another product, a price
at the till that differs from the catalog. The dataset logs each injected error (`errors.csv`),
so we can count how many violations of a rule are real errors. This folder has a catalog of
rules (`rules.py`) and three ways to repair the data (`repair.py`).

**Problem.** Many errors are plausible values on their own. They show up only when we compare
values: two columns of one row, two rows of one table, or several tables (stock counts, sales,
deliveries). A rule returns the rows with an inconsistency, and these rows do not show which
of the values is wrong, so an automatic repair can make the data worse.

**Idea.** Write each invariant as a rule that returns the rows that break it, with an action:
reject the row, repair it, or flag it for a human. Repair only when the wrong value is clear:
with reference data (a list of ZIP codes, the product catalog) and fuzzy matching, or with the
frequent value combinations of the data itself, as HoloClean does. Give each repair a
probability and send the uncertain ones to a human.

Each rule in `rules.py` is an SQL query for DuckDB, run on the tables as data frames. A denial
constraint across two rows of the same product family:

```python
RULES = [
    Rule(
        "Bigger pack of the same product is not cheaper",
        "denial constraint",
        "flag",
        """
        SELECT big.id AS row_id FROM products small JOIN products big
        ON small.family = big.family AND small.size < big.size
        WHERE try_cast(big.unit_price AS DOUBLE) < try_cast(small.unit_price AS DOUBLE)""",
        "products",
    ),
]
```

## What the code shows

- `rules.py`: 12 rules on the dirty tables. For each rule, the script prints the number of
  violations and how many of them are injected errors.
  1. **Invariants between attributes.** ZIP code ↔ city: 3 of 3 are errors (the misspelling
     `Pittsburg`, the misfielded value `city=USA`, and one wrong ZIP code). Product name ↔
     product ID in the deliveries: 977 of 977. Unit allowed for the category (a conditional
     constraint, for example produce by `count` or `kg`): 3 of 3.
  2. **IDs refer to existing records.** 2 products with a supplier that does not exist; both
     are errors.
  3. **Uniqueness and format.** Unique GTINs: 2 of 2. A valid GTIN check digit: 1 of 1.
  4. **A denial constraint across two rows.** The rule from the slide ("lower income → not a
     higher tax rate") here reads "a bigger pack of the same product is not cheaper": 1 of 1.
  5. **Missing values.** The placeholders `999-9999999` (phone) and shelf life `9999` are
     missing values that the rule repairs to empty: 2 of 2. The placeholder date
     `1900-01-01` is caught by the next rule.
  6. **Duplicates and illegal values in the deliveries.** No second identical delivery: 727
     violations, 711 of them injected duplicates. Delivery dates outside the data period: 96
     of 96.
  7. **Invariants across sources.** POS prices without a promotion equal the catalog price:
     542 of 542. "A store cannot sell more than its stock plus the deliveries" (sales, stock
     counts, and deliveries): 295 violations.
  8. **A rule finds the inconsistency; the cause needs more work.** The 295 days of the stock
     rule come from 54 forgotten delivery records, 207 deliveries entered wrongly (unit, date,
     product), and 34 errors in the manual stock counts. (The table prints 0 injected errors
     for this rule because the errors are logged for the deliveries and the stock, and the
     rule returns rows of the sales.)
- `repair.py`:
  1. **Repair rules.** "Take the city from the ZIP code" fixes store 2 (`Pittsburg` →
     `Pittsburgh`) and store 6 (`USA` → `Erie`), and breaks store 5 (`Monroeville` →
     `Pittsburgh`): there the ZIP code was the wrong value. A mapping of unit spellings
     (`KG` → `kg`, `ct` → `count`) repairs 990 of 990 cells correctly.
  2. **Fuzzy matching against reference data.** RapidFuzz compares each product name in the
     deliveries with the catalog. 571 typos are fixed automatically, all correctly (of 593
     injected typos). 406 deliveries go to a human: the name matches a different product
     than the ID, for example product 157 (Refill Oat Milk) with the name `Refill Olive Oil`.
  3. **Probabilistic repair (HoloClean style).** The script counts the combinations of
     product ID, name, category, unit, and supplier, and treats the frequent ones (at least
     30 rows) as the correct ones. No reference data is used. For each rare combination, it
     scores the frequent combinations that differ in at most 2 columns and computes a
     probability for the best one. Repairs with p ≥ 0.9 are applied: 2,002 cells, 1,931
     correct and 71 wrong (of 2,172 injected errors of these kinds). 162 more cells have
     p < 0.9 and go to a human. Examples: `Baana` → `Banana`, category
     `Fresh Fields Produce` → `produce`, product ID 101 → 160 for `Hummus 10 oz`.

## Tools

- [DuckDB](https://duckdb.org): an in-process SQL database for analytics. Here: runs the
  rules as SQL queries directly on pandas data frames, with a Python function for the GTIN
  check digit.
- [pandas](https://pandas.pydata.org): data frames. Here: the tables, the scores, and the
  repairs.
- [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/): fast fuzzy string matching. Here:
  product names against the catalog, and the similarity of values in the HoloClean-style
  repair.
- [HoloClean](https://github.com/HoloClean/holoclean): a research system for probabilistic
  data repair. Here: only the idea; `repair.py` has a small version in plain Python.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run rules.py    # 12 named rules, scored against the injected errors
uv run repair.py   # repair rules, fuzzy matching, HoloClean-style probabilistic repair
```
