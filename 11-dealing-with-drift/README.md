# 11 · Dealing with drift

**Slides:** *Dealing with Drift* · *Microsoft Azure Data Drift Dashboard* · *Models often
Degrade over Time*

The supermarket chain forecasts daily sales per store and product with a model trained on 2024
(`inventory_data.forecast`, see [dataset](../inventory-data/)). In 2025 the same drift events as
in [10](../10-drift-detection/) happen: a fad diet, a competitor, POS weights in lb in stores 7
and 8, and the weather API in °F. This folder has a notebook that compares five retraining
strategies over 2025, and a weekly monitoring job with alert thresholds and a dashboard.

**Problem.** Models degrade over time, because the world changes after training. Retraining
helps with some changes and hurts with others: a model that retrains on corrupted data learns the
corruption. A drift detector alone does not fix anything; someone must look at the alarm and act.

**Idea.** Retrain regularly on recent data, so that the model follows concept drift. Repair data
errors before retraining. Monitor inputs and errors every week against thresholds, and send each
alert to the team that owns the problem. Use alarms to involve humans, and keep a dashboard of
the monitored values over time.

The notebook (`retraining.ipynb`) forecasts each day of 2025 with the model that each strategy
has on that day. The strategy "repair the data" converts lb to kg and °F to °C first:

```python
repaired = data.assign(
    quantity=np.where(lb, data.quantity / 2.20462, data.quantity),
    temp_c=np.where(fahrenheit, (data.temp_c - 32) * 5 / 9, data.temp_c),
)
```

## What the code shows

`retraining.ipynb` scores the forecasts of 16 products against the true sales (WAPE, the
weighted absolute percentage error; lower is better). Open it on GitHub to see the outputs.

| strategy | WAPE Jan-Aug | WAPE Sep-Dec | retrains |
|---|---|---|---|
| static (2024 model) | 0.330 | 0.346 | 0 |
| retrain monthly, all data | 0.319 | 0.307 | 11 |
| retrain monthly, last 90 days | 0.273 | 0.334 | 11 |
| retrain on a drift alarm, last 90 days | 0.323 | 0.431 | 8 |
| repair the data, retrain monthly (90 days) | 0.273 | 0.291 | 11 |

1. **Models degrade over time.** The static 2024 model has the highest error in January to
   August (0.330); it keeps the old concept (no fad diet, no competitor).
2. **Retrain regularly on recent data.** Monthly retraining on the last 90 days lowers the error
   to 0.273 in January to August. The 90-day window forgets the old concept faster than a model
   on all data (0.319).
3. **Retraining does not fix schema drift.** After the POS update to lb, the 90-day model learns
   that stores 7 and 8 sell 2.2 times more: its error rises to 0.334 in September to December.
   The model on all data suffers less (0.307), because the bad months are a small part of its
   training data. The strategy that repairs the data first has the lowest error (0.291).
4. **Involve humans when a detector alarms.** The model that retrains on each Page-Hinkley alarm
   (8 retrains) learns from the corrupted lb data and becomes the worst model (0.431).

`monitor.py` runs a weekly monitoring job for each of the 52 weeks of 2025. It compares the week
with the same weeks of 2024 (± 2 weeks) and checks four values against `thresholds.yaml`:

```yaml
- metric: temperatures out of range (-30..45 °C)
  max: 0
  owner: data engineering (weather API)
- metric: MAE (kg or count)
  max: 4.0
  owner: forecasting team
```

5. **Evaluation in production, thresholds, automation.** The job stores 52 Evidently snapshots
   in `out/workspace` and writes 76 alerts to `out/alerts.jsonl`: the share of drifted input
   columns exceeds 0.2 in 32 weeks (first on 2025-03-10), the mean absolute error (MAE) exceeds
   4.0 in 22 weeks (from 2025-05-19), and the mean error is outside ±0.8 in 11 weeks (first on
   2025-01-27, after the fad diet).
6. **Alerts go to the owner of the problem.** The 11 weeks with impossible temperatures (from
   2025-10-13, the week of the °F switch) go to the weather API owner in data engineering; the
   errors go to the forecasting team.
7. **A data drift dashboard.** The Evidently UI shows the four monitored values of the 52 weekly
   runs over time, like the Azure Data Drift Dashboard on the slides.

## Tools

- [Evidently](https://www.evidentlyai.com): an open-source library to evaluate and monitor ML
  models and data, with a web UI. Here: the weekly snapshots (drifted columns, MAE, mean error,
  values out of range), the workspace, and the dashboard.
- [river](https://riverml.xyz): machine learning on data streams. Here: the Page-Hinkley
  detector that triggers the "retrain on a drift alarm" strategy.
- [scikit-learn](https://scikit-learn.org): machine learning in Python. Here: the gradient
  boosting model behind `inventory_data.forecast`.
- [PyYAML](https://pyyaml.org): reads YAML files. Here: the thresholds and owners in
  `thresholds.yaml`.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: the backtest, the data repair, and the monthly errors.
- [Altair](https://altair-viz.github.io) with
  [vl-convert](https://github.com/vega/vl-convert): declarative charts, as PNG images. Here:
  the monthly error of each strategy.
- [Jupyter](https://jupyter.org): notebooks with code and outputs.

## Run

Open `retraining.ipynb` on GitHub to see the outputs. To run it again (a few minutes), with
[uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab retraining.ipynb
uv run monitor.py                                          # 52 weekly monitoring runs + alerts
uv run evidently ui --workspace out/workspace --port 8000  # then open http://localhost:8000
```
