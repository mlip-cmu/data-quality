"""Synthetic dataset for the supermarket inventory case study.

All tables are generated on first use (deterministic) and cached as Parquet files.
"""

import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(os.environ.get("INVENTORY_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
VERSION = "2"


def ensure(force: bool = False) -> Path:
    stamp = DATA_DIR / f"VERSION-{VERSION}"
    if force or not stamp.exists():
        from . import corrupt, generate, scenarios

        generate.build(DATA_DIR / "clean")
        corrupt.build(DATA_DIR / "clean", DATA_DIR / "dirty")
        scenarios.build(DATA_DIR / "drift")
        stamp.touch()
    return DATA_DIR


def _read(kind: str, name: str) -> pd.DataFrame:
    return pd.read_parquet(ensure() / kind / f"{name}.parquet")


def _table(name: str):
    def load(dirty: bool = False) -> pd.DataFrame:
        csv = ensure() / "dirty" / f"{name}.csv"
        if dirty and csv.exists():
            return pd.read_csv(csv)
        return _read("dirty" if dirty else "clean", name)

    load.__name__ = name
    load.__doc__ = f"The `{name}` table (clean, or with injected errors if dirty=True)."
    return load


products = _table("products")
suppliers = _table("suppliers")
stores = _table("stores")
deliveries = _table("deliveries")
sales = _table("sales")
stock_counts = _table("stock_counts")


def path(kind: str, name: str) -> Path:
    """Path of a generated file, e.g. path("dirty", "products.csv")."""
    return ensure() / kind / name


def zip_codes() -> pd.DataFrame:
    return _read("clean", "zip_codes")


def planogram() -> pd.DataFrame:
    return _read("clean", "planogram")


def inventory() -> pd.DataFrame:
    return _read("clean", "inventory")


def weather() -> pd.DataFrame:
    return _read("clean", "weather")


def stock_audit() -> pd.DataFrame:
    return _read("clean", "stock_audit")


def oos_reports() -> pd.DataFrame:
    return _read("clean", "oos_reports")


def truth() -> pd.DataFrame:
    """Expected and true demand, lost sales, waste, shrinkage, true stock (not observable)."""
    return _read("clean", "truth")


def errors() -> pd.DataFrame:
    """Ground truth of all injected errors in the dirty tables."""
    return _read("dirty", "errors")


def pos_events() -> pd.DataFrame:
    """Line-level POS events of a few days, as they arrive in the event stream."""
    return _read("dirty", "pos_events")


def checkout_lines() -> pd.DataFrame:
    """Weighed checkout lines with the corrections staff made later (`was_corrected`)."""
    return _read("dirty", "checkout_lines")


def drift_sales() -> pd.DataFrame:
    """Daily sales 2024-2025 with drift events (see `drift_events()`)."""
    return _read("drift", "sales")


def drift_stores() -> pd.DataFrame:
    """Stores in the drift scenario (with the two new stores in Florida)."""
    return _read("drift", "stores")


def drift_truth() -> pd.DataFrame:
    return _read("drift", "truth")


def drift_weather() -> pd.DataFrame:
    """Weather as reported by the weather API (°F after the API change)."""
    return _read("drift", "weather")


def drift_scale_readings() -> pd.DataFrame:
    return _read("drift", "scale_readings")


def drift_events() -> pd.DataFrame:
    from .scenarios import EVENTS

    return pd.DataFrame(EVENTS)
