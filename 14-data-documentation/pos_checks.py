"""What the forecasting team assumes about the daily POS sales it receives (defensive checks)."""

import os

os.environ.setdefault("DISABLE_PANDERA_IMPORT_WARNING", "True")

import pandas as pd  # noqa: E402
import pandera.pandas as pa  # noqa: E402


class DailySales(pa.DataFrameModel):
    """Structure: the interface between the POS team and the forecasting team."""

    date: pa.typing.Series[pd.Timestamp]
    store_id: pa.typing.Series[int] = pa.Field(ge=1)
    product_id: pa.typing.Series[int] = pa.Field(ge=101)
    quantity: pa.typing.Series[float] = pa.Field(ge=0)
    unit_price: pa.typing.Series[float] = pa.Field(gt=0)
    promo: pa.typing.Series[bool]

    class Config:
        unique = ["date", "store_id", "product_id"]


def distribution_problems(batch: pd.DataFrame, history: pd.DataFrame,
                          units: pd.Series, tolerance: float = 0.35) -> list[str]:
    """Distribution: each store sells about as much per product as in the same period of history."""
    problems = []
    unit = batch.product_id.map(units)
    for kind in ("kg", "count"):
        now = batch[unit == kind].groupby("store_id").quantity.mean()
        before = history[history.product_id.map(units) == kind].groupby("store_id").quantity.mean()
        ratio = (now / before).dropna()
        for store, r in ratio[(ratio < 1 - tolerance) | (ratio > 1 + tolerance)].items():
            problems.append(f"store {store}: mean {kind} quantity is {r:.2f} x the usual")
    per_store = batch.groupby("store_id").size()
    expected = batch.product_id.nunique() * batch.date.nunique()
    for store, n in per_store[per_store < 0.95 * expected].items():
        problems.append(f"store {store}: only {n} of {expected} rows (missing days?)")
    return problems
