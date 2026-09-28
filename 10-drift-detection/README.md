# 10 · Detecting drift

**Slides:** *Dealing with Drift* · *Types of Drift* (concept, data, schema drift) · *Indicators
of Concept Drift* · *Indicators of Data Drift* · *Detecting Data Drift* ("compare distributions
over time (e.g., t-test); detect both sudden jumps and gradual changes") · *Drift Detection
Tools* (Evidently AI, NannyML, Alibi Detect, …)

The forecasting model (`inventory_data.forecast`) is trained on 2024. In 2025 the drift
scenario of the dataset changes the world: a fad diet (concept drift), a competitor (concept
drift), new stores in Florida and a heatwave (data drift), POS weights in lb and the weather
API in °F (schema drift), and slowly drifting checkout scales (sensor drift).

```sh
uv run marimo edit drift_detection.py   # build-your-own detectors, with charts
uv run evidently_reports.py             # Evidently reports + tests -> out/drift_*.html
```

`drift_detection.py`, what to look for:
1. **Data drift**: compare the inputs of each week with the *same weeks of the last year*
   (a whole-year reference would report drift every summer). Year-to-year weather
   differences cause alarms without an event, and with thousands of rows every t-test is
   "significant": look at the size of the difference, not the p-value. The lb switch in two
   stores is almost invisible in the distribution of all sales.
2. **Model degradation in telemetry**: the actual sales arrive a day later. Page-Hinkley (river)
   on the ratio actual/predicted per store and per product finds the fad diet, the competitor,
   and the lb switch within days.
3. **Concept drift indicator**: "different outputs for similar inputs" in a heatmap of
   actual/predicted by store and month, and a table of before/after ratios.
4. **Gradual drift**: CUSUM finds the drifting scale 10 days before a 3-sigma rule.
5. **Schema drift**: a simple range check on `temp_c` finds the °F change on the first day.

`evidently_reports.py` compares three months of 2025 with the same months of 2024 using
Evidently's data drift preset and explicit performance tests (MAE, mean error). Note: the
automatic performance tests of the regression preset compare with the error on the *reference*
data; here the reference is the training data, so they always fail. Use explicit thresholds or
a held-out reference. NannyML (performance estimation without labels) is not included: its
last release does not support Python 3.13. Alibi Detect now has a Business Source License.
