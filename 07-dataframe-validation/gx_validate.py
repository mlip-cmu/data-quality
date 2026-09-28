"""Great Expectations: check a new batch of delivery records before it enters the pipeline."""

import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

import great_expectations as gx  # noqa: E402
import great_expectations.expectations as gxe  # noqa: E402

import inventory_data as d  # noqa: E402

MONTH = ("2025-03-01", "2025-04-01")
OUT = Path("out").resolve()


def batch(dirty: bool):
    dl = d.deliveries(dirty=dirty)
    return dl[dl.entered_at.between(*MONTH, inclusive="left")].reset_index(drop=True)


context = gx.get_context(mode="ephemeral")
context.add_data_docs_site("local", {
    "class_name": "SiteBuilder",
    "site_index_builder": {"class_name": "DefaultSiteIndexBuilder"},
    "store_backend": {"class_name": "TupleFilesystemStoreBackend",
                      "base_directory": str(OUT / "gx_docs")},
})
deliveries = (context.data_sources.add_pandas("receiving").add_dataframe_asset("deliveries")
              .add_batch_definition_whole_dataframe("month"))

suite = context.suites.add(gx.ExpectationSuite(name="deliveries"))
for expectation in [
    # the expectations from the slide
    gxe.ExpectColumnValuesToBeOfType(column="delivery_id", type_="int64"),
    gxe.ExpectColumnValuesToBeUnique(column="delivery_id"),
    gxe.ExpectColumnValuesToBeOfType(column="quantity", type_="float64"),
    gxe.ExpectColumnValuesToBeBetween(column="quantity", min_value=0, max_value=None),
    gxe.ExpectColumnValuesToBeInSet(column="unit", value_set=["count", "kg", "liter"]),
    gxe.ExpectColumnValuesToBeOfType(column="supplier_id", type_="int64"),
    # more checks on the same batch
    gxe.ExpectColumnValuesToBeInSet(column="supplier_id", value_set=d.suppliers().id.tolist()),
    gxe.ExpectColumnValuesToBeInSet(column="category", value_set=d.products().category.unique()
                                    .tolist()),
    gxe.ExpectColumnValuesToBeBetween(column="delivery_date", min_value=datetime(2024, 1, 1),
                                      max_value=datetime(2025, 12, 31)),
    gxe.ExpectColumnPairValuesAToBeGreaterThanB(column_A="entered_at", column_B="received_at",
                                                or_equal=True),
    gxe.ExpectCompoundColumnsToBeUnique(
        column_list=["delivery_date", "store_id", "product_id", "quantity"]),
    gxe.ExpectColumnMedianToBeBetween(column="quantity", min_value=10, max_value=60),
    gxe.ExpectColumnStdevToBeBetween(column="quantity", max_value=200),
    gxe.ExpectColumnMaxToBeBetween(column="quantity", max_value=2000),
]:
    suite.add_expectation(expectation)

validation = context.validation_definitions.add(
    gx.ValidationDefinition(name="monthly deliveries", data=deliveries, suite=suite))

for label, dirty in [("clean batch", False), ("batch as entered by staff", True)]:
    df = batch(dirty)
    result = validation.run(batch_parameters={"dataframe": df},
                            result_format={"result_format": "COMPLETE",
                                           "unexpected_index_column_names": ["delivery_id"]})
    stats = result.statistics
    print(f"\n=== {label}: {len(df)} deliveries, {stats['successful_expectations']} of "
          f"{stats['evaluated_expectations']} expectations met ===\n")
    for r in result.results:
        cfg = r.expectation_config
        args = {k: v for k, v in cfg.kwargs.items() if k in ("column", "column_A", "column_list")}
        detail = ""
        if not r.success:
            res = r.result
            if "unexpected_count" in res:
                values = res.get("unexpected_list", [])
                examples = sorted({str(v) for v in values})[:4] if values and not isinstance(
                    values[0], dict) else []
                detail = f"{res['unexpected_count']} unexpected" + (
                    f", e.g. {examples}" if examples else "")
            elif "observed_value" in res:
                detail = f"observed {res['observed_value']}"
        column = str(list(args.values())[0])
        column = column if len(column) < 16 else "4 columns"
        print(f"  {'ok  ' if r.success else 'FAIL'} {cfg.type:<48} {column:<14} {detail[:60]}")

context.build_data_docs()
print(f"\nData Docs: {OUT / 'gx_docs' / 'index.html'}")
