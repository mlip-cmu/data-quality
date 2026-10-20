# 12 · Data cascades

**Slides:** *Poor Data Quality has Consequences* · *Garbage In, Garbage Out: Target Canada* ·
*Raw Data is an Oxymoron* · *Data Quality is a System-Wide Concern* · *Data Cascades* ·
*Common Data Cascades* · *Preview: Inaccurate Data can also be caused by factors other than
drift*. **Paper:** Sambasivan et al., CHI'21 (cascades are compounding, delayed, opaque, and
"practitioners turned to proxy metrics (e.g., accuracy, precision, or F1 score)").

The notebook `cascades.ipynb` simulates 4 stores of the supermarket chain and 20 products for
one year (`inventory_data.sim`, see [dataset](../inventory-data/)). Every day the system
forecasts the demand from the recorded sales of the last four weeks, and reorders when the stock
in its database is low. The order size comes from the shelf capacity, which the system computes
from the case dimensions in the product master data.

**Problem.** A small data error at one place of the system can grow into a large business
problem somewhere else, weeks later. Before Target Canada opened its stores in 2013, new staff
entered the data of 75,000 products by hand, with many wrong case dimensions. After the opening,
the warehouses were full and the shelves were empty. Such cascades compound over time, and the
usual model metrics do not show them.

**Idea.** Follow the data through the whole loop: data entry, store operations, the forecast,
and the orders. Measure the outcome that matters (lost sales, waste), next to the model metric.
Add cheap checks early and at each interface: validate the master data at entry, count the shelf
when the data looks suspicious, and leave known stock-out days out of the forecast.

The parameter cell at the top of the notebook selects the scenario and the fixes:

```python
SCENARIO = "everything at once"
# "clean data", "Target Canada: wrong case dimensions", "phantom inventory",
# or "everything at once"
VALIDATE = False  # validate the product master data at entry (see 13)
COUNT_RULE = False  # rule: no sales for 3 days but stock in the system -> count
CENSORED = False  # forecast only from days without a stock-out that the system knows about
```

## What the notebook shows

Open `cascades.ipynb` on GitHub to see the outputs. The committed run uses "everything at once"
without fixes; the table "All scenarios" runs every combination (yearly averages):

| scenario | fixes | lost sales (% of demand) | waste (% of sales) | forecast error vs recorded sales | in stock in the system, shelf empty (%) |
|---|---|---|---|---|---|
| clean data | none | 0.56 | 5.51 | 4.98 | 0.18 |
| Target Canada | none | 5.03 | 33.34 | 4.72 | 0.82 |
| Target Canada | validate | 0.56 | 5.51 | 4.98 | 0.18 |
| phantom inventory | none | 65.07 | 1.08 | 2.31 | 68.42 |
| phantom inventory | count rule | 9.38 | 2.95 | 5.12 | 19.33 |
| phantom inventory | count rule, censored | 9.37 | 2.95 | 5.12 | 19.39 |
| everything at once | none | 63.79 | 2.87 | 2.13 | 72.21 |
| everything at once | all three | 9.37 | 2.95 | 5.12 | 19.39 |

1. **Garbage in, garbage out: Target Canada.** Case dimensions of 5 products are entered in
   inches (read as cm), and those of 5 others have a wrong height. With inches, the system
   computes about 16 times more cases on the shelf and orders far too much: waste rises from
   5.51 % to 33.34 % of sales (perishables spoil). Dimensions that are too large give small
   orders and empty shelves: lost sales rise from 0.56 % to 5.03 %.
2. **Data cascades are compounding.** In the scenario "phantom inventory", theft and damage are
   not recorded and nobody counts the shelves. The database shows stock, so the system does not
   reorder; the shelf is empty, the recorded sales drop to zero, the forecast learns "no
   demand", and the system orders even less. In the committed run, lost sales grow over the
   year to more than 80 % of the demand per week (65.07 % on average for phantom inventory).
3. **Opaque cascades and proxy metrics.** The forecast error against the *recorded* sales gets
   *better* while lost sales grow: 2.31 for phantom inventory against 4.98 with clean data (in
   the committed run it drops from about 5 to below 1 per week). Zero sales are easy to predict.
   Goodness-of-fit is a different property from goodness-of-data.
4. **Raw data is an oxymoron: recorded sales differ from demand.** On days with a stock-out, the
   sales equal what was on the shelf, and the demand stays unknown. A forecast that skips the
   stock-out days (`CENSORED`) changes almost nothing (9.38 % → 9.37 % lost sales), because the
   database does not contain most stock-outs. The fix comes from outside the data.
5. **Early interventions are cheap.** Validation at data entry (see
   [13](../13-data-entry-app/)) brings Target Canada back to the clean result. A rule that
   starts a physical count after 3 days without sales cuts lost sales from 65.07 % to 9.38 %.
6. **Data quality is a system-wide concern.** Each fix works at a different interface: data
   entry, store operations, and the model.

## Tools

- `inventory_data.sim` and `inventory_data.master` ([dataset](../inventory-data/)): a daily
  inventory simulation (demand, true and recorded stock, orders, deliveries, spoilage) and the
  master data of stores, products, and suppliers.
- [pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org): data frames and arrays.
  Here: the ordering policy, the forecasts, and the weekly metrics.
- [Altair](https://altair-viz.github.io) with
  [vl-convert](https://github.com/vega/vl-convert): declarative charts, as PNG images. Here:
  the four weekly metrics of the clean and the selected run.
- [Jupyter](https://jupyter.org): notebooks with code and outputs.

## Run

Open `cascades.ipynb` on GitHub to see the outputs. To select a scenario and the fixes
(parameter cell at the top) and run it again, with [uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab cascades.ipynb
```

## Example answers for "Example for Inventory Mgmt Scenario?"

| Cascade (paper) | Inventory example |
|---|---|
| Interacting with physical world brittleness | checkout scales drift or are not recalibrated; fingerprints and ice on the self-checkout camera; freezer sensors; a heatwave or a pandemic changes demand; a competitor opens; a sugar tax changes what people buy |
| Inadequate application-domain expertise | data scientists treat sales as demand (stock-outs, phantom inventory); returns recorded as negative sales; promotions and holidays; which products substitute for each other; "count" vs "kg" for produce |
| Conflicting reward systems | staff who enter product data or count stock are measured by speed, and nobody measures their accuracy (Target Canada: 75,000 products entered by new staff with little training); cashiers key "misc. produce" to go faster; suppliers gain nothing from correct case dimensions |
| Poor cross-organizational documentation | the POS vendor switches weights to lb, the weather API switches to °F, a supplier changes pack sizes, without notice or documentation; nobody wrote down what `-1` in the stock field means |
