# 09 · ML-based detection of data errors

**Slides:** *Detecting Inconsistencies* · *ML-based for Detecting Inconsistencies* · *Not many
standard tools, often custom data sciency solutions*

Each script scores its detector against the injected errors (`inventory_data.errors()`) and
prints the most suspicious records.

## What this project illustrates

| Point | Where to see it |
|---|---|
| Anomaly detection | `anomalies.py`: IsolationForest, LOF (scikit-learn), ECOD (PyOD), and a robust z-score find unusual delivery quantities, for example the 80,000 kg banana delivery. |
| Context matters more than the algorithm | `anomalies.py`: one contextual feature (the deviation from the usual quantity of this product in this store) helps more than a different algorithm. LOF fails because many deliveries have the same quantity. |
| Learning common patterns | `patterns.py`: finds column pairs where one value almost always sets the other (approximate functional dependencies, for example product ID → name). Rows that break them are suspicious: a misspelled name or a wrong ID. |
| Suspicious data, not clear mistakes | `patterns.py`: some learned patterns are only "usually true" (a supplier mostly delivers one category), so many of their violations are correct data. |
| Near-duplicate detection | `duplicates.py`: the exact rule "same store, product, date, and quantity" misses near duplicates and flags false pairs. Splink combines the evidence of several fields and ranks the pairs; at p ≥ 0.1 it finds all duplicate pairs with high precision. |
| Domain knowledge in a learned model | `duplicates.py`: EM alone learns the wrong clusters; two m-values from domain knowledge ("a duplicate has the same store, product, and date") fix this. |
| Learning from past repairs | `learn_from_repairs.py`: a gradient-boosting classifier trained on past corrections of weighed checkout lines ranks new lines for review. A review of 5 % of the lines finds most lines that need a correction. |

## Run

```sh
uv run anomalies.py           # unusual delivery quantities
uv run patterns.py            # learned dependencies and their violations
uv run duplicates.py          # near-duplicate delivery records with Splink
uv run learn_from_repairs.py  # predict which checkout lines staff will correct
```
