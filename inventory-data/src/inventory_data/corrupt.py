"""Inject realistic data quality problems into copies of the clean tables.

Every injected problem is logged in `errors.parquet` (the ground truth for detectors).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from . import master, pos


class ErrorLog:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, table, row_id, column, error_type, clean, dirty) -> None:
        self.rows.append(
            {
                "table": table,
                "row_id": str(row_id),
                "column": column,
                "error_type": error_type,
                "clean_value": _s(clean),
                "dirty_value": _s(dirty),
            }
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _s(v) -> str | None:
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)


def build(clean: Path, out: Path, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    log = ErrorLog()
    products = pd.read_parquet(clean / "products.parquet")
    _products(products, log).to_csv(out / "products.csv", index=False)
    _suppliers(pd.read_parquet(clean / "suppliers.parquet"), log).to_csv(
        out / "suppliers.csv", index=False
    )
    _stores(pd.read_parquet(clean / "stores.parquet"), log).to_csv(out / "stores.csv", index=False)
    _deliveries(pd.read_parquet(clean / "deliveries.parquet"), rng, log).to_parquet(
        out / "deliveries.parquet", index=False
    )
    _sales(pd.read_parquet(clean / "sales.parquet"), log).to_parquet(
        out / "sales.parquet", index=False
    )
    _counts(pd.read_parquet(clean / "stock_counts.parquet"), products, rng, log).to_parquet(
        out / "stock_counts.parquet", index=False
    )
    events = pos.events(pd.read_parquet(clean / "sales.parquet"), products, rng, log)
    events.to_parquet(out / "pos_events.parquet", index=False)
    pos.checkout_lines(products).to_parquet(out / "checkout_lines.parquet", index=False)
    log.frame().to_parquet(out / "errors.parquet", index=False)


def _set(df, key, row_id, column, value, error_type, log, table):
    idx = df.index[df[key] == row_id][0]
    log.add(table, row_id, column, error_type, df.at[idx, column], value)
    df.at[idx, column] = value


def _products(p: pd.DataFrame, log: ErrorLog) -> pd.DataFrame:
    p = p.astype(object).copy()
    t = "products"

    def put(pid, col, val, kind):
        _set(p, "id", pid, col, val, kind, log, t)

    put(106, "unit", "lbs", "illegal_value")
    put(110, "unit", "KG", "illegal_value")
    put(120, "unit_price", "-3.99", "illegal_value")
    put(126, "unit_price", "N/A", "missing_value")
    put(139, "unit_price", "2,99", "invalid_format")
    put(124, "gtin", p.loc[p.id == 124, "gtin"].iloc[0][:12] + "0", "invalid_format")
    put(131, "supplier_id", 502, "dangling_reference")
    put(136, "supplier_id", 283, "dangling_reference")
    for pid in (114, 132, 135, 150, 151):
        for col in ("case_length_cm", "case_width_cm", "case_height_cm"):
            v = float(p.loc[p.id == pid, col].iloc[0])
            put(pid, col, round(v / 2.54, 1), "wrong_unit")
    for pid in (147, 153):
        h, c = p.loc[p.id == pid, ["case_height_cm", "case_pack"]].iloc[0]
        put(pid, "case_height_cm", float(c), "wrong_field_order")
        put(pid, "case_pack", int(round(h)), "wrong_field_order")
    put(158, "category", None, "missing_value")
    put(103, "name", "Cauliflour", "misspelling")
    put(115, "name", "Bluberries 6 oz", "misspelling")
    put(108, "unit", "liter", "violated_dependency")
    put(142, "category", "Heartland Pantry", "misfielded_value")
    put(152, "shelf_life_days", 9999, "placeholder")
    put(141, "unit_price", 2.59, "wrong_value")

    def dup(src, new_id, kind, **changes):
        row = p[p.id == src].iloc[0].copy()
        row["id"] = new_id
        for k, v in changes.items():
            row[k] = v
        log.add(t, new_id, "*", kind, None, f"copy of {src}")
        return row

    extra = [
        dup(101, 161, "duplicate_key", name="Bananas"),
        dup(104, 162, "near_duplicate", name="Organic Bananas", gtin=master.gtin13(201, 162)),
        dup(117, 163, "near_duplicate", name="Whole Milk Gallon", gtin=master.gtin13(202, 163)),
        dup(150, 150, "duplicate_key", name="Paper Towels 8 rolls", unit_price=11.49),
    ]
    return pd.concat([p, pd.DataFrame(extra)], ignore_index=True)


def _suppliers(s: pd.DataFrame, log: ErrorLog) -> pd.DataFrame:
    s = s.astype(object).copy()
    _set(s, "id", 205, "contact_phone", "999-9999999", "placeholder", log, "suppliers")
    _set(s, "id", 209, "contact_name", None, "missing_value", log, "suppliers")
    _set(s, "id", 207, "contact_phone", "(614) 555 0107", "invalid_format", log, "suppliers")
    row = s[s.id == 201].iloc[0].copy()
    row["id"], row["name"] = 213, "Fresh Fields Produce Inc."
    log.add("suppliers", 213, "*", "near_duplicate", None, "copy of 201")
    return pd.concat([s, row.to_frame().T], ignore_index=True)


def _stores(s: pd.DataFrame, log: ErrorLog) -> pd.DataFrame:
    s = s.astype(object).copy()
    _set(s, "id", 2, "city", "Pittsburg", "misspelling", log, "stores")
    _set(s, "id", 6, "city", "USA", "misfielded_value", log, "stores")
    _set(s, "id", 5, "zip", "15213", "violated_dependency", log, "stores")
    _set(s, "id", 4, "state", "Pennsylvania", "invalid_format", log, "stores")
    return s


TYPO_UNITS = {
    "kg": ["Kg", "kgs", "KG", "kilogram"],
    "count": ["ct", "each", "Count"],
    "liter": ["l", "Liter", "ltr"],
}


def _typo(word: str, rng) -> str:
    i = int(rng.integers(1, max(2, len(word) - 1)))
    return (
        word[:i] + word[i + 1 :]
        if rng.random() < 0.5
        else word[: i - 1] + word[i] + word[i - 1] + word[i + 1 :]
    )


def _deliveries(d: pd.DataFrame, rng, log: ErrorLog) -> pd.DataFrame:
    d = d.copy()
    t = "deliveries"
    n = len(d)
    pick = lambda frac, mask=None: rng.choice(  # noqa: E731
        d.index[mask] if mask is not None else d.index, max(1, int(frac * n)), replace=False
    )
    used: set[int] = set()

    def fresh(idx):
        idx = [i for i in idx if i not in used]
        used.update(idx)
        return idx

    kg = (d.unit == "kg").to_numpy()
    for i in fresh(pick(0.001, kg)):
        log.add(
            t,
            d.at[i, "delivery_id"],
            "quantity",
            "wrong_unit",
            d.at[i, "quantity"],
            d.at[i, "quantity"] * 1000,
        )
        d.at[i, "quantity"] *= 1000
    for i in fresh(pick(0.001)):
        log.add(
            t,
            d.at[i, "delivery_id"],
            "quantity",
            "outlier",
            d.at[i, "quantity"],
            d.at[i, "quantity"] * 10,
        )
        d.at[i, "quantity"] *= 10
    banana = d.index[(d.product_id == 101) & (d.store_id == 1) & (d.delivery_date == "2025-03-14")][
        0
    ]
    log.add(t, d.at[banana, "delivery_id"], "quantity", "outlier", d.at[banana, "quantity"], 80000)
    d.at[banana, "quantity"] = 80000.0
    used.add(banana)
    for i in fresh(pick(0.005)):
        new = rng.choice(TYPO_UNITS[d.at[i, "unit"]])
        log.add(t, d.at[i, "delivery_id"], "unit", "invalid_format", d.at[i, "unit"], new)
        d.at[i, "unit"] = new
    for i in fresh(pick(0.003)):
        new = _typo(d.at[i, "product_name"], rng)
        log.add(
            t, d.at[i, "delivery_id"], "product_name", "misspelling", d.at[i, "product_name"], new
        )
        d.at[i, "product_name"] = new
    ids = np.sort(d.product_id.unique())
    for i in fresh(pick(0.002)):
        pid = d.at[i, "product_id"]
        new = int(ids[(np.searchsorted(ids, pid) + 1) % len(ids)])
        log.add(t, d.at[i, "delivery_id"], "product_id", "wrong_reference", pid, new)
        d.at[i, "product_id"] = new
    for i in fresh(pick(0.002)):
        new = "Pittsburg" if d.at[i, "store_city"] == "Pittsburgh" else "Pittsburgh"
        log.add(
            t,
            d.at[i, "delivery_id"],
            "store_city",
            "violated_dependency",
            d.at[i, "store_city"],
            new,
        )
        d.at[i, "store_city"] = new
    for i in fresh(pick(0.001)):
        log.add(
            t,
            d.at[i, "delivery_id"],
            "category",
            "misfielded_value",
            d.at[i, "category"],
            d.at[i, "supplier_name"],
        )
        d.at[i, "category"] = d.at[i, "supplier_name"]
    for i in fresh(pick(0.0005)):
        log.add(
            t,
            d.at[i, "delivery_id"],
            "delivery_date",
            "placeholder",
            d.at[i, "delivery_date"].date(),
            "1900-01-01",
        )
        d.at[i, "delivery_date"] = pd.Timestamp("1900-01-01")
    for i in fresh(pick(0.0005)):
        log.add(
            t,
            d.at[i, "delivery_id"],
            "quantity",
            "illegal_value",
            d.at[i, "quantity"],
            -d.at[i, "quantity"],
        )
        d.at[i, "quantity"] = -d.at[i, "quantity"]

    missing = fresh(pick(0.003))
    for i in missing:
        log.add(t, d.at[i, "delivery_id"], "*", "missing_record", "delivery", None)
    d = d.drop(index=missing)

    src = d.loc[[i for i in pick(0.005) if i in d.index and i not in used]]
    dups = src.copy()
    dups["entered_at"] = dups.entered_at + pd.to_timedelta(rng.integers(5, 240, len(dups)), "m")
    near = rng.random(len(dups)) < 0.3
    dups.loc[near, "quantity"] = (
        dups.loc[near, "quantity"] * rng.choice([0.9, 1.1], near.sum())
    ).round(1)
    dups["delivery_id"] = np.arange(900001, 900001 + len(dups))
    for (_, a), (_, b), is_near in zip(src.iterrows(), dups.iterrows(), near, strict=True):
        log.add(
            t,
            b.delivery_id,
            "*",
            "near_duplicate" if is_near else "duplicate_record",
            None,
            f"copy of {a.delivery_id}",
        )
    return pd.concat([d, dups]).sort_values(["delivery_date", "entered_at"]).reset_index(drop=True)


def _sales(s: pd.DataFrame, log: ErrorLog) -> pd.DataFrame:
    s = s.copy()
    stale = (s.product_id == 136) & s.store_id.isin([7, 8]) & (s.date >= "2025-03-01") & ~s.promo
    for r in s[stale].itertuples():
        log.add(
            "sales",
            f"{r.date.date()}|{r.store_id}|{r.product_id}",
            "unit_price",
            "inconsistent_value",
            r.unit_price,
            7.99,
        )
    s.loc[stale, "unit_price"] = 7.99
    s.loc[stale, "revenue"] = (s.loc[stale, "quantity"] * 7.99).round(2)
    outage = (s.store_id == 6) & s.date.between("2025-02-10", "2025-02-12")
    for day in s[outage].date.unique():
        log.add("sales", f"{pd.Timestamp(day).date()}|6", "*", "missing_record", "store-day", None)
    dup = s[(s.store_id == 3) & (s.date == "2025-05-05")]
    log.add("sales", "2025-05-05|3", "*", "duplicate_record", None, "uploaded twice")
    return (
        pd.concat([s[~outage], dup])
        .sort_values(["date", "store_id", "product_id"])
        .reset_index(drop=True)
    )


def _counts(c: pd.DataFrame, products: pd.DataFrame, rng, log: ErrorLog) -> pd.DataFrame:
    c = c.copy()
    count_ids = set(products.id[products.unit == "count"])
    two_digit = (
        c.product_id.isin(count_ids)
        & c.counted_qty.between(12, 98)
        & (c.counted_qty % 10 != c.counted_qty // 10)
    )
    for i in rng.choice(c.index[two_digit], int(0.005 * len(c)), replace=False):
        v = int(c.at[i, "counted_qty"])
        new = float(str(v)[::-1])
        log.add(
            "stock_counts",
            f"{c.at[i, 'date'].date()}|{c.at[i, 'store_id']}|{c.at[i, 'product_id']}",
            "counted_qty",
            "transposed_digits",
            v,
            new,
        )
        c.at[i, "counted_qty"] = new
    return c
