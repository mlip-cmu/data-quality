# 11 · Dealing with drift

**Slides:** *Dealing with Drift* · *Microsoft Azure Data Drift Dashboard* · *Models often
Degrade over Time*

## What this project illustrates

| Point | Where to see it |
|---|---|
| Models degrade over time | `retraining.ipynb`: the static 2024 model has a higher error than a model that is retrained every month on the last 90 days (January to August: 0.33 vs 0.27 WAPE). |
| Regularly retrain the model on recent data | `retraining.ipynb`: monthly retraining follows the concept drift (fad diet, competitor); a 90-day window forgets the old concept faster than a model on all data. |
| Retraining does not fix schema drift | `retraining.ipynb`: after the POS update to lb, the retrained models learn the wrong units (90-day window: 0.27 WAPE in January to August, 0.33 in September to December). The strategy that repairs the data first (lb → kg, °F → °C) has the lowest error in September to December. |
| Involve humans when a detector alarms | `retraining.ipynb`: the model that retrains on each drift alarm learns from the corrupted lb data and becomes the worst model. |
| Evaluation in production, monitoring thresholds, automation | `monitor.py`: a weekly monitoring job compares inputs and errors with the same weeks of the last year (Evidently metrics) and checks the thresholds in `thresholds.yaml`. |
| Alerts go to the owner of the problem | `monitor.py` → `out/alerts.jsonl`: the weather API team gets the impossible temperatures, the forecasting team gets the error. |
| A data drift dashboard (Azure Data Drift Dashboard) | The Evidently UI shows the four monitored values of the 52 weekly runs over time. |

## Run

Open `retraining.ipynb` on GitHub to see the outputs. To run it again (a few minutes):

```sh
uv run jupyter lab retraining.ipynb
uv run monitor.py                                          # 52 weekly monitoring runs + alerts
uv run evidently ui --workspace out/workspace --port 8000  # then open http://localhost:8000
```
