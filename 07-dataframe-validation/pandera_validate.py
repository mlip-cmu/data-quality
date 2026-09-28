"""Pandera: the schema of the product master data as code, with a quarantine for bad rows."""

import os
import re
from pathlib import Path

os.environ.setdefault("DISABLE_PANDERA_IMPORT_WARNING", "True")

import pandas as pd  # noqa: E402
import pandera.pandas as pa  # noqa: E402
from pandera.typing import DataFrame, Series  # noqa: E402

import inventory_data as d  # noqa: E402
from inventory_data.master import gtin_is_valid  # noqa: E402

OUT = Path("out")
OUT.mkdir(exist_ok=True)
SUPPLIERS = d.suppliers().id.tolist()


class ProductMaster(pa.DataFrameModel):
    id: Series[int] = pa.Field(unique=True, gt=100)
    gtin: Series[str] = pa.Field(str_matches=r"^\d{13}$", unique=True)
    name: Series[str] = pa.Field(str_length={"min_value": 2, "max_value": 255})
    category: Series[str] = pa.Field(
        isin=[
            "produce",
            "dairy",
            "bakery",
            "meat",
            "seafood",
            "beverages",
            "pantry",
            "frozen",
            "household",
            "refill",
        ]
    )
    unit: Series[str] = pa.Field(isin=["count", "kg", "liter"])
    unit_price: Series[float] = pa.Field(gt=0, le=500)
    supplier_id: Series[int] = pa.Field(isin=SUPPLIERS)
    case_pack: Series[int] = pa.Field(ge=1, le=200)
    case_height_cm: Series[float] = pa.Field(ge=5, le=120)
    shelf_life_days: Series[int] = pa.Field(ge=1, le=1825)

    @pa.check("gtin", name="gtin_check_digit")
    def check_digit(cls, gtin: Series[str]) -> Series[bool]:
        return gtin.map(gtin_is_valid)

    @pa.dataframe_check(name="produce_is_sold_by_count_or_kg")
    def produce_unit(cls, df: pd.DataFrame) -> Series[bool]:
        return (df.category != "produce") | df.unit.isin(["count", "kg"])

    class Config:
        coerce = True


raw = pd.read_csv(d.path("dirty", "products.csv"), dtype=str, keep_default_na=False)
raw = raw.replace("", None)
print(f"{len(raw)} rows in the product master data (read as text)\n")


def reasons(failures: pd.DataFrame) -> pd.Series:
    f = failures.dropna(subset=["index"])
    frame = "produce_is_sold_by_count_or_kg"
    f = f.assign(
        reason=[
            chk if chk == frame else f"{col} {re.sub(r'\\(\\[.*\\]\\)', '(...)', chk)} [{case}]"
            for col, chk, case in zip(f.column, f.check.astype(str), f.failure_case, strict=True)
        ]
    )
    return f.drop_duplicates(["index", "reason"]).groupby("index").reason.agg("; ".join)


data, rejected = raw, []
for _ in range(3):
    try:
        good = ProductMaster.validate(data, lazy=True)
        break
    except pa.errors.SchemaErrors as e:
        why = reasons(e.failure_cases)
        rejected.append(data.loc[why.index.astype(int)].assign(reason=why.to_numpy()))
        data = data.drop(index=why.index.astype(int))

quarantine = pd.concat(rejected)
quarantine.to_csv(OUT / "quarantine.csv", index=False)
good.to_parquet(OUT / "products_valid.parquet")
print(quarantine[["id", "name", "reason"]].to_string(index=False, max_colwidth=90))
print(
    f"\n{len(good)} valid rows -> out/products_valid.parquet, "
    f"{len(quarantine)} rows -> out/quarantine.csv"
)
print("Not caught: most case dimensions in inches (plausible numbers), a price that is too low,")
print("a near-duplicate name. These need rules across rows and tables (see 08 and 09).")


@pa.check_types(lazy=True)
def shelf_capacity(products: DataFrame[ProductMaster], shelf_volume_l: float) -> pd.Series:
    case_l = products.case_height_cm * 30 * 40 / 1000
    return (shelf_volume_l // case_l) * products.case_pack


print("\nA function with a typed interface rejects bad input at the call:")
try:
    shelf_capacity(raw, 120.0)
except pa.errors.SchemaErrors as e:
    print(f"  shelf_capacity(raw data): SchemaErrors with {len(e.failure_cases)} failures")
print(f"  shelf_capacity(valid data): ok, {len(shelf_capacity(good, 120.0))} values")

print("\nLearned invariants: infer a schema from February (clean), check March (as entered)")
cols = ["quantity", "store_id", "unit"]
clean, dirty = d.deliveries(), d.deliveries(dirty=True)
feb = clean[clean.delivery_date.between("2025-02-01", "2025-02-28")][cols]
mar = dirty[dirty.delivery_date.between("2025-03-01", "2025-03-31")]
inferred = pa.infer_schema(feb)
for name, col in inferred.columns.items():
    print(f"  {name}: {col.dtype}, " + ", ".join(c.error for c in col.checks))
try:
    inferred.validate(mar[cols], lazy=True)
except pa.errors.SchemaErrors as e:
    flagged = mar.loc[e.failure_cases["index"].dropna().astype(int).unique(), "delivery_id"]
    injected = d.errors().query("table == 'deliveries' and column == 'quantity'").row_id
    real = flagged.astype(str).isin(injected).sum()
    print(
        f"  {len(flagged)} March deliveries flagged, {real} of them are injected errors; the other "
        f"{len(flagged) - real} are only larger than anything seen in February."
    )
