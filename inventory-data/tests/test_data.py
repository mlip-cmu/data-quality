import numpy as np
import pandas as pd

import inventory_data as d
from inventory_data import master, sim


def test_world_is_deterministic():
    stores, products = master.stores(include_new=False), master.products()
    days = sim.dates("2024-01-01", "2024-01-31")
    a = sim.make_world(stores, products, days, seed=3)
    b = sim.make_world(stores, products, days, seed=3)
    np.testing.assert_array_equal(a.demand, b.demand)


def test_clean_data_meets_rules():
    p, s, st = d.products(), d.suppliers(), d.stores()
    assert p.id.is_unique and p.gtin.is_unique
    assert p.gtin.map(master.gtin_is_valid).all()
    assert set(p.supplier_id) <= set(s.id)
    assert set(p.unit) <= set(master.UNITS)
    zips = d.zip_codes().set_index("zip").city
    assert (st.zip.map(zips) == st.city).all()
    dl = d.deliveries()
    assert (dl.quantity > 0).all() and set(dl.product_id) <= set(p.id)
    sales = d.sales()
    assert (sales.quantity >= 0).all()
    assert not sales.duplicated(["date", "store_id", "product_id"]).any()


def test_every_changed_product_cell_is_logged():
    clean = d.products().astype(str).set_index("id")
    dirty = pd.read_csv(d.path("dirty", "products.csv"), dtype=str, keep_default_na=False)
    dirty = dirty.drop_duplicates("id").set_index("id").loc[clean.index]
    logged = set(d.errors().query("table == 'products'").pipe(
        lambda e: zip(e.row_id, e.column)))
    for pid in clean.index:
        for col in ["name", "category", "unit", "unit_price", "supplier_id", "gtin",
                    "case_pack", "case_height_cm", "shelf_life_days"]:
            a, b = clean.at[pid, col], dirty.at[pid, col]
            if a != b and not (a in ("nan", "None") and b == "") and _num(a) != _num(b):
                assert (pid, col) in logged, (pid, col, a, b)


def test_delivery_duplicates_and_missing_rows_are_logged():
    clean, dirty = d.deliveries(), d.deliveries(dirty=True)
    e = d.errors().query("table == 'deliveries'")
    extra = set(dirty.delivery_id) - set(clean.delivery_id)
    missing = set(clean.delivery_id) - set(dirty.delivery_id)
    assert extra == set(e[e.error_type.isin(["duplicate_record", "near_duplicate"])].row_id.astype(int))
    assert missing == set(e[e.error_type == "missing_record"].row_id.astype(int))


def _num(x):
    try:
        return float(x)
    except ValueError:
        return x
