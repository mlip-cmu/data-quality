"""The sales forecasting model of the case study (needs `scikit-learn` in the calling project)."""

import numpy as np
import pandas as pd

FEATURES = ["store_id", "product_id", "dow", "season_sin", "season_cos", "promo", "unit_price",
            "temp_c"]
CATEGORICAL = ["store_id", "product_id", "dow"]


def features(sales: pd.DataFrame, stores: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """One row per store, product, and day with the model features (weather as reported)."""
    wx = weather.merge(stores[["id", "station"]].rename(columns={"id": "store_id"}), on="station")
    df = sales.merge(wx[["date", "store_id", "temp_c"]], on=["date", "store_id"], how="left")
    doy = df.date.dt.dayofyear
    return df.assign(dow=df.date.dt.dayofweek, season_sin=np.sin(2 * np.pi * doy / 365.25),
                     season_cos=np.cos(2 * np.pi * doy / 365.25), promo=df.promo.astype(int))


def train(df: pd.DataFrame, target: str = "quantity", max_iter: int = 200):
    from sklearn.ensemble import HistGradientBoostingRegressor

    model = HistGradientBoostingRegressor(
        max_iter=max_iter, learning_rate=0.1, categorical_features=[
            FEATURES.index(c) for c in CATEGORICAL], random_state=0)
    model.fit(df[FEATURES], np.log1p(df[target].clip(lower=0)))
    model.calibration_ = 1.0
    model.calibration_ = df[target].sum() / predict(model, df).sum()
    return model


def predict(model, df: pd.DataFrame) -> np.ndarray:
    """Predictions on the original scale (corrected for the bias of the log transform)."""
    return np.expm1(model.predict(df[FEATURES])) * model.calibration_
