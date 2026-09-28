"""What happens when data is exchanged without a schema: pandas guesses."""

import json
import warnings

import pandas as pd

import inventory_data as d

warnings.simplefilter("ignore")


def types(df: pd.DataFrame) -> dict[str, str]:
    return {c: str(t) for c, t in df.dtypes.items()}


def section(title: str) -> None:
    print(f"\n=== {title} ===")


section("1. The CSV from the slide: fine, but the types are guesses")
slide = pd.read_csv("products_export.csv", nrows=3)
print(slide.to_string(index=False))
print(types(slide))
print("One value (75.5) makes Quantity a float for all rows, also for counts.")

section("2. The full export: one typo changes the type of the whole column")
try:
    products = pd.read_csv("products_export.csv")
except pd.errors.ParserError as e:
    print(f"read_csv fails: {e}".strip())
    products = pd.read_csv("products_export.csv", on_bad_lines="warn")
    print("With on_bad_lines='warn', the row with an extra field is silently dropped.")
print(types(products))
total = products.Quantity.sum()
print(f"Quantity.sum() = {str(total)[:60]!r}...  (string concatenation, not a number)")
print(f"Missing name and quantity become NaN: {products.isna().sum().to_dict()}")
print(f"Duplicate ProductID 108: {products.ProductID.duplicated().sum()} duplicate, no error")

section("3. Store stock export: identifiers, numbers, dates")
stock = pd.read_csv("stock_export.csv")
print(types(stock))
catalog = d.products()
print(f"GTIN read as {stock.gtin.dtype}: {stock.gtin[0]} (leading zero lost)")
try:
    stock.merge(catalog, on="gtin")
except ValueError as e:
    print(f"Join with the catalog fails: {e}")
fixed = stock.astype({"gtin": str}).merge(catalog, on="gtin")
print(f"Join after astype(str): {len(fixed)} of {len(stock)} rows match (the zero is gone)")
ok = pd.read_csv("stock_export.csv", dtype={"gtin": str}).merge(catalog, on="gtin")
print(f"Read with dtype={{'gtin': str}}: {len(ok)} of {len(stock)} rows match")
print(f"on_hand values: {stock.on_hand.tolist()}  ('N/A' became NaN, '38,2' and '7O' are text)")
dates = pd.to_datetime(stock.date, format="mixed")
print(f"Mixed dates parsed: {[str(x.date()) for x in dates]}")
print("  '06/03/2025' is June 3 in the US, but March 6 in most other countries.")

section("4. JSON supplier feed: every record can look different")
feed = json.load(open("supplier_feed.json"))
flat = pd.json_normalize(feed)
print(flat.to_string(index=False))
print(types(flat))
print("price mixes numbers and strings, one record uses 'title' instead of 'name',")
print("one GTIN is a number without the leading zero, one pack has no unit, units differ in case.")
