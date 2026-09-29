# 01 · Accuracy vs precision of data

A supermarket chain forecasts the banana sales of each store from the sales that the checkout
scales record ([dataset](../inventory-data/)).

**Problem.** Measurements can be *imprecise* (random noise: each reading is a bit off, in
either direction) or *inaccurate* (systematic bias: a miscalibrated scale always reads too
low). Both make the training data worse, but in different ways.

**Idea.** Train the same model on clean, imprecise, inaccurate, and both kinds of data, and
compare the models with the true demand. More data averages out noise, but not bias. Noise
makes a model less confident; bias makes it confident and wrong.

The notebook makes the four versions of the training data from the same recorded sales.
Imprecise data gets zero-mean random noise on each reading; inaccurate data is lower by a
fixed factor:

```python
eps = rng.normal(0, 1, len(train))
s, b = NOISE / 100, BIAS / 100
recorded = {
    "clean": train.sales.to_numpy(),
    "imprecise": np.maximum(train.sales * (1 + s * eps), 0).to_numpy(),
    "inaccurate": (train.sales * (1 - b)).to_numpy(),
    "both": np.maximum(train.sales * (1 - b) * (1 + s * eps), 0).to_numpy(),
}
```

Each model is scored against the true expected demand, not against the recorded data, so
the mean error shows the bias that the model learned:

```python
err = pred - test.expected_demand
return float(np.mean(np.abs(err))), float(np.mean(err))  # MAE, mean error
```

## What the code shows (`accuracy_precision.ipynb`)

- Scatter plots of recorded vs true sales: noise spreads the points around the diagonal; bias
  moves all points below it.
- Learning curves: with more training days, the error of the noisy data goes down toward the
  clean data. The error of the biased data stays at the level of the bias, and the model
  predicts too little.
- Prediction intervals: noisy data gives wide intervals that contain the true value about as
  often as they should; biased data gives narrow intervals in the wrong place.
- With little, noisy data, a simple linear model is better than gradient boosting: a better
  model does not fix bad data.

## Tools

- [scikit-learn](https://scikit-learn.org): the standard Python library for classic machine
  learning. Here: the forecast models (`Ridge`, `HistGradientBoostingRegressor`, also with a
  quantile loss for prediction intervals).
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: the training data and the simulated noise and bias.
- [Altair](https://altair-viz.github.io): declarative charts for Python, based on Vega-Lite.
  [vl-convert](https://github.com/vega/vl-convert) saves the charts as PNG images, so that
  GitHub can show them in the notebook.
- [Jupyter](https://jupyter.org) (JupyterLab, nbconvert): notebooks that mix code, text, and
  outputs. The notebook is committed with its outputs.

## Run

Open `accuracy_precision.ipynb` on GitHub to see the outputs. To change the noise and the
bias (parameter cell at the top) and run it again, with [uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab accuracy_precision.ipynb
```
