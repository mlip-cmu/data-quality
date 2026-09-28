"""Build the clean dataset (2 years, 8 stores, 60 products)."""

from pathlib import Path

import numpy as np
import pandas as pd

from . import master, sim


def build(out: Path, seed: int = 42) -> None:
    rng = np.random.default_rng(seed + 1)
    out.mkdir(parents=True, exist_ok=True)
    stores = master.stores(include_new=False)
    products = master.products()
    suppliers = master.suppliers()
    planogram = master.shelf_volume_l(products, stores)
    world = sim.make_world(stores, products, seed=seed)
    result = sim.simulate(world, planogram)

    days = world.days
    price = products.unit_price.to_numpy()[None, None, :] * np.where(world.promo, 0.8, 1.0)[:, None]
    price = np.broadcast_to(price, world.lam.shape).round(2)
    long = sim.to_long(world, {
        "quantity": result["sales"], "unit_price": price,
        "promo": np.broadcast_to(world.promo[:, None, :], world.lam.shape),
        "on_hand_system": result["on_hand_system"], "counted": result["counted"],
        "expected_demand": world.lam, "demand": world.demand, "lost": result["lost"], "waste": result["waste"],
        "shrink": result["shrink"], "on_hand": result["on_hand"],
        "arrivals": result["arrivals"], "orders": result["orders"],
    })

    sales = long[["date", "store_id", "product_id", "quantity", "unit_price", "promo"]].copy()
    sales["revenue"] = (sales.quantity * sales.unit_price).round(2)
    sales.to_parquet(out / "sales.parquet", index=False)
    long[["date", "store_id", "product_id", "on_hand_system"]].to_parquet(
        out / "inventory.parquet", index=False)
    long[["date", "store_id", "product_id", "expected_demand", "demand", "quantity", "lost",
          "waste", "shrink", "on_hand"]].rename(columns={"quantity": "sales"}).to_parquet(
        out / "truth.parquet", index=False)

    staff = {s: [f"E{s:02d}{k}" for k in range(1, 5)] for s in stores.id}
    counts = long[long.counted.notna()][["date", "store_id", "product_id", "counted", "on_hand"]]
    counts = counts.rename(columns={"counted": "counted_qty"})
    counts["counted_by"] = [rng.choice(staff[s]) for s in counts.store_id]
    audit = counts.sample(frac=0.02, random_state=seed).rename(columns={"on_hand": "audited_qty"})
    counts.drop(columns="on_hand").to_parquet(out / "stock_counts.parquet", index=False)
    audit.drop(columns="counted_by").to_parquet(out / "stock_audit.parquet", index=False)

    deliveries = _deliveries(long, products, stores, suppliers, staff, rng)
    deliveries.to_parquet(out / "deliveries.parquet", index=False)
    _oos_reports(long, rng).to_parquet(out / "oos_reports.parquet", index=False)

    wx = sim.weather(days, np.random.default_rng(seed))
    wx.to_parquet(out / "weather.parquet", index=False)
    products.to_parquet(out / "products.parquet", index=False)
    suppliers.to_parquet(out / "suppliers.parquet", index=False)
    stores.to_parquet(out / "stores.parquet", index=False)
    master.zip_codes().to_parquet(out / "zip_codes.parquet", index=False)
    planogram.to_parquet(out / "planogram.parquet", index=False)


def _deliveries(long, products, stores, suppliers, staff, rng) -> pd.DataFrame:
    d = long[long.arrivals > 0][["date", "store_id", "product_id", "arrivals"]].copy()
    d = d.rename(columns={"date": "delivery_date", "arrivals": "quantity"})
    d = d.merge(products[["id", "name", "category", "unit", "supplier_id"]]
                .rename(columns={"id": "product_id", "name": "product_name"}), on="product_id")
    d = d.merge(suppliers[["id", "name", "lead_time_days"]]
                .rename(columns={"id": "supplier_id", "name": "supplier_name"}), on="supplier_id")
    d = d.merge(stores[["id", "city", "zip"]]
                .rename(columns={"id": "store_id", "city": "store_city", "zip": "store_zip"}),
                on="store_id")
    d["order_date"] = d.delivery_date - pd.to_timedelta(d.lead_time_days, unit="D")
    d = d.sort_values(["delivery_date", "store_id", "product_id"]).reset_index(drop=True)
    d.insert(0, "delivery_id", np.arange(500001, 500001 + len(d)))
    d["received_by"] = [rng.choice(staff[s]) for s in d.store_id]
    hours = rng.uniform(6, 14, len(d))
    lag_days = np.where(rng.random(len(d)) < 0.03, rng.integers(1, 6, len(d)), 0)
    d["received_at"] = d.delivery_date + pd.to_timedelta(hours, unit="h")
    d["entered_at"] = d.received_at + pd.to_timedelta(
        lag_days * 24 + rng.exponential(0.5, len(d)), unit="h")
    d["received_at"] = d.received_at.dt.floor("min")
    d["entered_at"] = d.entered_at.dt.floor("min")
    cols = ["delivery_id", "order_date", "delivery_date", "supplier_id", "supplier_name",
            "store_id", "store_city", "store_zip", "product_id", "product_name", "category",
            "quantity", "unit", "received_by", "received_at", "entered_at"]
    return d[cols]


def _oos_reports(long, rng) -> pd.DataFrame:
    """Customers report empty shelves in the app: noisy and incomplete."""
    empty = (long.lost > 0) & (rng.random(len(long)) < 0.15)
    false_alarm = (long.lost == 0) & (rng.random(len(long)) < 0.002)
    r = long[empty | false_alarm][["date", "store_id", "product_id"]].copy()
    r["reported_at"] = r.date + pd.to_timedelta(rng.uniform(9, 21, len(r)), unit="h")
    r["reported_at"] = r.reported_at.dt.floor("min")
    r.insert(0, "report_id", np.arange(1, len(r) + 1))
    return r.drop(columns="date").reset_index(drop=True)
