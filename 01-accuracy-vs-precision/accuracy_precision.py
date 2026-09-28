import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge

    import inventory_data as d
    from inventory_data import viz

    viz.enable()
    return HistGradientBoostingRegressor, Ridge, alt, d, mo, np, pd


@app.cell
def _(mo):
    mo.md("""
    # Accuracy vs precision of data

    Bananas are sold by weight. The checkout scales record the sales, and the forecasting model
    learns from these records. What if the scales are **imprecise** (random noise) or
    **inaccurate** (miscalibrated: they read too low)? We train on the *recorded* sales of 2024
    and score the model against the *true* expected demand of 2025 (the pattern the model should
    learn, without the day-to-day randomness of customers).
    """)
    return


@app.cell
def _(d, np, pd):
    truth = d.truth().query("product_id == 101")
    sales = d.sales().query("product_id == 101")[["date", "store_id", "promo"]]
    weather = d.weather().merge(d.stores()[["id", "station"]].rename(columns={"id": "store_id"}),
                                on="station")
    bananas = (truth.merge(sales, on=["date", "store_id"])
               .merge(weather[["date", "store_id", "temp_c"]], on=["date", "store_id"]))
    doy = bananas.date.dt.dayofyear
    bananas = bananas.assign(dow=bananas.date.dt.dayofweek, season_sin=np.sin(2 * np.pi * doy / 365),
                             season_cos=np.cos(2 * np.pi * doy / 365), promo=bananas.promo.astype(int))
    FEATURES = ["store_id", "dow", "season_sin", "season_cos", "promo", "temp_c"]
    train = bananas[bananas.date < "2025-01-01"].sort_values("date").reset_index(drop=True)
    test = bananas[bananas.date >= "2025-01-01"].reset_index(drop=True)
    pd.DataFrame({"rows": [len(train), len(test)], "mean kg per store and day":
                  [train.sales.mean().round(1), test.sales.mean().round(1)]},
                 index=["train (2024)", "test (2025)"])
    return FEATURES, test, train


@app.cell
def _(mo):
    noise = mo.ui.slider(0, 60, value=30, step=5, label="noise of each reading (%, imprecise)")
    bias = mo.ui.slider(0, 30, value=10, step=2, label="scales read too low by (%, inaccurate)")
    mo.vstack([noise, bias])
    return bias, noise


@app.cell
def _(bias, noise, np, train):
    rng = np.random.default_rng(0)
    eps = rng.normal(0, 1, len(train))
    s, b = noise.value / 100, bias.value / 100
    recorded = {
        "clean": train.sales.to_numpy(),
        "imprecise": np.maximum(train.sales * (1 + s * eps), 0).to_numpy(),
        "inaccurate": (train.sales * (1 - b)).to_numpy(),
        "both": np.maximum(train.sales * (1 - b) * (1 + s * eps), 0).to_numpy(),
    }
    CONDITIONS = list(recorded)
    return CONDITIONS, recorded


@app.cell
def _(CONDITIONS, alt, pd, recorded, train):
    one = train.store_id == 1
    points = pd.concat([pd.DataFrame({"true kg": train.sales[one], "recorded kg": recorded[c][one],
                                      "data": c}) for c in CONDITIONS[1:3]])
    diagonal = alt.Chart(pd.DataFrame({"x": [0, 70], "y": [0, 70]})).mark_line(
        color="#c3c2b7", strokeWidth=1).encode(x=alt.X("x", title="true kg"),
                                               y=alt.Y("y", title="recorded kg"))

    def scatter(kind):
        dots = alt.Chart(points[points.data == kind]).mark_circle(
            size=40, opacity=0.6, clip=True).encode(
            x=alt.X("true kg:Q", title="true kg", scale=alt.Scale(domain=[0, 70])),
            y=alt.Y("recorded kg:Q", title="recorded kg", scale=alt.Scale(domain=[0, 70])),
            color=alt.Color("data:N", scale=alt.Scale(domain=CONDITIONS, range=[
                "#2a78d6", "#eb6834", "#1baf7a", "#eda100"]), legend=None),
            tooltip=["data", alt.Tooltip("true kg:Q", format=".1f"),
                     alt.Tooltip("recorded kg:Q", format=".1f")])
        return (diagonal + dots).properties(width=260, height=260, title=kind)

    alt.hconcat(scatter("imprecise"), scatter("inaccurate")).properties(
        title="Recorded vs true daily banana sales, store 1, 2024 (grey line: recorded = true)")
    return


@app.cell
def _(FEATURES, HistGradientBoostingRegressor, Ridge, np, pd, test):
    SIZES = [14, 28, 56, 112, 224, 366]

    def fit_score(X, y, model):
        if model == "linear":
            enc = lambda f: pd.get_dummies(f.astype({"store_id": str, "dow": str}), dtype=float)
            cols = enc(X).columns
            m = Ridge(alpha=1.0).fit(enc(X), y)
            pred = m.predict(enc(test[FEATURES]).reindex(columns=cols, fill_value=0))
        else:
            m = HistGradientBoostingRegressor(max_iter=60, categorical_features=[0, 1],
                                              random_state=0).fit(X, y)
            pred = m.predict(test[FEATURES])
        err = pred - test.expected_demand
        return float(np.mean(np.abs(err))), float(np.mean(err))

    return SIZES, fit_score


@app.cell
def _(np, train):
    all_days = np.sort(train.date.unique())
    samples = [np.random.default_rng(k).permutation(all_days) for k in range(3)]

    def subset(n, k):
        return train.date.isin(samples[k][:n]).to_numpy()

    return (subset,)


