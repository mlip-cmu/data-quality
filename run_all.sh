#!/usr/bin/env bash
# Run the demos of all projects (or only the folders given as arguments), as the CI does.
set -euo pipefail
cd "$(dirname "$0")"
export DO_NOT_TRACK=1 MPLBACKEND=Agg

# Notebooks run in place: the outputs are committed, so they can be read on GitHub.
notebook() { uv run jupyter nbconvert --to notebook --execute --inplace "$1"; }

demo() {
  case "$1" in
    inventory-data) uv run inventory-data && uv run pytest -q ;;
    01-*) notebook accuracy_precision.ipynb ;;
    02-*) uv run scorecard.py ;;
    03-*) uv run load.py && uv run sqlite_contrast.py ;;
    04-*) uv run pitfalls.py && uv run validate.py ;;
    05-*) uv run extract.py --replay && uv run api.py && uv run extract_anthropic.py ;;
    06-*) uv run avro_demo.py && uv run formats.py ;;
    07-*) uv run gx_validate.py && uv run pandera_validate.py ;;
    08-*) uv run rules.py && uv run repair.py ;;
    09-*) uv run anomalies.py && uv run patterns.py && uv run duplicates.py \
            && uv run learn_from_repairs.py ;;
    10-*) notebook drift_detection.ipynb && uv run evidently_reports.py ;;
    11-*) notebook retraining.ipynb && uv run monitor.py ;;
    12-*) notebook cascades.ipynb ;;
    13-*) uv run pytest -q ;;
    14-*) uv run datacard_stats.py && uv run pytest -q ;;
    *) echo "unknown project: $1" >&2; return 1 ;;
  esac
}

projects=("$@")
[ ${#projects[@]} -eq 0 ] && projects=(inventory-data [0-9][0-9]-*/)
for p in "${projects[@]}"; do
  p=${p%/}
  echo "=== $p ==="
  (cd "$p" && mkdir -p out && uv sync --locked -q && demo "$p")
done
