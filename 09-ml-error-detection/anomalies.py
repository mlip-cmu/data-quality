"""Anomaly detection on delivery quantities: suspicious, not certainly wrong."""

import warnings

import numpy as np
import pandas as pd
from pyod.models.ecod import ECOD
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score
from sklearn.neighbors import LocalOutlierFactor

import inventory_data as d

warnings.simplefilter("ignore", UserWarning)

dl = d.deliveries(dirty=True)
truth = d.errors().query("table == 'deliveries' and column == 'quantity'")
dl["is_error"] = dl.delivery_id.astype(str).isin(truth.row_id)

signed_log = np.sign(dl.quantity) * np.log1p(dl.quantity.abs())
typical = signed_log.groupby([dl.store_id, dl.product_id]).transform("median")
mad = (signed_log - typical).abs().groupby([dl.store_id, dl.product_id]).transform("median")
features = {
    "raw": pd.DataFrame(
        {
            "log_quantity": signed_log,
            "product": dl.product_id,
            "weekday": dl.delivery_date.dt.dayofweek,
        }
    ),
    "in context": pd.DataFrame(
        {"log_quantity": signed_log, "deviation_from_typical": signed_log - typical}
    ),
}
scores = {
    ("robust z-score per store and product", "in context"): (signed_log - typical).abs()
    / (mad + 0.05)
}
for name, X in features.items():
    scores[("IsolationForest (scikit-learn)", name)] = (
        -IsolationForest(random_state=0).fit(X).score_samples(X)
    )
    scores[("LocalOutlierFactor (scikit-learn)", name)] = (
        -LocalOutlierFactor(n_neighbors=100).fit(X).negative_outlier_factor_
    )
    scores[("ECOD (PyOD)", name)] = ECOD().fit(X).decision_scores_

k = int(dl.is_error.sum())
print(
    f"{len(dl):,} deliveries, {k} with an injected quantity error (outlier, wrong unit, negative)\n"
)
rows = []
for (name, feats), s in scores.items():
    top = np.argsort(-np.asarray(s))[:k]
    rows.append(
        (name, feats, dl.is_error.to_numpy()[top].mean(), average_precision_score(dl.is_error, s))
    )
print(
    pd.DataFrame(
        rows, columns=["detector", "features", f"precision in top {k}", "average precision"]
    )
    .round(3)
    .to_string(index=False)
)

best = scores[("IsolationForest (scikit-learn)", "in context")]
print("\nMost suspicious deliveries, IsolationForest in context (for a human to check):\n")
cols = ["delivery_id", "delivery_date", "store_id", "product_name", "quantity", "unit", "is_error"]
ranked = dl.assign(score=best).sort_values("score", ascending=False).reset_index(drop=True)
print(ranked.head(8)[cols + ["score"]].round({"score": 3}).to_string(index=False))
banana = ranked.index[(ranked.product_id == 101) & (ranked.quantity == 80000)][0]
print(f"\nThe 80,000 kg banana delivery is rank {banana + 1}.")
print("One contextual feature (the usual quantity of this product in this store) helps more than")
print("the choice of algorithm. LOF fails here: many deliveries have exactly the same quantity.")
