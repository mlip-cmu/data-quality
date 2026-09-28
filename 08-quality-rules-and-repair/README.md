# 08 · Data quality rules and repair

**Slides:** *Wrong and Inconsistent Data* · *Discussion: error detection and repair* ·
*Example Tool: Great Expectations* (invariants across attributes and sources) · *Example:
HoloClean*

`rules.py` is a small rule catalog. Each rule is an SQL query (DuckDB) that returns the rows
that break it, plus an action (reject, repair, flag). For each rule, the script shows how many
violations are injected errors.

## What this project illustrates

| Point | Where to see it |
|---|---|
| Missing values | `rules.py`: placeholders (`999-9999999`, `1900-01-01`, shelf life `9999`) become missing values. |
| Misspellings and misfielded values | `rules.py`: the ZIP code ↔ city rule finds `Pittsburg` and `city=USA`. |
| Illegal values | `rules.py`: delivery dates that are not in the data period. |
| Invariants between attributes | `rules.py`: ZIP code ↔ city; product name ↔ product ID; unit allowed for the category (a conditional constraint). |
| IDs refer to existing records | `rules.py`: the supplier of each product exists. |
| Uniqueness and format | `rules.py`: unique GTINs with a valid check digit; no second identical delivery. |
| A denial constraint across two rows ("lower income → not a higher tax rate") | `rules.py`: a bigger pack of the same product must not be cheaper. |
| Invariants across sources | `rules.py`: POS prices vs the catalog; "you cannot sell more than the stock plus the deliveries" (three sources). |
| A rule shows *that* something is wrong, not *what* | `rules.py`: the stock rule finds forgotten and wrong delivery records, and also errors in the stock counts. |
| Repair rules must know which value is wrong | `repair.py`, step 1: "take the city from the ZIP code" fixes two stores and breaks one, where the ZIP code was the wrong value. |
| Fuzzy matching against reference data | `repair.py`, step 2: rapidfuzz fixes typos in product names. When the name matches a different product than the ID, a human decides. |
| Probabilistic repair (HoloClean) | `repair.py`, step 3: learns frequent combinations of product ID, name, category, unit, and supplier from the data (no reference data), scores repair candidates, and gives each repair a probability. Repairs with p ≥ 0.9 are applied, the rest go to a human. It is sometimes wrong. |

## Run

```sh
uv run rules.py    # 12 named rules, scored against the injected errors
uv run repair.py   # repair rules, fuzzy matching, HoloClean-style probabilistic repair
```
