# 12 · Data cascades

**Slides:** *Poor Data Quality has Consequences* · *Garbage In, Garbage Out: Target Canada* ·
*Raw Data is an Oxymoron* · *Data Quality is a System-Wide Concern* · *Data Cascades* ·
*Common Data Cascades* · *Preview: Inaccurate Data can also be caused by factors other than
drift*. **Paper:** Sambasivan et al., CHI'21 (cascades are compounding, delayed, opaque, and
"practitioners turned to proxy metrics (e.g., accuracy, precision, or F1 score)").

A marimo notebook with a simulation of 4 stores and 20 products for one year
(`inventory_data.sim`). The system forecasts the demand from the recorded sales and reorders
when the stock it believes is on the shelf gets low; the order size comes from the shelf
capacity, computed from the case dimensions in the product master data.

```sh
uv run marimo edit cascades.py
```

Scenarios: **Target Canada** (case dimensions entered in inches or in the wrong field),
**phantom inventory** (theft and damage are not recorded, nobody counts), and both together.
Switches for early fixes: validation at data entry (see `13-data-entry-app`), a rule that
triggers a physical count, and a forecast that skips stock-out days.

What to look for:
- Wrong case dimensions → orders far too large (waste of perishables) or too small (empty
  shelves), like the replenishment problems at Target Canada.
- Phantom inventory compounds: no reorder → empty shelf → zero recorded sales → the forecast
  learns "no demand" → even fewer orders. The system says "in stock" while the shelf is empty.
- The proxy metric (forecast error against the *recorded* sales) gets *better* while the lost
  sales grow to more than half of the demand: goodness-of-fit is not goodness-of-data.
- Sales are not demand. A forecast that skips stock-out days cannot help if the system does
  not know about the stock-outs; the count rule (information from outside the data) does.

## Example answers for "Example for Inventory Mgmt Scenario?"

| Cascade (paper) | Inventory example |
|---|---|
| Interacting with physical world brittleness | checkout scales drift or are not recalibrated; fingerprints and ice on the self-checkout camera; freezer sensors; a heatwave or a pandemic changes demand; a competitor opens; a sugar tax changes what people buy |
| Inadequate application-domain expertise | data scientists treat sales as demand (stock-outs, phantom inventory); returns recorded as negative sales; promotions and holidays; which products substitute for each other; "count" vs "kg" for produce |
| Conflicting reward systems | staff who enter product data or count stock are measured by speed, not accuracy (Target Canada: 75,000 products entered by new staff with little training); cashiers key "misc. produce" to go faster; suppliers gain nothing from correct case dimensions |
| Poor cross-organizational documentation | the POS vendor switches weights to lb, the weather API switches to °F, a supplier changes pack sizes, without notice or documentation; nobody wrote down what `-1` in the stock field means |
