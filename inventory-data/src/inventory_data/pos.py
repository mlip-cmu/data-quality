"""Line-level point-of-sale data."""

import numpy as np
import pandas as pd

EVENT_DAYS = pd.date_range("2025-06-02", "2025-06-04")
EVENT_STORES = [1, 2, 3]


def events(sales: pd.DataFrame, products: pd.DataFrame, rng, log) -> pd.DataFrame:
    """Checkout events as they arrive in the event stream (late, duplicated, clock skew)."""
    s = sales[sales.date.isin(EVENT_DAYS) & sales.store_id.isin(EVENT_STORES) & (sales.quantity > 0)]
    s = s.merge(products[["id", "unit"]], left_on="product_id", right_on="id")
    rows = []
    for r in s.itertuples():
        if r.unit == "count":
            parts = _split_counts(int(r.quantity), rng)
        else:
            parts = _split_weight(r.quantity, rng)
        for q in parts:
            rows.append((r.date, r.store_id, r.product_id, q, r.unit, r.unit_price, r.promo))
    e = pd.DataFrame(rows, columns=["date", "store_id", "product_id", "quantity", "unit",
                                    "unit_price", "promo"])
    secs = rng.uniform(7 * 3600, 22 * 3600, len(e))
    e["event_time"] = (e.date + pd.to_timedelta(secs, unit="s")).dt.tz_localize("America/New_York")
    e["terminal_id"] = [f"T{k}" for k in rng.integers(1, 6, len(e))]
    e = e.sort_values(["store_id", "event_time"]).reset_index(drop=True)
    e.insert(0, "event_id", [f"{s}-{t:%Y%m%d}-{i:05d}" for i, (s, t) in
                             enumerate(zip(e.store_id, e.event_time, strict=True))])
    e["ingested_at"] = e.event_time + pd.to_timedelta(rng.exponential(2, len(e)), unit="s")

    late = rng.random(len(e)) < 0.01
    e.loc[late, "ingested_at"] += pd.to_timedelta(rng.uniform(10, 180, late.sum()), unit="m")
    for eid in e.event_id[late]:
        log.add("pos_events", eid, "ingested_at", "late_arrival", None, "10-180 min late")
    skew = (e.store_id == 2) & (e.terminal_id == "T4")
    for eid in e.event_id[skew]:
        log.add("pos_events", eid, "event_time", "clock_skew", "local time", "UTC as local")
    e.loc[skew, "event_time"] += pd.Timedelta(hours=4)
    dup = e[rng.random(len(e)) < 0.005].copy()
    dup["ingested_at"] += pd.to_timedelta(rng.uniform(1, 30, len(dup)), unit="s")
    for eid in dup.event_id:
        log.add("pos_events", eid, "*", "duplicate_record", None, "re-sent by terminal")
    e = pd.concat([e, dup]).sort_values("ingested_at").reset_index(drop=True)
    e["event_time"] = e.event_time.dt.tz_convert("UTC")
    e["ingested_at"] = e.ingested_at.dt.tz_convert("UTC")
    return e.drop(columns="date")


def _split_counts(q: int, rng) -> list[int]:
    parts = []
    while q > 0:
        k = min(q, int(rng.choice([1, 1, 1, 2, 2, 3])))
        parts.append(k)
        q -= k
    return parts


def _split_weight(q: float, rng) -> list[float]:
    parts = []
    while q > 0.05:
        k = min(q, round(float(rng.gamma(3, 0.4)), 3))
        parts.append(round(k, 3))
        q -= k
    return parts


WEIGHED = [101, 104, 105, 106, 110, 111, 127, 128, 129, 130, 159]
LOOKALIKE = {101: 104, 104: 101, 105: 106, 106: 105, 110: 111, 111: 110, 127: 129, 129: 127}


def checkout_lines(products: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    """Weighed items at the checkout plus the corrections staff made later (past repairs)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range("2025-03-01", "2025-03-30")
    price = products.set_index("id").unit_price
    rows = []
    for day in days:
        for store in (1, 2, 3, 4):
            n = rng.poisson(180)
            pid = rng.choice(WEIGHED, n)
            hour = rng.integers(7, 22, n)
            term = rng.integers(1, 6, n)
            cashier = [f"C{store}{k}" for k in rng.integers(1, 7, n)]
            weight = rng.gamma(3, 0.4, n).round(3)
            rows.append(pd.DataFrame({"date": day, "store_id": store, "terminal_id": term,
                                      "cashier_id": cashier, "hour": hour, "product_id": pid,
                                      "true_quantity": weight}))
    lines = pd.concat(rows, ignore_index=True)
    lines["terminal_id"] = "T" + lines.terminal_id.astype(str)
    q = lines.true_quantity.to_numpy().copy()
    p = lines.product_id.to_numpy().copy()

    bad_scale = ((lines.store_id == 2) & (lines.terminal_id == "T3")
                 & (lines.date >= "2025-03-10")).to_numpy()
    q[bad_scale] *= 1.15
    wrong_plu = (lines.cashier_id == "C25").to_numpy() & (rng.random(len(lines)) < 0.12)
    wrong_plu |= (lines.hour >= 20).to_numpy() & (rng.random(len(lines)) < 0.03)
    wrong_plu &= lines.product_id.isin(LOOKALIKE).to_numpy()
    p[wrong_plu] = [LOOKALIKE[x] for x in p[wrong_plu]]
    no_tare = lines.product_id.isin([127, 128, 129, 159]).to_numpy() & (rng.random(len(lines)) < 0.04)
    q[no_tare] += rng.uniform(0.08, 0.2, no_tare.sum())

    lines["product_id"] = p
    lines["quantity"] = q.round(3)
    lines["unit_price"] = lines.product_id.map(price)
    lines["was_corrected"] = bad_scale | wrong_plu | no_tare
    lines["error_cause"] = np.select([bad_scale, wrong_plu, no_tare],
                                     ["scale", "wrong_plu", "no_tare"], "")
    lines.insert(0, "line_id", np.arange(1, len(lines) + 1))
    return lines
