"""Drift reports and tests with Evidently: the same month of 2024 is the reference."""

import os
import warnings
from pathlib import Path

os.environ.setdefault("DO_NOT_TRACK", "1")
warnings.filterwarnings("ignore")

from evidently import DataDefinition, Dataset, Regression, Report  # noqa: E402
from evidently.metrics import MAE, MeanError  # noqa: E402
from evidently.presets import DataDriftPreset  # noqa: E402
from evidently.tests import gte, lte  # noqa: E402

import inventory_data as d  # noqa: E402
from inventory_data import forecast  # noqa: E402

OUT = Path("out")
OUT.mkdir(exist_ok=True)

data = forecast.features(d.drift_sales(), d.drift_stores(), d.drift_weather())
model = forecast.train(data[data.date < "2025-01-01"])
data["pred"] = forecast.predict(model, data)
data["store_id"] = data.store_id.astype(str)
data["product_id"] = data.product_id.astype(str)

definition = DataDefinition(
    numerical_columns=["temp_c", "unit_price", "quantity", "pred"],
    categorical_columns=["store_id", "product_id", "dow", "promo"],
    regression=[Regression(target="quantity", prediction="pred")])
columns = definition.numerical_columns + definition.categorical_columns


def window(month: str):
    rows = data[data.date.dt.strftime("%Y-%m") == month]
    return Dataset.from_pandas(rows[columns], data_definition=definition)


for current, reference in [("2025-03", "2024-03"), ("2025-06", "2024-06"),
                           ("2025-11", "2024-11")]:
    report = Report([DataDriftPreset(), MAE(mean_tests=[lte(3.3)]),
                     MeanError(mean_tests=[gte(-0.3), lte(0.3)])], include_tests=True)
    snapshot = report.run(current_data=window(current), reference_data=window(reference))
    path = OUT / f"drift_{current}.html"
    snapshot.save_html(str(path))
    tests = snapshot.dict()["tests"]
    failed = [t["name"] for t in tests if t["status"] != "SUCCESS"]
    print(f"{current} vs {reference}: {len(tests) - len(failed)} of {len(tests)} tests pass "
          f"-> {path}")
    for name in failed[:8]:
        print(f"   FAIL {name}")
    if len(failed) > 8:
        print(f"   ... and {len(failed) - 8} more")
