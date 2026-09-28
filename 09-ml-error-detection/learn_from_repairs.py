"""Learn from past repairs: which new checkout lines will staff probably have to correct?"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

import inventory_data as d

lines = d.checkout_lines()
features = ["store_id", "terminal_id", "cashier_id", "hour", "product_id", "quantity",
            "unit_price"]
X = lines[features].astype({c: "category" for c in ["store_id", "terminal_id", "cashier_id",
                                                     "product_id"]})
y = lines.was_corrected
past = (lines.date < "2025-03-21").to_numpy()

model = HistGradientBoostingClassifier(categorical_features="from_dtype", random_state=0)
model.fit(X[past], y[past])
p = model.predict_proba(X[~past])[:, 1]
new, truth = lines[~past].assign(p=p), y[~past].to_numpy()

k = int(0.05 * len(new))
top = np.argsort(-p)[:k]
print(f"{past.sum():,} past lines (March 1-20) with {y[past].sum()} corrections -> train")
print(f"{(~past).sum():,} new lines (March 21-30) -> which ones should staff check?\n")
print(f"  ROC AUC: {roc_auc_score(truth, p):.3f}")
print(f"  Checking the top 5 % ({k} lines) finds {truth[top].sum()} of {truth.sum()} lines that "
      f"need a correction (precision {truth[top].mean():.0%}, base rate {truth.mean():.1%})")

imp = permutation_importance(model, X[~past], truth, scoring="roc_auc", n_repeats=5,
                             random_state=0)
print("\nWhat the model learned (permutation importance):")
for name, value in sorted(zip(features, imp.importances_mean, strict=True), key=lambda t: -t[1]):
    print(f"  {name:<12} {value:.3f}")

print("\nThe learned patterns are the causes of the past repairs:")
for cause, grp in lines[past & lines.was_corrected].groupby("error_cause"):
    where = grp[["store_id", "terminal_id", "cashier_id", "hour"]].astype(str).mode().iloc[0].to_dict()
    print(f"  {cause:<10} {len(grp):>4} corrections, most often at {where}")
print("\nMost suspicious new lines:")
print(new.nlargest(5, "p")[["line_id", "date", "store_id", "terminal_id", "cashier_id", "hour",
                            "product_id", "quantity", "p", "was_corrected"]]
      .round({"p": 3}).to_string(index=False))
