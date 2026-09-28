# 01 · Accuracy vs precision of data

**Slides:** *Accuracy vs. Precision (on Data)* · *Data Accuracy and Precision: Impact on ML* ·
*Data Quality vs Quantity*

The checkout scales record the banana sales, and the forecasting model learns from these
records. The notebook compares four versions of the same training data (2024): **clean**,
**imprecise** (random noise on each reading), **inaccurate** (the scales read 10 % too low),
and **both**. It scores each model against the true expected demand of 2025.

## What this project illustrates

| Point | Where to see it in `accuracy_precision.ipynb` |
|---|---|
| Accuracy vs precision (the "target" picture) | Scatter plots of recorded vs true kg: noise spreads the points around the diagonal; the miscalibrated scale moves all points below it. |
| More data → better models, up to a point | Learning curves: the error goes down with more training days, and then flattens. |
| Noisy data → more data needed | The error of the imprecise data goes down toward the clean data as the number of days increases. |
| Inaccurate data → misleading models | The error of the inaccurate data stays at the level of the bias; the mean error is negative (the model predicts too little). |
| Noisy data → less confident models | Quantile intervals: noisy data gives wide intervals that contain the true value about as often as they should. |
| Inaccurate data → confident but wrong | Biased data gives narrow intervals in the wrong place. |
| Invest in data quality, not only in quantity or in the model | With little, noisy data, a simple linear model is better than gradient boosting. |

## Run

Open `accuracy_precision.ipynb` on GitHub to see the outputs. To change the noise and the
bias (parameter cell at the top) and run it again:

```sh
uv run jupyter lab accuracy_precision.ipynb
```
