# 08 · Data quality rules and repair

**Slides:** *Wrong and Inconsistent Data* (missing values, misspellings, misfielded values,
duplicates, wrong references) · *Discussion: error detection and repair* · *Example Tool: Great
Expectations* (invariants across attributes and sources; ZIP and city, IDs refer to existing
records, uniqueness, "lower income → not a higher tax rate") · *Example: HoloClean*

```sh
uv run rules.py    # 12 named rules in SQL (DuckDB), scored against the injected errors
uv run repair.py   # repair rules, fuzzy matching, HoloClean-style probabilistic repair
```

`rules.py` is a small rule catalog. Each rule is an SQL query that returns the rows that break
it, plus an action (reject, repair, flag). The rules go beyond a schema: ZIP code ↔ city, the
supplier exists, unique and valid GTINs, a conditional constraint (unit by category), a denial
constraint across two rows (the inventory version of the tax-rate example: a bigger pack of the
same product must not be cheaper), placeholders, consistency between the delivery records and
the catalog, duplicate deliveries, and consistency between the POS prices and the catalog.
The cross-source invariant "you cannot sell more than the stock plus the deliveries" connects
three sources. It finds forgotten and wrongly entered delivery records, and also fires for
errors in the stock counts: a rule shows *that* something is wrong, not *what*. Cross-table
rules are SQL here; Great Expectations (see `07`) checks one table at a time on pandas.

`repair.py`:
1. **Repair rules** are cheap but must know which value is wrong. "Take the city from the ZIP
   code" fixes two stores and breaks one, where the ZIP code was the wrong value.
2. **Fuzzy matching** against the catalog (rapidfuzz) fixes typos in product names. When the name
   matches *another* product than the ID, it cannot decide; these go to a human.
3. **HoloClean-style repair** uses no reference data. It learns the frequent combinations of
   (product ID, name, category, unit, supplier) from the data. For each rare combination it
   scores repair candidates (frequency of the candidate × probability of the difference;
   similar strings are more likely typos) and gives each repair a probability. Repairs with
   p ≥ 0.9 are applied, the rest go to a human. It fixes typos, misfielded values, unit
   spellings, and wrong product IDs together, and it is sometimes wrong.
