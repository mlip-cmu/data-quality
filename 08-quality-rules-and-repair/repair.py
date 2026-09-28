"""Repair wrong and inconsistent data: rules, fuzzy matching, and HoloClean-style repair."""

import math

import pandas as pd
from rapidfuzz import fuzz, process

import inventory_data as d

clean_dl = d.deliveries().set_index("delivery_id")
dirty_dl = d.deliveries(dirty=True).set_index("delivery_id")
errors = d.errors()


def score(repairs: pd.DataFrame, table_errors: pd.DataFrame) -> str:
    """Compare repaired cells (delivery_id, column, value) with the clean data."""
    truth = [clean_dl.at[i, c] if i in clean_dl.index else None
             for i, c in zip(repairs.delivery_id, repairs.column, strict=True)]
    right = sum(str(t) == str(v) for t, v in zip(truth, repairs.value, strict=True))
    return (f"{len(repairs)} cells repaired: {right} correct, {len(repairs) - right} wrong; "
            f"{len(table_errors)} injected errors of these kinds")


print("=== 1. Repair rules ===\n")
stores = d.stores(dirty=True)
zips = d.zip_codes().set_index("zip").city
stores["zip"] = stores.zip.astype(str).str.zfill(5)
fixed = stores.assign(city=stores.zip.map(zips).fillna(stores.city))
truth = d.stores().set_index("id").city
for s in fixed[fixed.city != stores.city].itertuples():
    ok = "correct" if s.city == truth[s.id] else "WRONG: the ZIP was wrong, not the city"
    print(f"  store {s.id}: city '{stores.set_index('id').city[s.id]}' -> '{s.city}'  {ok}")

units = {"Kg": "kg", "kgs": "kg", "KG": "kg", "kilogram": "kg", "ct": "count", "each": "count",
         "Count": "count", "l": "liter", "Liter": "liter", "ltr": "liter"}
bad_unit = dirty_dl.unit.isin(units)
repairs = pd.DataFrame({"delivery_id": dirty_dl.index[bad_unit], "column": "unit",
                        "value": dirty_dl.unit[bad_unit].map(units)})
print(f"\n  units: {score(repairs, errors.query('table == \"deliveries\" and column == \"unit\"'))}")

print("\n=== 2. Fuzzy matching against the product catalog ===\n")
catalog = d.products().set_index("id").name
suspect = dirty_dl[dirty_dl.product_name != dirty_dl.product_id.map(catalog)]
auto, review = [], []
for i, row in suspect.iterrows():
    name, similarity, best_id = process.extractOne(row.product_name, catalog, scorer=fuzz.ratio)
    if best_id == row.product_id and similarity >= 85:
        auto.append((i, "product_name", name))
    else:
        review.append((i, row.product_id, row.product_name, best_id, round(similarity)))
auto = pd.DataFrame(auto, columns=["delivery_id", "column", "value"])
print(f"  typos fixed automatically: {score(auto, errors.query('error_type == \"misspelling\" and table == \"deliveries\"'))}")
print(f"  {len(review)} deliveries to a human: the name points to another product than the ID, e.g.")
for i, pid, name, best, sim in review[:3]:
    print(f"    delivery {i}: product_id {pid} ({catalog[pid]}) but name '{name}' -> {best}? ({sim} %)")

print("\n=== 3. HoloClean-style repair: learn the constraints from the data itself ===\n")
ENTITY = ["product_id", "product_name", "category", "unit", "supplier_id"]
EPS = 0.01


def similarity(a: str, b: str, column: str) -> float:
    if column.endswith("_id"):
        return 0.05
    return max(fuzz.ratio(a, b) / 100, 0.01)


def repair_candidates(rows: pd.DataFrame, entity: list[str], min_support: int = 30):
    counts = rows.astype(str).groupby(entity).size()
    frequent = counts[counts >= min_support]
    known = set(frequent.index)
    for observed, n_rows in counts[counts < min_support].items():
        cands = []
        for tup, support in frequent.items():
            diff = [c for c, a, b in zip(entity, observed, tup, strict=True) if a != b]
            if len(diff) <= 2:
                logp = math.log(support) + sum(
                    math.log(1 - EPS) if a == b else math.log(EPS * similarity(a, b, c))
                    for c, a, b in zip(entity, observed, tup, strict=True))
                cands.append((logp, tup, diff))
        if cands and observed not in known:
            top = max(c[0] for c in cands)
            total = sum(math.exp(c[0] - top) for c in cands)
            logp, best, diff = max(cands)
            yield observed, best, diff, 1 / total, n_rows


rows = dirty_dl[ENTITY].astype(str)
applied, review = [], []
for observed, best, diff, p, n in repair_candidates(rows, ENTITY):
    target = applied if p >= 0.9 else review
    mask = (rows[ENTITY] == pd.Series(observed, index=ENTITY)).all(axis=1)
    for i in rows.index[mask]:
        for c in diff:
            target.append((i, c, best[ENTITY.index(c)], p))
applied = pd.DataFrame(applied, columns=["delivery_id", "column", "value", "p"])
review = pd.DataFrame(review, columns=["delivery_id", "column", "value", "p"])
kinds = errors.query("table == 'deliveries' and column in @ENTITY and error_type != 'missing_record'")
print(f"  {score(applied, kinds)}")
print(f"  {len(review)} more cells have a repair with p < 0.9 and go to a human")
examples = applied.drop_duplicates("column").head(4)
for r in examples.itertuples():
    print(f"    delivery {r.delivery_id}: {r.column} '{dirty_dl.at[r.delivery_id, r.column]}' -> "
          f"'{r.value}' (p = {r.p:.3f})")
print("\n  No reference data was used: the frequent value combinations are the 'constraints'.")
