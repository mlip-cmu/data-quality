# 09 · ML-based detection of data errors

**Slides:** *Detecting Inconsistencies* ("most approaches use ML"; anomaly detection, learning
common patterns, near-duplicate detection, learning from past repairs; "usually identifying
suspicious data rather than clear mistakes") · *Not many standard tools, often custom data
sciency solutions* (PyOD, Isolation Forest, LOF, Splink, …)

Every script scores its detector against the injected errors (`inventory_data.errors()`).

```sh
uv run anomalies.py           # unusual delivery quantities (the 80,000 kg banana delivery)
uv run patterns.py            # learn approximate dependencies (product ID -> name) and outliers
uv run duplicates.py          # near-duplicate delivery records with Splink
uv run learn_from_repairs.py  # predict which checkout lines staff will have to correct
```

- `anomalies.py`: IsolationForest, LOF (scikit-learn), and ECOD (PyOD) with raw features and
  with one contextual feature (the deviation from the usual quantity of this product in this
  store), plus a simple robust z-score. The context feature helps more than the choice of the
  algorithm. LOF fails because many deliveries have exactly the same quantity.
- `patterns.py` discovers column pairs where one value almost always determines the other
  (approximate functional dependencies). Rows that break them are suspicious: a misspelled
  name or a wrong ID. Some learned patterns are only "usually true" (a supplier mostly
  delivers one category), so their violations are often correct data.
- `duplicates.py`: probabilistic record linkage. The exact rule "same store, product, date and
  quantity" misses the near duplicates (the second entry has a slightly different quantity) and
  flags some false pairs. Splink combines evidence from several fields. EM alone learns the
  wrong clusters here (duplicates are rare, and clerks work in one store), so two m-values come
  from domain knowledge ("a duplicate has the same store, product, and date") and EM learns
  the rest. The probabilities are low because the model assumes independent fields, but the
  ranking is good: at p ≥ 0.1 it finds all duplicate pairs with high precision.
- `learn_from_repairs.py`: staff corrected some weighed checkout lines in the past (a
  miscalibrated scale, a cashier who keys the wrong product, meat weighed without the tray). A
  gradient-boosting classifier trained on these past repairs ranks new lines for review.
  Checking 5 % of the lines finds most of the lines that need a correction.
