# 01 · Accuracy vs precision of data

**Slides:** *Accuracy vs. Precision (on Data)* · *Data Accuracy and Precision: Impact on ML*
("more data → better models, up to a point; noisy data → less confident models, more data
needed; inaccurate data → misleading models; invest in data quality, not just quantity") ·
*Data Quality vs Quantity*

A marimo notebook. The checkout scales record the banana sales that the forecasting model
learns from. The scales are (a) correct, (b) imprecise (random noise per reading),
(c) inaccurate (they read 10 % too low; the book's example), or (d) both. The model trains on
the recorded sales of 2024 and is scored against the true expected demand of 2025.

```sh
uv run marimo edit accuracy_precision.py   # interactive, with sliders for noise and bias
uv run marimo export html accuracy_precision.py -o out/accuracy_precision.html  # static run
```

What to look for:
- The scatter plots are the "target" picture in data: noise spreads the points around the
  diagonal, a miscalibrated scale moves all points below it.
- Learning curves: with more training days the error of the imprecise data goes down toward
  the clean data. The error of the inaccurate data stays at the level of the bias, and the
  mean error shows the model predicts too little.
- A better (more complex) model does not help with little, noisy data; here the simple
  linear model is better than gradient boosting.
- Quantile intervals: noisy data gives wide intervals that contain the true value about as
  often as they should; biased data gives narrower intervals in the wrong place.
