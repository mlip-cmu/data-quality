"""A drift scenario: the same chain, but the world (and the data pipeline) changes in 2025."""

from pathlib import Path

import numpy as np
import pandas as pd

from . import master, sim

LB_PER_KG = 2.20462

EVENTS = [
    {
        "start": "2025-01-15",
        "end": None,
        "kind": "concept drift",
        "event": "Fad diet: cucumber demand more than doubles (also in winter)",
        "stores": "all",
        "products": "102",
    },
    {
        "start": "2025-03-01",
        "end": "2025-08-31",
        "kind": "sensor drift",
        "event": "Checkout scales in store 2 read a bit higher every day; recalibrated 2025-09-01",
        "stores": "2",
        "products": "kg items",
    },
    {
        "start": "2025-04-01",
        "end": None,
        "kind": "concept drift",
        "event": "A competitor opens next to store 3: 30 % less demand for the same inputs",
        "stores": "3",
        "products": "all",
    },
    {
        "start": "2025-06-01",
        "end": None,
        "kind": "data drift",
        "event": "Two new stores open in Florida (much warmer climate)",
        "stores": "9, 10",
        "products": "all",
    },
    {
        "start": "2025-07-10",
        "end": "2025-07-31",
        "kind": "data drift",
        "event": "Heatwave in PA and OH (+8 °C)",
        "stores": "1-8",
        "products": "all",
    },
    {
        "start": "2025-09-01",
        "end": None,
        "kind": "schema drift",
        "event": "POS software update in stores 7 and 8 records weights in lb instead of kg",
        "stores": "7, 8",
        "products": "kg items",
    },
    {
        "start": "2025-10-15",
        "end": None,
        "kind": "schema drift",
        "event": "The weather API changes temp_c from °C to °F (the column name stays the same)",
        "stores": "all",
        "products": "all",
    },
]


def build(out: Path, seed: int = 42) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed + 5)
    stores = master.stores()
    products = master.products()
    days = sim.dates()
    wx = sim.weather(days, np.random.default_rng(seed))
    heat = wx.date.between("2025-07-10", "2025-07-31") & ~wx.station.isin(["TPA", "MCO"])
    wx.loc[heat, "temp_c"] += 8

    def fad_diet(w: sim.World) -> None:
        w.lam[w.days >= "2025-01-15", :, _idx(w.products, 102)] *= 2.2

    def competitor(w: sim.World) -> None:
        w.lam[w.days >= "2025-04-01", _idx(w.stores, 3), :] *= 0.7

    world = sim.make_world(
        stores, products, days, seed=seed, modifiers=[fad_diet, competitor], weather_df=wx
    )
    result = sim.simulate(world, master.shelf_volume_l(products, stores))

    kg = (products.unit == "kg").to_numpy()
    factor = np.ones(world.lam.shape)
    t = (days - pd.Timestamp("2025-03-01")).days.to_numpy()
    scale = np.where((t >= 0) & (days <= "2025-08-31"), 1 + 0.0015 * t, 1.0)
    factor[:, _idx(stores, 2), :] *= np.where(kg, scale[:, None], 1.0)
    lb = days >= "2025-09-01"
    for s in (7, 8):
        factor[lb, _idx(stores, s), :] *= np.where(kg, LB_PER_KG, 1.0)
    noise = np.where(kg, rng.normal(1, 0.01, factor.shape), 1.0)
    recorded = np.where(kg, (result["sales"] * factor * noise).round(2), result["sales"])

    price = products.unit_price.to_numpy()[None, None, :] * np.where(world.promo, 0.8, 1.0)[:, None]
    long = sim.to_long(
        world,
        {
            "quantity": recorded,
            "unit_price": np.broadcast_to(price, recorded.shape).round(2),
            "promo": np.broadcast_to(world.promo[:, None, :], recorded.shape),
            "demand": world.demand,
            "true_sales": result["sales"],
            "lost": result["lost"],
            "expected_demand": world.lam,
        },
    )
    long[["date", "store_id", "product_id", "quantity", "unit_price", "promo"]].to_parquet(
        out / "sales.parquet", index=False
    )
    long[
        ["date", "store_id", "product_id", "expected_demand", "demand", "true_sales", "lost"]
    ].to_parquet(out / "truth.parquet", index=False)

    reported = wx.copy()
    f = reported.date >= "2025-10-15"
    reported.loc[f, "temp_c"] = (reported.loc[f, "temp_c"] * 9 / 5 + 32).round(1)
    reported.to_parquet(out / "weather.parquet", index=False)
    stores.to_parquet(out / "stores.parquet", index=False)

    rows = []
    for si, s in enumerate(stores.itertuples()):
        for di, day in enumerate(days):
            if world.open_[di, si]:
                mean = 1.2 * factor[di, si, _idx(products, 101)] * (1 + rng.normal(0, 0.02))
                rows.append((day, s.id, round(float(mean), 3)))
    pd.DataFrame(rows, columns=["date", "store_id", "mean_banana_line_kg"]).to_parquet(
        out / "scale_readings.parquet", index=False
    )


def _idx(df: pd.DataFrame, value: int) -> int:
    return int(np.flatnonzero(df.id.to_numpy() == value)[0])
