"""Learn common patterns (approximate functional dependencies) and flag the rows that break them."""

from itertools import permutations

import pandas as pd

import inventory_data as d

dl = d.deliveries(dirty=True)
COLUMNS = ["product_id", "product_name", "category", "unit", "supplier_id", "supplier_name",
           "store_id", "store_city", "store_zip"]
errors = d.errors().query("table == 'deliveries'")


def confidence(df: pd.DataFrame, lhs: str, rhs: str) -> float:
    """Share of rows whose rhs value is the most frequent one for their lhs value."""
    top = df.groupby([lhs, rhs]).size().groupby(level=0).max()
    return top.sum() / len(df)


rules = []
for lhs, rhs in permutations(COLUMNS, 2):
    if dl[lhs].nunique() > 1 and dl[rhs].nunique() > 1:
        c = confidence(dl, lhs, rhs)
        if 0.95 <= c < 1:
            rules.append((lhs, rhs, c))
rules = pd.DataFrame(rules, columns=["if you know", "you know", "confidence"])
rules = rules[~rules["you know"].isin(["store_zip"])].sort_values("confidence", ascending=False)
print("Learned patterns (almost always true in the data; 100 % patterns have nothing to flag):\n")
print(rules.round(4).to_string(index=False))

print("\nRows that break the product_id -> product_name pattern:\n")
mode = dl.groupby("product_id").product_name.agg(lambda s: s.mode()[0])
flagged = dl[dl.product_name != dl.product_id.map(mode)]
kinds = errors[errors.row_id.isin(flagged.delivery_id.astype(str))].error_type.value_counts()
print(f"  {len(flagged)} rows flagged; injected errors among them: {kinds.to_dict()}")
print(flagged[["delivery_id", "product_id", "product_name"]].head(5).assign(
    usual_name=lambda f: f.product_id.map(mode)).to_string(index=False))
print("\nA flagged row says only that the ID and the name disagree: a typo in the name, or a wrong ID.")
print("Some learned patterns are only 'usually true' (a supplier mostly delivers one category, but")
print("the seafood supplier also sells frozen shrimp). Rows that break those are often correct.")
