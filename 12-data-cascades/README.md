# 12 · Data cascades

A simulation of a supermarket chain with 4 stores and 20 products for one year
([`inventory_data.sim`](../inventory-data/)). Every day the system forecasts the demand from
the **recorded** sales of the last four weeks, and reorders when the stock that it *believes*
is on the shelf gets low. The order size depends on the shelf capacity, which the system
computes from the case dimensions in the product master data.

**Problem.** A small data problem at one place can cause large problems later at another
place (a *data cascade*). Case dimensions typed in inches instead of cm give wrong order sizes.
Theft that nobody records makes the system believe that the shelf is full, so it does not
reorder; the empty shelf gives zero sales, and the forecast learns that there is no demand.
The metric that the data scientists see (the forecast error against the recorded sales) does
not show the problem: it even gets better.

**Idea.** Simulate the whole loop and compare the scenarios with cheap, early fixes at
different interfaces of the system: validation of the master data at entry, a rule that
starts a physical count when the data looks suspicious, and a forecast that knows about
stock-outs. Measure the real outcome (lost sales, waste), not only the model metric.

The count rule uses information from outside the data: when a product with expected demand has
no sales for three days while the system shows stock, staff count the shelf, and the system
stock is corrected (`cascades.ipynb`):

```python
if count_rule:
    quiet[:] = np.where((o["sales"][d] == 0) & (inv.system > 0) & (f > 0.5), quiet + 1, 0)
    recount = quiet >= 3
    inv.system[recount] = inv.true[recount]
```

The reorder decision uses the stock that the system believes, so an error in the data
becomes a wrong decision in the store:

```python
position = inv.system + inv.on_order()
reorder_point = f * (lead + 1) * 1.3
return np.where(position < reorder_point, target - position, 0)
```

## What the code shows (`cascades.ipynb`)

- **Wrong master data** (case dimensions in inches or in the wrong field): the orders are far
  too large (perishables spoil) or too small (empty shelves). Validation at entry prevents it.
- **Phantom inventory** (unrecorded theft, no counts): the problem compounds. Lost sales
  increase to more than half of the demand, while the system says "in stock".
- The forecast error against the *recorded* sales gets *better* while the lost sales increase:
  a good fit to the data is not the same as good data.
- **Sales are not demand:** on days with a stock-out, the sales show the stock, not the demand.
  A forecast that skips stock-out days does not help when the system does not know about
  them; the count rule does.
- The table "All scenarios" compares each scenario with and without the fixes.

## Examples of data cascades in inventory management

The four types of data cascades from Sambasivan et al.,
["Everyone wants to do the model work, not the data work"](https://research.google/pubs/everyone-wants-to-do-the-model-work-not-the-data-work-data-cascades-in-high-stakes-ai/)
(CHI 2021):

| Cause of the cascade | Inventory example |
|---|---|
| Interacting with physical world brittleness | checkout scales drift or are not recalibrated; fingerprints and ice on the self-checkout camera; freezer sensors; a heatwave or a pandemic changes demand; a competitor opens; a sugar tax changes what people buy |
| Inadequate application-domain expertise | data scientists treat sales as demand (stock-outs, phantom inventory); returns recorded as negative sales; promotions and holidays; which products substitute for each other; "count" vs "kg" for produce |
| Conflicting reward systems | staff who enter product data or count stock are measured by speed, not accuracy (Target Canada: 75,000 products entered by new staff with little training); cashiers key "misc. produce" to go faster; suppliers gain nothing from correct case dimensions |
| Poor cross-organizational documentation | the POS vendor switches weights to lb, the weather API switches to °F, a supplier changes pack sizes, without notice or documentation; nobody wrote down what `-1` in the stock field means |

## Tools

- [NumPy](https://numpy.org) and [pandas](https://pandas.pydata.org): arrays and data frames.
  Here: the day-by-day simulation (`inventory_data.sim`) and the weekly results.
- [Altair](https://altair-viz.github.io): declarative charts, saved as PNG with
  [vl-convert](https://github.com/vega/vl-convert).
- [Jupyter](https://jupyter.org) (JupyterLab, nbconvert): the notebook, committed with its
  outputs.

## Run

Open `cascades.ipynb` on GitHub to see the outputs. To select a scenario and the fixes
(parameter cell at the top) and run it again, with [uv](https://docs.astral.sh/uv/):

```sh
uv run jupyter lab cascades.ipynb
```
