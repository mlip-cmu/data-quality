# 11 · Dealing with drift

**Slides:** *Dealing with Drift* ("regularly retrain model on recent data; use evaluation in
production to detect decaying model performance; involve humans when increasing
inconsistencies are detected; monitoring thresholds, automation") · *Microsoft Azure Data Drift
Dashboard* (here: the open-source Evidently UI) · *Models often Degrade over Time*

```sh
uv run marimo edit retraining.py   # backtest of retraining strategies (takes about a minute)
uv run monitor.py                  # 52 weekly monitoring runs + alerts
uv run evidently ui --workspace out/workspace --port 8000   # then open http://localhost:8000
```

`retraining.py` forecasts every day of 2025 with five strategies: a static 2024 model,
monthly retraining on all data, monthly retraining on the last 90 days, retraining when a
Page-Hinkley detector alarms, and "repair the data (lb → kg, °F → °C), then retrain monthly".
The forecasts are scored against the true sales in catalog units. What to look for:
- Regular retraining on recent data follows the concept drift (fad diet, competitor).
- Retraining does not fix schema drift: after the POS update the model learns the wrong
  units. Only the strategy that repairs the data stays good in September to December.
- The alarm-triggered model retrained on the corrupted data and became the worst model. An
  alarm should make a human look for the root cause.

`monitor.py` is the monitoring job of the forecasting team. Every week it compares the inputs
and the errors with the same weeks of the last year (Evidently metrics), stores a snapshot in
a local Evidently workspace, and checks the thresholds in `thresholds.yaml`. Each alert goes to
the owner of the check (`out/alerts.jsonl`): the weather API team for impossible temperatures,
the forecasting team for the error. The dashboard shows the four monitored values over time.
