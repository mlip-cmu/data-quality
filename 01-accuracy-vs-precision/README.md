# 01 · Accuracy vs precision of data

**Slides:** *Accuracy vs. Precision (on Data)* · *Data Accuracy and Precision: Impact on ML* ·
*Data Quality vs Quantity*

Bananas are sold by weight. The checkout scales record the banana sales of the 8 stores
([dataset](../inventory-data/)), and the forecasting model learns from these records. This
folder has one notebook, `accuracy_precision.ipynb`. It trains on the recorded sales of 2024
(2,928 rows: one per store and day) and scores each model against the true expected demand of
2025 (2,920 rows): the pattern a model should learn, without the day-to-day randomness of the
customers. In 2025, the stores sell 28.3 kg of bananas per day on average.

**Problem.** Measurements are never perfect. A scale can be *imprecise*: each reading has some
random noise. A scale can also be *inaccurate*: it is miscalibrated and reads too low every
time. Both kinds of error go into the training data, and the model learns from them.

**Idea.** Separate the two kinds of error and measure their effect on the model. Random noise
averages out with more data. A systematic bias stays, however much data we collect, and it
makes the model wrong in a consistent direction. So collecting more data helps only with
noise; a bias must be found and fixed in the data itself.

The notebook makes four versions of the same training data, with the parameters `NOISE = 30`
(% noise of each reading) and `BIAS = 10` (% that the scales read too low):

```python
rng = np.random.default_rng(0)
eps = rng.normal(0, 1, len(train))
s, b = NOISE / 100, BIAS / 100
recorded = {
    "clean": train.sales.to_numpy(),
    "imprecise": np.maximum(train.sales * (1 + s * eps), 0).to_numpy(),
    "inaccurate": (train.sales * (1 - b)).to_numpy(),
    "both": np.maximum(train.sales * (1 - b) * (1 + s * eps), 0).to_numpy(),
}
```

The features are the store, the day of the week, the season, a promotion flag, and the
temperature.

## What the notebook shows

Open `accuracy_precision.ipynb` on GitHub to see the outputs.

1. **Accuracy vs precision.** Two scatter plots of recorded vs true kg (store 1, 2024) show the
   "target" picture of the slides: the noise spreads the imprecise points around the diagonal;
   the miscalibrated scale moves all inaccurate points below it.
2. **More data, up to a point.** Learning curves for a gradient boosting model trained on 14 to
   366 days (mean absolute error, MAE, in kg per store and day, averaged over 3 random samples
   of days):

   | days | clean | imprecise | inaccurate | both |
   |---:|---:|---:|---:|---:|
   | 14 | 5.84 | 6.47 | 6.57 | 7.16 |
   | 56 | 3.46 | 4.93 | 4.05 | 5.15 |
   | 366 | 2.59 | 3.23 | 3.93 | 4.37 |

   The error goes down with more days, and then flattens.
3. **Noisy data needs more data.** The error of the imprecise data halves from 6.47 to 3.23 kg
   as the number of days grows. With 366 days of imprecise data, the error is close to the
   error with 112 days of clean data (3.37 kg): more data makes up for the noise.
4. **Inaccurate data gives a misleading model.** The error of the inaccurate data stays at about
   4 kg from 56 days on: more data does not reduce it. With all 366 days, the mean error is
   -3.61 kg for the inaccurate data and -0.88 kg for the clean data. The difference, 2.7 kg, is
   about 10 % of the 28.3 kg: the model predicts too little, by the size of the bias.
5. **A simpler model on noisy data.** On the imprecise data, a linear model (Ridge) has a lower
   error than gradient boosting at every size: 5.34 vs 6.47 kg with 14 days, 1.65 vs 3.23 kg
   with 366 days. A more complex model does not fix bad data. Invest in data quality, as well
   as in more data or a better model.
6. **Noisy data gives a less confident model.** Quantile models predict an 80 % interval for
   each day of 2025. With the imprecise data, the intervals are wide (23.62 kg on average) and
   contain the true sales on 82 % of the days, about as often as they should.
7. **Inaccurate data gives a confident but wrong model.** With the inaccurate data, the
   intervals are narrow (14.52 kg) and in the wrong place: they contain the true sales on
   only 60 % of the days.

## Tools

- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: join the sales, the weather, and the true demand; add the noise and the bias.
- [scikit-learn](https://scikit-learn.org): a library of classic ML models. Here:
  `HistGradientBoostingRegressor` (gradient boosting, also with a quantile loss for the
  intervals) and `Ridge` (a linear model).
- [Altair](https://altair-viz.github.io) with
  [vl-convert](https://github.com/vega/vl-convert): declarative charts, as PNG images. Here:
  the scatter plots, the learning curves, and the intervals.
- [Jupyter](https://jupyter.org): notebooks with code and outputs.
- [`inventory_data`](../inventory-data/): the shared dataset of this repository. Here: the
  sales, the weather, and the true expected demand of the bananas (product 101).

## Run

Open `accuracy_precision.ipynb` on GitHub to see the outputs. To change `NOISE` and `BIAS`
(parameter cell at the top) and run it again, with [uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab accuracy_precision.ipynb
```
