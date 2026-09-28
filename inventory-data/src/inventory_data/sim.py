"""Small simulation engine: true demand -> shelves -> recorded sales -> orders -> deliveries."""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import master

START, END = "2024-01-01", "2025-12-31"
WEEKDAY = np.array([0.85, 0.85, 0.9, 0.95, 1.1, 1.3, 1.05])
HOLIDAYS = pd.to_datetime([
    "2024-01-01", "2024-05-27", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-05-26", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
])


def dates(start: str = START, end: str = END) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="D")


def weather(days: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    doy = days.dayofyear.to_numpy()
    shared = _ar1(len(days), 0.7, 2.5, rng)
    rows = []
    for station, (mean, amp) in master.WEATHER_STATIONS.items():
        noise = (shared if station not in ("TPA", "MCO") else 0) + _ar1(len(days), 0.6, 1.2, rng)
        temp = mean - amp * np.cos(2 * np.pi * (doy - 20) / 365) + noise
        rain = np.where(rng.random(len(days)) < 0.35, rng.gamma(1.2, 6, len(days)), 0.0)
        rows.append(pd.DataFrame({"date": days, "station": station,
                                  "temp_c": temp.round(1), "precip_mm": rain.round(1)}))
    return pd.concat(rows, ignore_index=True)


def _ar1(n: int, phi: float, sd: float, rng: np.random.Generator) -> np.ndarray:
    x = np.zeros(n)
    eps = rng.normal(0, sd * np.sqrt(1 - phi**2), n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + eps[i]
    return x


def promotions(days: pd.DatetimeIndex, products_df: pd.DataFrame,
               rng: np.random.Generator) -> np.ndarray:
    """Chain-wide promotion weeks, (days, products) bool."""
    weeks = (days - days[0]).days // 7
    on = rng.random((weeks.max() + 1, len(products_df))) < 0.06
    return on[weeks]


@dataclass
class World:
    days: pd.DatetimeIndex
    stores: pd.DataFrame
    products: pd.DataFrame
    temp: np.ndarray  # (D, S) true temperature
    promo: np.ndarray  # (D, P)
    lam: np.ndarray  # (D, S, P) expected demand
    demand: np.ndarray  # (D, S, P) sampled true demand
    open_: np.ndarray  # (D, S)


def make_world(stores_df: pd.DataFrame, products_df: pd.DataFrame,
               days: pd.DatetimeIndex | None = None, seed: int = 42,
               modifiers: list[Callable[[World], None]] | None = None,
               weather_df: pd.DataFrame | None = None) -> World:
    rng = np.random.default_rng(seed)
    days = dates() if days is None else days
    wx = weather(days, rng) if weather_df is None else weather_df
    temp = (wx.pivot(index="date", columns="station", values="temp_c")
            .reindex(days)[stores_df.station].to_numpy())
    promo = promotions(days, products_df, rng)
    doy = days.dayofyear.to_numpy()[:, None]

    amp_peak = [master.SEASON_OVERRIDE.get(p.id, master.SEASON.get(p.category, (0.0, 1)))
                for p in products_df.itertuples()]
    amp = np.array([a for a, _ in amp_peak])[None, :]
    peak = np.array([pk for _, pk in amp_peak])[None, :]
    season = 1 + amp * np.cos(2 * np.pi * (doy - peak) / 365)

    temp_coef = np.array([master.TEMP_SENSITIVITY.get(i, 0.0) for i in products_df.id])
    temp_eff = np.exp(temp_coef[None, None, :] * (temp[:, :, None] - 15))

    store_scale = stores_df.size_sqm.to_numpy() / 2400 * rng.uniform(0.9, 1.1, len(stores_df))
    weekday = WEEKDAY[days.dayofweek]
    to_holiday = np.array([((HOLIDAYS - d).days.to_numpy() % 400).min() for d in days])
    holiday = np.where((to_holiday >= 1) & (to_holiday <= 3), 1.3, 1.0)
    trend = 1 + 0.02 * (days - days[0]).days.to_numpy() / 365
    day_eff = (weekday * holiday * trend)[:, None, None]

    base = products_df.base_demand.to_numpy(float)
    lam = (base[None, None, :] * store_scale[None, :, None] * day_eff * season[:, None, :]
           * temp_eff * np.where(promo, 1.6, 1.0)[:, None, :])
    open_ = (days.to_numpy()[:, None] >= stores_df.opened.to_numpy()[None, :])
    world = World(days, stores_df, products_df, temp, promo, lam, np.zeros_like(lam), open_)
    for modify in modifiers or []:
        modify(world)
    world.lam *= world.open_[:, :, None]
    world.demand = sample_demand(world.lam, products_df.unit.to_numpy(), rng)
    return world


def sample_demand(lam: np.ndarray, units: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    count = units == "count"
    out = np.empty_like(lam)
    out[..., count] = rng.poisson(lam[..., count] * rng.gamma(20, 1 / 20, lam[..., count].shape))
    out[..., ~count] = (lam[..., ~count] * rng.gamma(12, 1 / 12, lam[..., ~count].shape)).round(2)
    return out


@dataclass
class Inventory:
    """Daily inventory loop for all stores and products at once."""

    demand: np.ndarray  # (D, S, P)
    capacity: np.ndarray  # (S, P) shelf capacity in units, as the system computes it
    case_pack: np.ndarray  # (P,)
    lead_time: np.ndarray  # (P,)
    shelf_life: np.ndarray  # (P,)
    is_count: np.ndarray  # (P,)
    shrink_rate: float = 0.003
    count_every: int | None = 7
    seed: int = 0
    out: dict = field(default_factory=dict)

    def run(self, policy: Callable[[int, "Inventory"], np.ndarray]) -> dict:
        rng = np.random.default_rng(self.seed)
        n_days, n_s, n_p = self.demand.shape
        shape = self.demand.shape
        o = {k: np.zeros(shape) for k in ("sales", "lost", "waste", "shrink", "orders",
                                          "arrivals", "on_hand", "on_hand_system")}
        o["counted"] = np.full(shape, np.nan)
        self.true = np.minimum(self.capacity, self.demand[:7].mean(0) * 3)
        self.true = np.where(self.is_count, np.round(self.true), self.true)
        self.system = self.true.copy()
        pipeline = np.zeros((n_days + int(self.lead_time.max()) + 1, n_s, n_p))
        self.pipeline, self.o = pipeline, o
        perishable = self.shelf_life <= 30
        spoil = np.where(perishable, 0.2 / self.shelf_life, 0.0)
        for d in range(n_days):
            self.day = d
            arr = pipeline[d]
            self.true += arr
            self.system += arr
            sales = np.minimum(self.demand[d], self.true)
            waste = self._rand_round(self.true - sales, spoil, rng)
            shrink = self._rand_round(self.true - sales - waste, self.shrink_rate, rng)
            self.true -= sales + waste + shrink
            self.system = np.maximum(self.system - sales - waste, 0)
            if self.count_every and d % self.count_every == self.count_every - 1:
                counted = self._count(rng)
                o["counted"][d] = counted
                self.system = counted.copy()
            o["sales"][d], o["waste"][d], o["shrink"][d] = sales, waste, shrink
            o["lost"][d] = self.demand[d] - sales
            o["arrivals"][d], o["on_hand"][d], o["on_hand_system"][d] = arr, self.true, self.system
            want = np.maximum(policy(d, self), 0)
            cases = np.ceil(np.round(want / self.case_pack, 6))
            qty = cases * self.case_pack
            o["orders"][d] = qty
            for p in range(n_p):
                pipeline[d + int(self.lead_time[p]), :, p] += qty[:, p]
        self.out = o
        return o

    def on_order(self) -> np.ndarray:
        return self.pipeline[self.day + 1:].sum(0)

    def _rand_round(self, base: np.ndarray, rate, rng) -> np.ndarray:
        amount = np.maximum(base, 0) * rate
        rounded = np.floor(amount + rng.random(amount.shape))
        return np.where(self.is_count, rounded, amount.round(2))

    def _count(self, rng) -> np.ndarray:
        err = np.where(rng.random(self.true.shape) < 0.1, rng.integers(-3, 4, self.true.shape), 0)
        noisy = np.where(self.is_count, self.true + err,
                         self.true * rng.normal(1, 0.03, self.true.shape))
        return np.maximum(noisy, 0).round(2)


def shelf_capacity(products_df: pd.DataFrame, stores_df: pd.DataFrame,
                   planogram: pd.DataFrame) -> np.ndarray:
    """Units that fit on the shelf, computed from the case dimensions in the master data."""
    vol = planogram.pivot(index="store_id", columns="product_id", values="shelf_volume_l")
    vol = vol.loc[stores_df.id, products_df.id].to_numpy()
    cases = np.floor(vol / master.case_volume_l(products_df).to_numpy()[None, :])
    return np.maximum(cases, 1) * products_df.case_pack.to_numpy()[None, :]


def reorder_policy(forecast: np.ndarray, capacity: np.ndarray, lead_time: np.ndarray,
                   safety: float = 1.3) -> Callable[[int, Inventory], np.ndarray]:
    """(s, S) policy: reorder when stock + open orders fall below the expected demand."""

    def policy(d: int, inv: Inventory) -> np.ndarray:
        f = forecast[min(d + 1, len(forecast) - 1)]
        position = inv.system + inv.on_order()
        reorder_point = f * (lead_time + 1) * safety
        target = np.minimum(np.maximum(capacity, reorder_point), capacity * 1.5)
        return np.where(position < reorder_point, target - position, 0)

    return policy


def simulate(world: World, planogram: pd.DataFrame, products_df: pd.DataFrame | None = None,
             lead_times: np.ndarray | None = None, forecast: np.ndarray | None = None,
             shrink_rate: float = 0.003, count_every: int | None = 7, seed: int = 1) -> dict:
    """Run the inventory loop. `products_df` is the master data the *system* uses
    (it may contain errors); the true world is in `world`."""
    p = world.products if products_df is None else products_df
    capacity = shelf_capacity(p, world.stores, planogram)
    lead = lead_times if lead_times is not None else _lead_times(world.products)
    inv = Inventory(world.demand, capacity, p.case_pack.to_numpy(float), lead,
                    world.products.shelf_life_days.to_numpy(), (world.products.unit == "count")
                    .to_numpy(), shrink_rate=shrink_rate, count_every=count_every, seed=seed)
    inv.run(reorder_policy(world.lam if forecast is None else forecast, capacity, lead))
    return inv.out | {"capacity": capacity}


def _lead_times(products_df: pd.DataFrame) -> np.ndarray:
    lt = master.suppliers().set_index("id").lead_time_days
    return products_df.supplier_id.map(lt).to_numpy()


def to_long(world: World, arrays: dict[str, np.ndarray]) -> pd.DataFrame:
    """(D, S, P) arrays -> long table with one row per open store, product and day."""
    d, s, p = np.meshgrid(np.arange(len(world.days)), np.arange(len(world.stores)),
                          np.arange(len(world.products)), indexing="ij")
    df = pd.DataFrame({"date": world.days[d.ravel()],
                       "store_id": world.stores.id.to_numpy()[s.ravel()],
                       "product_id": world.products.id.to_numpy()[p.ravel()]})
    for name, arr in arrays.items():
        df[name] = arr.ravel()
    return df[world.open_[d.ravel(), s.ravel()]].reset_index(drop=True)
