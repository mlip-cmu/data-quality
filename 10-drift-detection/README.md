# 10 · Detecting drift

A supermarket chain trains a sales forecast on 2024. In 2025 the world changes, on known dates
([drift scenario](../inventory-data/)): a fad diet and a competitor change the demand
(concept drift), new stores and a heatwave change the inputs (data drift), the POS systems of
two stores switch to lb and the weather API switches to °F (schema drift), and the scales of
one store slowly read higher (sensor drift).

**Problem.** A model is trained on the past, but it is used on a world that changes. The
changes are not announced, and they can be sudden or gradual, global or in one store only.

**Idea.** Monitor the data and the model in production, and compare them with a reference:

- compare the distribution of the inputs of each week with the same weeks of the last year;
- when the true sales arrive a day later, monitor the ratio of actual to predicted sales as a
  stream, with a change detector;
- use detectors that add up small deviations (CUSUM) to find gradual drift;
- use validation rules to find schema drift at once.

A change detector on the stream of actual/predicted sales, for each store and product
(`drift_detection.ipynb`, section 2):

```python
ph = drift.PageHinkley(min_instances=14, delta=1.0, threshold=40, mode="both")
for day, r in zip(s.date, s.ratio, strict=True):
    ph.update((r - 1) / max(sd, 0.02))
    if ph.drift_detected:
        alarms.append({"stream": f"{key.removesuffix('_id')} {value}", "date": day, ...})
```

CUSUM adds up the deviations that are larger than a slack `k = 0.5`, so a small, persistent
shift grows until it crosses the threshold (section 4):

```python
for i in range(1, len(z)):
    cusum[i] = max(0.0, cusum[i - 1] + z[i] - 0.5)
```

## What the code shows (`drift_detection.ipynb`)

1. **Data drift:** the KS statistic and the PSI of each week find the heatwave, the new stores,
   and the °F values. Year-to-year weather differences also cause alarms, and with thousands of
   rows a t-test is "significant" in almost every week: look at the size of the change. The lb
   switch in two stores is almost invisible in the distribution of all sales.
2. **Model degradation:** Page-Hinkley finds the fad diet, the competitor, and the lb switch
   within 4 to 11 days.
3. **Concept drift:** a heatmap of actual/predicted by store and month, and a before/after
   table: similar inputs, different outputs.
4. **Gradual drift:** CUSUM finds the drifting scale 10 days before a 3-sigma rule.
5. **Schema drift:** a range check on `temp_c` finds the °F values on the first day.
6. **Summary:** the detection delay for each event, and the total number of alarms (not every
   alarm is an event).

`evidently_reports.py` makes HTML reports with drift and performance tests for three months
of 2025 vs the same months of 2024 (`out/drift_*.html`).

## Tools

- [SciPy](https://scipy.org): scientific computing for Python. Here: the KS test and the
  t-test (`scipy.stats`).
- [river](https://riverml.xyz): machine learning on data streams, one record at a time. Here:
  the Page-Hinkley change detector (`river.drift`).
- [Evidently](https://github.com/evidentlyai/evidently): open-source reports, tests, and
  dashboards to monitor data and ML models. Here: a data drift preset and tests for the error.
- [scikit-learn](https://scikit-learn.org): the forecast model (gradient boosting, in
  `inventory_data.forecast`).
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
- [Altair](https://altair-viz.github.io): declarative charts, saved as PNG with
  [vl-convert](https://github.com/vega/vl-convert).
- [Jupyter](https://jupyter.org) (JupyterLab, nbconvert): the notebook, committed with its
  outputs.

## Run

Open `drift_detection.ipynb` on GitHub to see the outputs. To run it again, with
[uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab drift_detection.ipynb
uv run evidently_reports.py   # Evidently reports and tests -> out/drift_*.html
```
