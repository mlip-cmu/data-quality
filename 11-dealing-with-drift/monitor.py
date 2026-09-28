"""Weekly monitoring run: Evidently snapshots in a local workspace, plus alerts for humans."""

import json
import os
import shutil
import warnings
from pathlib import Path

os.environ.setdefault("DO_NOT_TRACK", "1")
warnings.filterwarnings("ignore")

import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from evidently import DataDefinition, Dataset, Regression, Report  # noqa: E402
from evidently.metrics import MAE, DriftedColumnsCount, MeanError, OutRangeValueCount  # noqa: E402
from evidently.sdk.models import PanelMetric  # noqa: E402
from evidently.sdk.panels import line_plot_panel  # noqa: E402
from evidently.ui.workspace import Workspace  # noqa: E402

import inventory_data as d  # noqa: E402
from inventory_data import forecast  # noqa: E402

OUT = Path("out")
WORKSPACE = OUT / "workspace"
shutil.rmtree(WORKSPACE, ignore_errors=True)
OUT.mkdir(exist_ok=True)

data = forecast.features(d.drift_sales(), d.drift_stores(), d.drift_weather())
model = forecast.train(data[data.date < "2025-01-01"])
data["pred"] = forecast.predict(model, data)
data = data.astype({"store_id": str, "product_id": str})
INPUTS = ["store_id", "product_id", "promo", "temp_c", "unit_price"]
definition = DataDefinition(
    numerical_columns=["temp_c", "unit_price", "quantity", "pred"],
    categorical_columns=["store_id", "product_id", "promo"],
    regression=[Regression(target="quantity", prediction="pred")],
)
CHECKS = {
    "share of drifted input columns": ("DriftedColumnsCount", "share"),
    "temperatures out of range (-30..45 °C)": ("OutRangeValueCount", "count"),
    "MAE (kg or count)": ("MAE", "mean"),
    "mean error (kg or count)": ("MeanError", "mean"),
}
thresholds = yaml.safe_load(open("thresholds.yaml"))

ws = Workspace.create(str(WORKSPACE))
project = ws.create_project("Inventory forecasting: weekly monitoring")
for title, (metric, label) in CHECKS.items():
    project.dashboard.add_panel(
        line_plot_panel(
            title=title,
            values=[PanelMetric(metric=metric, metric_labels={"value_type": label}, legend=title)],
            size="half",
        )
    )

alerts = []
for week in pd.date_range("2025-01-06", "2025-12-22", freq="7D"):
    cur = data[data.date.between(week, week + pd.Timedelta(days=6))]
    ref_start = week - pd.Timedelta(days=364 + 14)
    ref = data[data.date.between(ref_start, ref_start + pd.Timedelta(days=34))].sample(
        8000, random_state=1
    )
    report = Report(
        [
            DriftedColumnsCount(columns=INPUTS),
            MAE(),
            MeanError(),
            OutRangeValueCount(column="temp_c", left=-30, right=45),
        ]
    )
    snapshot = report.run(
        current_data=Dataset.from_pandas(cur, data_definition=definition),
        reference_data=Dataset.from_pandas(ref, data_definition=definition),
        timestamp=week.to_pydatetime(),
    )
    ws.add_run(project.id, snapshot, include_data=False)
    values = {m["config"]["type"].split(":")[-1]: m["value"] for m in snapshot.dict()["metrics"]}
    for rule in thresholds:
        metric, label = CHECKS[rule["metric"]]
        v = values[metric][label]
        if v > rule.get("max", float("inf")) or v < rule.get("min", float("-inf")):
            alerts.append(
                {
                    "week": str(week.date()),
                    "check": rule["metric"],
                    "value": round(v, 3),
                    "limits": [rule.get("min"), rule.get("max")],
                    "owner": rule["owner"],
                }
            )

with open(OUT / "alerts.jsonl", "w") as f:
    f.writelines(json.dumps(a) + "\n" for a in alerts)
print(f"52 weekly snapshots in {WORKSPACE}; {len(alerts)} alerts in out/alerts.jsonl\n")
summary = pd.DataFrame(alerts).groupby(["check", "owner"]).week.agg(["count", "min", "max"])
print(summary.rename(columns={"count": "weeks", "min": "first", "max": "last"}).to_string())
print(f"\nDashboard: uv run evidently ui --workspace {WORKSPACE} --port 8000")
