"""Near-duplicate delivery records with probabilistic record linkage (Splink)."""

import logging

import pandas as pd
import splink.comparison_library as cl
import splink.comparison_level_library as cll
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

import inventory_data as d

logging.getLogger("splink").setLevel(logging.ERROR)

dl = d.deliveries(dirty=True)
dl = dl[dl.delivery_date.between("2025-01-01", "2025-03-31")]
records = dl[["delivery_id", "store_id", "product_id", "delivery_date", "quantity", "unit",
              "received_by"]].reset_index(drop=True)

errors = d.errors().query("table == 'deliveries' and error_type in "
                          "['duplicate_record', 'near_duplicate']")
copies = errors.assign(original=errors.dirty_value.str.removeprefix("copy of ").astype(int),
                       duplicate=errors.row_id.astype(int))
ids = set(records.delivery_id)
true_pairs = {tuple(sorted(p)) for p in zip(copies.original, copies.duplicate, strict=True)
              if p[0] in ids and p[1] in ids}

settings = SettingsCreator(
    link_type="dedupe_only",
    unique_id_column_name="delivery_id",
    comparisons=[
        cl.ExactMatch("store_id").configure(m_probabilities=[0.999, 0.001]),
        cl.ExactMatch("product_id").configure(m_probabilities=[0.999, 0.001]),
        cl.AbsoluteDateDifferenceAtThresholds("delivery_date", input_is_string=False,
                                              metrics=["day", "day"], thresholds=[1, 3])
        .configure(m_probabilities=[0.95, 0.04, 0.005, 0.005]),
        cl.CustomComparison([cll.NullLevel("quantity"), cll.ExactMatchLevel("quantity"),
                             cll.PercentageDifferenceLevel("quantity", 0.15), cll.ElseLevel()],
                            output_column_name="quantity"),
        cl.ExactMatch("unit"),
    ],
    blocking_rules_to_generate_predictions=[
        "l.store_id = r.store_id AND l.product_id = r.product_id "
        "AND abs(date_diff('day', l.delivery_date, r.delivery_date)) <= 3"],
)
db = DuckDBAPI()
linker = Linker(db.register(records), settings)
linker.training.estimate_probability_two_random_records_match(
    [block_on("store_id", "product_id", "delivery_date")], recall=0.9)
linker.training.estimate_u_using_random_sampling(max_pairs=1e6, seed=1)
linker.training.estimate_parameters_using_expectation_maximisation(
    block_on("store_id", "product_id", "delivery_date"))
pairs = linker.inference.predict(threshold_match_probability=0.01).as_pandas_dataframe()
pairs["pair"] = [tuple(sorted(p)) for p in zip(pairs.delivery_id_l, pairs.delivery_id_r,
                                                strict=True)]
pairs["is_duplicate"] = pairs.pair.isin(true_pairs)

print(f"{len(records):,} deliveries in Q1 2025, {len(true_pairs)} injected duplicate pairs "
      f"({errors.error_type.value_counts().to_dict()} overall)\n")
exact = records[records.duplicated(["store_id", "product_id", "delivery_date", "quantity"],
                                   keep=False)]
exact_pairs = {tuple(sorted(g.delivery_id))[:2] for _, g in
               exact.groupby(["store_id", "product_id", "delivery_date", "quantity"])}
rows = [("exact match on all fields", len(exact_pairs), len(exact_pairs & true_pairs))]
for t in (0.01, 0.1, 0.3):
    found = pairs[pairs.match_probability >= t]
    rows.append((f"Splink, match probability >= {t}", len(found), int(found.is_duplicate.sum())))
result = pd.DataFrame(rows, columns=["method", "pairs found", "true duplicates"])
result["precision"] = (result["true duplicates"] / result["pairs found"]).round(3)
result["recall"] = (result["true duplicates"] / len(true_pairs)).round(3)
print(result.to_string(index=False))

print("\nNear duplicates (the second entry has a slightly different quantity):\n")
cols = ["delivery_id_l", "delivery_id_r", "delivery_date_l", "delivery_date_r", "quantity_l",
        "quantity_r", "match_probability"]
near = pairs[pairs.is_duplicate & (pairs.quantity_l != pairs.quantity_r)]
print(near[cols].head(4).round({"match_probability": 3}).to_string(index=False))
print("\nNot duplicates, but similar (the same product the next day):\n")
print(pairs[~pairs.is_duplicate].nlargest(3, "match_probability")[cols]
      .round({"match_probability": 3}).to_string(index=False))