@app.cell
def _(CONDITIONS, FEATURES, SIZES, fit_score, np, pd, recorded, subset, train):
    rows = []
    for c in CONDITIONS:
        for n in SIZES:
            scores = [fit_score(train[FEATURES][subset(n, k)], recorded[c][subset(n, k)],
                                "boosting") for k in range(3)]
            rows.append({"days of training data": n, "data": c,
                         "MAE (kg)": np.mean([sc[0] for sc in scores]),
                         "mean error (kg)": np.mean([sc[1] for sc in scores])})
    curves = pd.DataFrame(rows)
    return (curves,)


@app.cell
def _(CONDITIONS, alt, curves, mo):
    base = alt.Chart(curves).encode(
        x=alt.X("days of training data:Q", scale=alt.Scale(type="log"),
                axis=alt.Axis(values=[14, 28, 56, 112, 224, 366])),
        y=alt.Y("MAE (kg):Q", scale=alt.Scale(zero=True)),
        color=alt.Color("data:N", sort=CONDITIONS),
        tooltip=["data", "days of training data",
                 alt.Tooltip("MAE (kg):Q", format=".2f")])
    chart = (base.mark_line() + base.mark_point()).properties(
        width=560, height=300, title="More data fixes imprecise data, not inaccurate data")
    table = curves.pivot(index="days of training data", columns="data",
                         values="MAE (kg)")[CONDITIONS].round(2)
    bias_row = curves[curves["days of training data"] == 366].set_index("data")["mean error (kg)"]
    mo.vstack([chart, mo.md("Mean absolute error against the true expected demand of 2025 "
                            "(kg per store and day):"), table,
               mo.md("Mean error with all 366 days (negative = the model predicts too little): "
                     + ", ".join(f"{k} {v:+.2f} kg" for k, v in bias_row[CONDITIONS].items()))])
    return


@app.cell
def _(FEATURES, SIZES, alt, fit_score, mo, np, pd, recorded, subset, train):
    models = pd.DataFrame([
        {"days of training data": n, "model": m, "MAE (kg)": np.mean([fit_score(
            train[FEATURES][subset(n, k)], recorded["imprecise"][subset(n, k)], m)[0]
            for k in range(3)])}
        for m in ("linear", "boosting") for n in SIZES])
    _base = alt.Chart(models).encode(
        x=alt.X("days of training data:Q", scale=alt.Scale(type="log"),
                axis=alt.Axis(values=SIZES)),
        y=alt.Y("MAE (kg):Q", scale=alt.Scale(zero=True)),
        color=alt.Color("model:N"),
        tooltip=["model", "days of training data", alt.Tooltip("MAE (kg):Q", format=".2f")])
    mo.vstack([
        mo.md("### Better model or more data? (imprecise data)"),
        (_base.mark_line() + _base.mark_point()).properties(width=560, height=260),
        models.pivot(index="days of training data", columns="model", values="MAE (kg)").round(2),
    ])
    return


@app.cell
def _(FEATURES, HistGradientBoostingRegressor, np, pd, recorded, test, train):
    bands = []
    for _c in ["imprecise", "inaccurate"]:
        q = {}
        for _alpha in (0.1, 0.5, 0.9):
            _m = HistGradientBoostingRegressor(loss="quantile", quantile=_alpha, max_iter=100,
                                               categorical_features=[0, 1], random_state=0)
            q[_alpha] = _m.fit(train[FEATURES], recorded[_c]).predict(test[FEATURES])
        bands.append(pd.DataFrame({"date": test.date, "store_id": test.store_id, "data": _c,
                                   "low": q[0.1], "median": q[0.5], "high": q[0.9],
                                   "true": test.sales}))
    bands = pd.concat(bands)
    coverage = bands.groupby("data").apply(
        lambda b: pd.Series({"true value inside the 80 % interval": np.mean(
            (b.true >= b.low) & (b.true <= b.high)), "interval width (kg)": (b.high - b.low).mean()}),
        include_groups=False).round(2)
    return bands, coverage


@app.cell
def _(alt, bands, coverage, mo):
    window = bands[(bands.store_id == 1) & bands.date.between("2025-05-01", "2025-06-15")]
    _band = alt.Chart().mark_area(opacity=0.15, color="#2a78d6").encode(
        x=alt.X("date:T", title=None), y=alt.Y("low:Q", title="kg per day"), y2="high:Q")
    _median = alt.Chart().mark_line(color="#2a78d6").encode(x="date:T", y="median:Q")
    _true = alt.Chart().mark_line(color="#eb6834", strokeWidth=2).encode(
        x="date:T", y="true:Q", tooltip=[alt.Tooltip("date:T"), alt.Tooltip("true:Q", format=".1f"),
                                        alt.Tooltip("low:Q", format=".1f"),
                                        alt.Tooltip("high:Q", format=".1f")])
    _charts = [alt.layer(_band, _median, _true, data=window[window.data == k]).properties(
        width=270, height=220, title=k) for k in ("imprecise", "inaccurate")]
    _chart = alt.hconcat(*_charts).properties(
        title="80 % prediction interval (blue) and true sales (orange), store 1")
    mo.vstack([_chart, coverage])
    return


@app.cell
def _(mo):
    mo.md("""
    ## What to take away

    - **Imprecise data** (noise) → the model is less confident (wide intervals) and needs more
      data; with enough data the noise averages out.
    - **Inaccurate data** (bias) → the model is confident but wrong (narrow intervals in the
      wrong place). More data does not help: the error stays at the level of the bias.
    - A more complex model does not fix bad data; with little, noisy data a simple model can be
      better. Invest in the *right* data, not only in more data.
    """)
    return


if __name__ == "__main__":
    app.run()
