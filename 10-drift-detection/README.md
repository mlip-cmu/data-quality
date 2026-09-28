# 10 · Detecting drift

**Slides:** *Dealing with Drift* · *Types of Drift* · *Indicators of Concept Drift* ·
*Indicators of Data Drift* · *Detecting Data Drift* · *Drift Detection Tools*

The forecasting model (`inventory_data.forecast`) is trained on 2024. In 2025 the drift
scenario of the dataset changes the world: a fad diet and a competitor (concept drift), new
stores in Florida and a heatwave (data drift), POS weights in lb and the weather API in °F
(schema drift), and slowly drifting checkout scales (sensor drift).

## What this project illustrates

| Point | Where to see it |
|---|---|
| Types of drift: concept, data, schema | `drift_detection.ipynb`, first table: the seven true events and their kind. |
| Detect data drift: compare distributions over time | Section 1: each week of inputs vs the same weeks of the last year (KS statistic, PSI). The heatwave, the new stores, and the °F values stand out. |
| Choose the reference data carefully | Section 1: the reference is the same season of last year; a reference of the whole year reports drift every summer. |
| Statistical significance is not the size of a change | Section 1, last table: with thousands of rows, the t-test is "significant" in almost every week. |
| A local change is diluted in global statistics | Section 1: the lb switch in two stores is almost invisible in the distribution of all sales. |
| Indicator: decaying model performance in telemetry | Section 2: Page-Hinkley (river) on the ratio actual/predicted of each store and product finds the fad diet, the competitor, and the lb switch within 4 to 11 days. |
| Indicator of concept drift: different outputs for similar inputs | Section 3: heatmap of actual/predicted by store and month, and a before/after table for cucumbers and store 3. |
| Detect gradual changes, not only sudden jumps | Section 4: CUSUM finds the drifting scale 10 days before a 3-sigma rule. |
| Schema drift is found by validation | Section 5: a range check on `temp_c` finds the °F change on the first day. |
| Detection delay and false alarms | Summary table: the delay for each event, and the total number of alarms. |
| Drift detection tools | `evidently_reports.py`: Evidently data drift preset and performance tests (MAE, mean error) for three months of 2025 vs the same months of 2024 → `out/drift_*.html`. |

## Run

Open `drift_detection.ipynb` on GitHub to see the outputs. To run it again:

```sh
uv run jupyter lab drift_detection.ipynb
uv run evidently_reports.py   # Evidently reports and tests -> out/drift_*.html
```
