# 09 · ML-based detection of data errors

**Slides:** *Detecting Inconsistencies* · *ML-based for Detecting Inconsistencies* · *Not many
standard tools, often custom data sciency solutions*

The supermarket chain records every delivery and every checkout line
([dataset](../inventory-data/)). The dirty copy of the data has injected errors, and
`inventory_data.errors()` lists each one (the ground truth). This folder has four scripts. Each
one fits a model of normal data, scores the records, compares the scores with the ground truth,
and prints the most suspicious records for a human to check.

**Problem.** Many errors break no schema and no hand-written rule: a delivery of 40,000 kg of
onions, a product name that belongs to another product ID, the same delivery entered twice with a
slightly different quantity. Nobody can write a rule for every case, and there are few standard
tools for this.

**Idea.** Learn the patterns from the data itself and flag the records that do not fit:
outliers (anomaly detection), rows that break a column dependency that almost always holds,
pairs of records that are probably the same (record linkage), and lines that look like the lines
that staff had to correct in the past. A flag marks a record as suspicious; a human checks it.
Context and domain knowledge often help more than the choice of the algorithm.

The contextual feature in `anomalies.py` is the distance of a delivery quantity (on a log scale)
from the median quantity of the same product in the same store:

```python
signed_log = np.sign(dl.quantity) * np.log1p(dl.quantity.abs())
typical = signed_log.groupby([dl.store_id, dl.product_id]).transform("median")
...
    "in context": pd.DataFrame(
        {"log_quantity": signed_log, "deviation_from_typical": signed_log - typical}
    ),
```

## What the code shows

1. **Anomaly detection** (`anomalies.py`). 198,815 deliveries, 495 with an injected quantity
   error (outlier, wrong unit, negative). Four detectors score each delivery; the table gives
   the share of true errors among the 495 highest scores:
   - with the raw features (quantity, product, weekday): IsolationForest 0.61, ECOD 0.56,
     LocalOutlierFactor (LOF) 0.23;
   - with the contextual feature: IsolationForest 0.82, ECOD 0.82, a robust z-score per store
     and product 0.71.

   The 8 highest-ranked deliveries are all true errors (for example 40,000 kg of yellow
   onions); the 80,000 kg banana delivery is rank 24.
2. **Context matters more than the algorithm** (`anomalies.py`). One contextual feature raises
   the precision of IsolationForest from 0.61 to 0.82; a different algorithm with the raw
   features does not come close. LOF drops to 0.004 with the context: many deliveries have
   exactly the same quantity, and LOF compares the density around each point with the density
   around its neighbors.
3. **Learning common patterns** (`patterns.py`). The script tests every pair of 9 columns and
   keeps 12 approximate functional dependencies A → B: in 98.7 to 99.9 % of the rows, B has the
   most frequent value for the value of A (for example `product_id` → `product_name`,
   99.51 %; the script skips dependencies that hold in 100 % of the rows). The 977 rows that
   break `product_id` → `product_name` contain 585 injected misspellings ("Atlanic Salmon")
   and 392 wrong product IDs. A flagged row shows only that the ID and the name disagree; the
   cause may be a typo in the name or a wrong ID.
4. **Suspicious data, often correct** (`patterns.py`). Some learned patterns are only
   usually true: `supplier_id` → `category` holds in 98.69 % of the rows, because a supplier
   mostly delivers one category (the seafood supplier also sells frozen shrimp). Many rows
   that break such a pattern are correct.
5. **Near-duplicate detection** (`duplicates.py`). 22,573 deliveries in the first quarter of
   2025, with 108 injected duplicate pairs. The exact rule "same store, product, date, and
   quantity" finds 74 pairs: 69 true pairs (recall 0.64) and 5 false ones. It misses every
   near duplicate, for example quantity 12.0 and 10.8 on the same day. Splink combines the
   evidence of several fields into a match probability and ranks the pairs:

   | match probability | pairs found | true duplicates | precision | recall |
   |---|---|---|---|---|
   | ≥ 0.01 | 307 | 108 | 0.35 | 1.00 |
   | ≥ 0.1 | 113 | 108 | 0.96 | 1.00 |
   | ≥ 0.3 | 39 | 39 | 1.00 | 0.36 |

6. **Domain knowledge in a learned model** (`duplicates.py`). The expectation-maximization
   (EM) step of Splink estimates how often duplicates agree on each field. The script fixes
   these values (m-probabilities) for store, product, and date from domain knowledge: a
   duplicate has the same store, product, and date.
7. **Learning from past repairs** (`learn_from_repairs.py`). Staff correct some weighed
   checkout lines (column `was_corrected`). A gradient-boosting classifier trains on the
   14,329 lines of March 1-20 (673 corrections) and ranks the 7,210 lines of March 21-30
   (ROC AUC 0.948). A review of the top 5 % (360 lines) finds 351 of the 480 lines that need a
   correction (precision 98 %; base rate 6.7 %). The most important features are the
   terminal and the store. These features match the causes of the past repairs: scale errors
   (418 corrections, most often at terminal T3 in store 2), weights without tare (177), and
   wrong product codes (78).

## Tools

- [scikit-learn](https://scikit-learn.org): machine learning in Python. Here:
  `IsolationForest` and `LocalOutlierFactor` for anomaly detection, a
  `HistGradientBoostingClassifier` for past repairs, and the metrics (average precision,
  ROC AUC, permutation importance).
- [PyOD](https://pyod.readthedocs.io): a library of outlier detection algorithms. Here: ECOD,
  which scores a point by how far it lies in the tails of each feature distribution.
- [Splink](https://moj-analytical-services.github.io/splink/): probabilistic record linkage
  (the Fellegi-Sunter model) that runs on SQL engines. Here: it compares candidate pairs of
  deliveries in [DuckDB](https://duckdb.org) and estimates a match probability per pair.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: features, the learned dependencies, and the result tables.
- `inventory_data` ([dataset](../inventory-data/)): loads the dirty data and the ground truth
  of the injected errors.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run anomalies.py           # unusual delivery quantities
uv run patterns.py            # learned dependencies and their violations
uv run duplicates.py          # near-duplicate delivery records with Splink
uv run learn_from_repairs.py  # predict which checkout lines staff will correct
```
