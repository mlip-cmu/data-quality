# 11 · Dealing with drift

The same sales forecast and the same 2025 drift scenario as in
[`10-drift-detection`](../10-drift-detection/): concept drift (a fad diet, a competitor),
data drift, and schema drift (POS weights in lb, weather in °F).

**Problem.** A model that is not updated gets worse when the world changes. But retraining is
not always the answer: when the data itself is wrong (schema drift), retraining teaches the
model the error.

**Idea.** Retrain regularly on recent data, so that the model follows concept drift. Monitor
the inputs and the errors in production, with explicit thresholds, and send each alert to the
team that owns the problem. A human finds the root cause of an alarm: fix the data first when
the data is wrong, then retrain.

A backtest retrains each strategy at the time it would have in production: every month, or
after a drift alarm, on all data or on the last 90 days (`retraining.ipynb`):

```python
due = (when == "monthly" and day.day == 1 and day > last) or (
    when == "alarm" and detector.drift_detected and (day - last).days >= 14
)
if due:
    start = day - pd.Timedelta(days=window_days) if window_days else history.date.min()
    model = forecast.train(history[history.date >= start], max_iter=100)
```

The monitoring thresholds and the owner of each check are configuration
(`thresholds.yaml`):

```yaml
- metric: temperatures out of range (-30..45 °C)
  max: 0
  owner: data engineering (weather API)
- metric: MAE (kg or count)
  max: 4.0
  owner: forecasting team
```

## What the code shows

- `retraining.ipynb` compares five strategies against the true sales:
  - The static 2024 model has a higher error than a model that is retrained every month on the
    last 90 days (January to August: 0.33 vs 0.27 WAPE).
  - Monthly retraining follows the fad diet and the competitor; a 90-day window forgets the
    old concept faster than a model on all data.
  - After the POS switch to lb, the retrained models learn the wrong units (90-day window: 0.33
    WAPE in September to December). The strategy that repairs the data first (lb → kg,
    °F → °C) has the lowest error.
  - The model that retrains after each drift alarm learns from the corrupted data and becomes
    the worst model.
- `monitor.py` runs the monitoring job for each week of 2025, stores each run in an Evidently
  workspace, and writes the alerts to `out/alerts.jsonl`. The Evidently UI shows the monitored
  values over time as a dashboard.

## Tools

- [Evidently](https://github.com/evidentlyai/evidently): open-source reports, tests, and
  dashboards to monitor data and ML models. Here: the weekly metrics, a local workspace, and
  the dashboard (Evidently UI).
- [river](https://riverml.xyz): machine learning on data streams. Here: the Page-Hinkley drift
  detector that triggers retraining.
- [scikit-learn](https://scikit-learn.org): the forecast model (gradient boosting).
- [PyYAML](https://pyyaml.org): reads the thresholds from `thresholds.yaml`.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
- [Altair](https://altair-viz.github.io): declarative charts, saved as PNG with
  [vl-convert](https://github.com/vega/vl-convert).
- [Jupyter](https://jupyter.org) (JupyterLab, nbconvert): the notebook, committed with its
  outputs.

## Run

Open `retraining.ipynb` on GitHub to see the outputs. To run it again (a few minutes), with
[uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab retraining.ipynb
uv run monitor.py                                          # 52 weekly monitoring runs + alerts
uv run evidently ui --workspace out/workspace --port 8000  # then open http://localhost:8000
```
