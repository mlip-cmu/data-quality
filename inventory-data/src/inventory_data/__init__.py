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
        export_csv()
        export_preview()
        stamp.touch()
    return DATA_DIR


def export_csv() -> None:
    """Write every Parquet table also as CSV (committed to git, so it can be read on GitHub)."""
    for path in sorted(DATA_DIR.glob("*/*.parquet")):
        df = pd.read_parquet(path)
        df.round({c: 4 for c in df.columns if df[c].dtype.kind == "f"}).to_csv(
            path.with_suffix(".csv"), index=False
        )


PREVIEW = {"store_id": 1, "from": "2025-03-01", "to": "2025-03-31"}
PREVIEW_DRIFT = {"store_id": 7, "from": "2025-08-15", "to": "2025-09-15"}


def export_preview(max_bytes: int = 500_000) -> None:
    """Small CSV files that GitHub shows as a table: small tables in full, an extract of each
    large table (one store and one month; for drift, store 7 around the POS switch to lb)."""
    preview = DATA_DIR / "preview"
    preview.mkdir(exist_ok=True)
    for f in preview.glob("*.csv"):
        f.unlink()
    for path in sorted(DATA_DIR.glob("*/*.csv")):
        if path.parent == preview:
            continue
        name = f"{path.parent.name}_{path.stem}"
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        if path.stat().st_size > max_bytes:
            p = PREVIEW_DRIFT if path.parent.name == "drift" else PREVIEW
            date = next(c for c in ("date", "delivery_date", "event_time") if c in df.columns)
            day = df[date].str[:10]
            keep = (day >= p["from"]) & (day <= p["to"])
            if "store_id" in df.columns:
                keep &= df.store_id == str(p["store_id"])
            df = df[keep]
            name += f"_store{p['store_id']}_{p['from']}_{p['to']}"
        df.to_csv(preview / f"{name}.csv", index=False)


def _read(kind: str, name: str) -> pd.DataFrame:
    return pd.read_parquet(ensure() / kind / f"{name}.parquet")


def _table(name: str):
    def load(dirty: bool = False) -> pd.DataFrame:
        kind = "dirty" if dirty else "clean"
        if not (ensure() / kind / f"{name}.parquet").exists():
            return pd.read_csv(DATA_DIR / kind / f"{name}.csv")
        return _read(kind, name)

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
