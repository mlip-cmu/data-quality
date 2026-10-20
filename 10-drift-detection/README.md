# 10 · Detecting drift

**Slides:** *Dealing with Drift* · *Types of Drift* · *Indicators of Concept Drift* ·
*Indicators of Data Drift* · *Detecting Data Drift* · *Drift Detection Tools*

The supermarket chain forecasts daily sales per store and product with a model
(`inventory_data.forecast`, see [dataset](../inventory-data/)) that is trained on 2024. The drift
scenario of the dataset changes the world in 2025 with seven documented events
(`inventory_data.drift_events()`). This folder has a notebook that tries to find these events
without using the list, and a script that builds the same kind of checks with Evidently.

**Problem.** The world changes after deployment. The inputs change (data drift), the relation
between inputs and the target changes (concept drift), or the format of the data changes (schema
drift). The model gives no error message; its forecasts slowly get worse, and nobody notices
until the orders are wrong.

**Idea.** Monitor the inputs and the model. Compare the distribution of recent inputs with a
reference window of the same season, and use the size of the difference as the signal. Track the
error of the model once the actual sales arrive, with detectors that find sudden and gradual
changes. Validate the schema and the value ranges of every new batch.

The notebook (`drift_detection.ipynb`) runs one Page-Hinkley detector per store and per product
on the daily ratio actual/predicted, scaled by the standard deviation in 2024:

```python
for value, s in streams(live, key).groupby(key):
    sd = ref_ratio.get(value, s.ratio.std())
    ph = drift.PageHinkley(min_instances=14, delta=1.0, threshold=40, mode="both")
    for day, r in zip(s.date, s.ratio, strict=True):
        ph.update((r - 1) / max(sd, 0.02))
        if ph.drift_detected:
            alarms.append(...)
```

## What the notebook shows

Open `drift_detection.ipynb` on GitHub to see the outputs.

1. **Types of drift.** The first table lists the seven true events and their kind: a fad diet
   doubles the demand for cucumbers and a competitor opens next to store 3 (concept drift); two
   new stores open in Florida and a heatwave adds 8 °C (data drift); the POS terminals of stores
   7 and 8 record weights in lb and the weather API reports °F in the column `temp_c` (schema
   drift); the checkout scales of store 2 read a bit higher every day (sensor drift).
2. **Data drift: compare distributions** (section 1). Each week of 2025 is compared with the
   same weeks of 2024 (± 2 weeks). The reference is the same season, because the temperature is
   seasonal and a reference of the whole year would report drift every summer. The mean
   temperature rises by about 6.5 °C in the heatwave and by 35 to 45 °C after the °F switch.
   The store mix (PSI) jumps from near 0 to about 1.4 when the Florida stores open (alarm
   threshold 0.2).
3. **A significant change can be tiny** (section 1, last table). With thousands of rows,
   a t-test gives a tiny p-value in every week, also in a normal week with a change of −0.7 °C
   (p = 2.5e-29).
4. **A local change is diluted** (section 1). The KS statistic of all sales quantities stays
   below 0.1 all year: the lb switch in two stores is almost invisible in the global
   distribution.
5. **Decaying performance in telemetry** (section 2). Page-Hinkley alarms on the streams of
   product 102 (cucumbers) 4 days after the fad diet, store 3 after 8 days, and stores 7 and 8
   (lb) after 10 and 11 days.
6. **Different outputs for similar inputs** (section 3). A heatmap shows actual/predicted by
   store and month. For days without a promotion, actual/predicted moves from 1.00 to 2.09 for
   cucumbers and from 1.08 to 0.76 for store 3: the same inputs now lead to different sales.
7. **Gradual changes** (section 4). For the drifting scale in store 2, CUSUM adds up small
   deviations and alarms 16 days after the start; a 3-sigma rule alarms after 26 days.
8. **Schema drift found by validation** (section 5). A range check (−30 to 45 °C) on `temp_c`
   fails on 2025-10-15, the first day of the °F switch.
9. **Detection delay and false alarms** (summary). The table lists the delay for each event
   (0 to 16 days). Page-Hinkley raised 21 alarms on 20 streams. Besides the 4 event streams,
   16 products alarm between September 16 and December 19: 11 products sold by kg (probably
   the lb switch) and 5 products sold by count, such as ice cream, iced tea, and watermelon
   (probably the °F switch). A lower threshold finds the events earlier, with more alarms.

`evidently_reports.py` compares three months of 2025 with the same months of 2024. It runs the
Evidently data drift preset and two performance tests (mean absolute error ≤ 3.3, mean error
between −0.3 and 0.3), and writes `out/drift_*.html`:

10. **Drift detection tools.** 2025-03: 9 of 12 tests pass (the temperature drifts; MAE and
    mean error fail). 2025-06 and 2025-11: 7 of 12 pass; the quantity and the store mix fail
    too.

## Tools

- [SciPy](https://scipy.org): scientific computing in Python. Here: the two-sample
  Kolmogorov-Smirnov (KS) test and the t-test in `scipy.stats`.
- [river](https://riverml.xyz): machine learning on data streams. Here: the Page-Hinkley drift
  detector on the error streams.
- [Evidently](https://www.evidentlyai.com): an open-source library to evaluate and monitor ML
  models and data. Here: drift reports and tests as HTML files.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: the weekly windows, PSI (population stability index), and CUSUM, written by hand.
- [scikit-learn](https://scikit-learn.org): machine learning in Python. Here: the gradient
  boosting model behind `inventory_data.forecast`.
- [Altair](https://altair-viz.github.io) with
  [vl-convert](https://github.com/vega/vl-convert): declarative charts, as PNG images. Here:
  the drift scores, the error over time, and the heatmap.
- [Jupyter](https://jupyter.org): notebooks with code and outputs.

## Run

Open `drift_detection.ipynb` on GitHub to see the outputs. To run it again, with
[uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab drift_detection.ipynb
uv run evidently_reports.py   # Evidently reports and tests -> out/drift_*.html
```
