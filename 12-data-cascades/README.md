# 12 · Data cascades

**Slides:** *Poor Data Quality has Consequences* · *Garbage In, Garbage Out: Target Canada* ·
*Raw Data is an Oxymoron* · *Data Quality is a System-Wide Concern* · *Data Cascades* ·
*Common Data Cascades* · *Preview: Inaccurate Data can also be caused by factors other than
drift*. **Paper:** Sambasivan et al., CHI'21 (cascades are compounding, delayed, opaque, and
"practitioners turned to proxy metrics (e.g., accuracy, precision, or F1 score)").

A simulation of 4 stores and 20 products for one year (`inventory_data.sim`). The system
forecasts the demand from the recorded sales and reorders when the stock it believes is on
the shelf gets low. The order size comes from the shelf capacity, which the system computes
from the case dimensions in the product master data.

## What this project illustrates

| Point | Where to see it in `cascades.ipynb` |
|---|---|
| Garbage in, garbage out: Target Canada | Scenario "Target Canada": case dimensions entered in inches or in the wrong field. The orders are far too large (perishables spoil) or too small (empty shelves). |
| Data cascades are compounding | Scenario "phantom inventory": theft and damage are not recorded and nobody counts. No reorder → empty shelf → zero recorded sales → the forecast learns "no demand" → fewer orders. Lost sales increase to more than half of the demand. |
| Data cascades are opaque; proxy metrics hide them | The forecast error against the *recorded* sales becomes *better* while the lost sales increase: goodness-of-fit is not goodness-of-data. |
| Raw data is an oxymoron: sales are not demand | On days with a stock-out, the sales show the stock, not the demand. A forecast that skips stock-out days does not help when the system does not know about the stock-outs. |
| Early interventions are cheap | The table "All scenarios": validation at data entry (see `13-data-entry-app`), a rule that starts a physical count, and a forecast that knows about stock-outs. |
| Data quality is a system-wide concern | Each fix works at a different interface: data entry, store operations, and the model. |

## Run

Open `cascades.ipynb` on GitHub to see the outputs. To select a scenario and the fixes
(parameter cell at the top) and run it again:

```sh
uv run jupyter lab cascades.ipynb
```

## Example answers for "Example for Inventory Mgmt Scenario?"

| Cascade (paper) | Inventory example |
|---|---|
| Interacting with physical world brittleness | checkout scales drift or are not recalibrated; fingerprints and ice on the self-checkout camera; freezer sensors; a heatwave or a pandemic changes demand; a competitor opens; a sugar tax changes what people buy |
| Inadequate application-domain expertise | data scientists treat sales as demand (stock-outs, phantom inventory); returns recorded as negative sales; promotions and holidays; which products substitute for each other; "count" vs "kg" for produce |
| Conflicting reward systems | staff who enter product data or count stock are measured by speed, not accuracy (Target Canada: 75,000 products entered by new staff with little training); cashiers key "misc. produce" to go faster; suppliers gain nothing from correct case dimensions |
| Poor cross-organizational documentation | the POS vendor switches weights to lb, the weather API switches to °F, a supplier changes pack sizes, without notice or documentation; nobody wrote down what `-1` in the stock field means |
