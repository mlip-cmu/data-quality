# 09 · ML-based detection of data errors

The delivery, product, and checkout data of a supermarket chain contain injected errors, and a
log records each error ([dataset](../inventory-data/)).

**Problem.** Rules (see `08`) find only the errors that someone thought of in advance. Many
errors are plausible values that are unusual only in their context: an 80,000 kg banana
delivery, a product name that does not fit its ID, a delivery that was entered two times with
a slightly different quantity.

**Idea.** Learn what normal data looks like and flag what is unusual: anomaly detection,
learned dependencies between columns, probabilistic matching of near-duplicate records, and a
classifier trained on past repairs. The result is a ranked list of *suspicious* records for a
human to review, not a list of certain errors.

The anomaly detector gets the context of each delivery as a feature: the deviation from the
median quantity of the same product in the same store (`anomalies.py`):

```python
signed_log = np.sign(dl.quantity) * np.log1p(dl.quantity.abs())
typical = signed_log.groupby([dl.store_id, dl.product_id]).transform("median")
X = pd.DataFrame({"log_quantity": signed_log, "deviation_from_typical": signed_log - typical})
scores = -IsolationForest(random_state=0).fit(X).score_samples(X)
```

The record linkage model compares pairs field by field (`duplicates.py`). Where the data
cannot teach the model what a duplicate looks like, the probabilities come from domain
knowledge ("a duplicate has the same store, product, and date"):

```python
comparisons=[
    cl.ExactMatch("store_id").configure(m_probabilities=[0.999, 0.001]),
    cl.ExactMatch("product_id").configure(m_probabilities=[0.999, 0.001]),
    cl.AbsoluteDateDifferenceAtThresholds("delivery_date", ...).configure(...),
    cl.CustomComparison([... cll.PercentageDifferenceLevel("quantity", 0.15), ...]),
    cl.ExactMatch("unit"),
],
```

## What the code shows

Each script compares its detector with the injected errors and prints the most suspicious
records.

- `anomalies.py`: four anomaly detectors on delivery quantities. One contextual feature (the
  deviation from the usual quantity of this product in this store) helps more than a different
  algorithm. LOF fails because many deliveries have the same quantity.
- `patterns.py`: finds column pairs where one value almost always sets the other (for example,
  product ID → name). Rows that break them are suspicious. Some patterns are only "usually
  true" (a supplier mostly delivers one category), so many of their violations are correct.
- `duplicates.py`: the exact rule "same store, product, date, and quantity" misses near
  duplicates and flags false pairs. Probabilistic record linkage combines the evidence of
  several fields; at p ≥ 0.1 it finds all duplicate pairs with high precision. Unsupervised
  training alone learns the wrong clusters; fixed probabilities for three fields fix this.
- `learn_from_repairs.py`: a classifier trained on past corrections of weighed checkout lines
  ranks new lines for review. A review of 5 % of the lines finds most lines that need a
  correction.

## Tools

- [scikit-learn](https://scikit-learn.org): classic machine learning. Here: `IsolationForest`
  and `LocalOutlierFactor` (anomaly detection) and a gradient-boosting classifier.
- [PyOD](https://pyod.readthedocs.io): a library of many outlier detection algorithms with one
  API. Here: ECOD, a fast detector without parameters.
- [Splink](https://moj-analytical-services.github.io/splink/): probabilistic record linkage
  and deduplication (Fellegi-Sunter model), here on DuckDB.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames, arrays, and
  the features.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run anomalies.py           # unusual delivery quantities
uv run patterns.py            # learned dependencies and their violations
uv run duplicates.py          # near-duplicate delivery records
uv run learn_from_repairs.py  # predict which checkout lines staff will correct
```
