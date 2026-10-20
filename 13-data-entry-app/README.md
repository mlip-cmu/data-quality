# 13 · Data entry with live data quality feedback

**Slides:** *Garbage In, Garbage Out: Target Canada* · *Conflicting Reward Systems*.
**Paper:** field partners got real-time data quality indicators, and the data quality went up.

When the supermarket chain lists a new product, store staff type its master data into a
form: name, GTIN (the 13-digit barcode number), category, unit, price, supplier, case size,
and weight. This folder has that form as a [Streamlit](https://streamlit.io) web app
(`app.py`) with the checks in `checks.py`. The checks run again after each change of a field.

**Problem.** Target Canada filled its new systems by hand, without validation rules, and
much of the product data was wrong: dimensions in inches in fields for centimeters, fields
in the wrong order, typos. The replenishment system computed shelf space and orders from
this data, so the shelves were empty or overfull. The people who collect data are often
rewarded for speed, and they rarely see what their errors cause later (conflicting reward
systems).

**Idea.** Check the data at entry, while the person who knows the product is still at the
form. Errors that are certain (wrong type, bad check digit, a GTIN that already exists) block
saving. Values that are only implausible produce a warning; the entry can still be saved,
with the status "needs review" and the reason, so that a data steward looks at it. Show the
result of the checks next to the form after each change, and make the quality of each
person's entries visible.

The plausibility check in `checks.py` computes how heavy a full case would be per liter and
compares it with a typical density for the category (0.45 kg per liter for produce):

```python
volume_l = p.case_length_cm * p.case_width_cm * p.case_height_cm / 1000
density = p.unit_weight_kg * p.case_pack / volume_l
typical = DENSITY_KG_PER_L[p.category]
if density > 3 * typical and density / 2.54**3 < 3 * typical:
    found.append(Finding("warning", "case dimensions", ...))  # looks like inches
elif not typical / 4 < density < 4 * typical:
    found.append(Finding("warning", "case dimensions", ...))  # fields swapped?
```

## What the code shows

The function `check` in `checks.py` returns a list of findings (level, field, message) for
one entry. The numbers below come from calling it with the 60 products of the dataset.

1. **Schema errors block saving.** A Pydantic model `NewProduct` defines the types, ranges,
   and allowed values (for example a GTIN of exactly 13 digits, 1 to 200 units per case,
   a shelf life of 1 to 1,825 days). A GTIN with 12 digits fails with "String should match
   pattern '^\d{13}$'", and the button "Save" is disabled. Target Canada had no such rules.
2. **Rules beyond the schema also block saving.** A GTIN with a wrong last digit fails the
   check digit test ("the check digit is wrong (typo?)"). A GTIN that is already in the
   catalog fails ("this GTIN already belongs to 'Banana'"). A produce item sold by the liter
   fails ("produce is sold by count or kg").
3. **Errors prevented by design.** The supplier is a dropdown list of the 12 suppliers, so a
   supplier ID that does not exist cannot be entered.
4. **Wrong units.** The Target Canada mistake: a produce case of 19.9 × 13 × 10.6 with 18
   units of 1 kg. In cm, a full case would weigh 6.6 kg per liter, more than 3 times the
   typical 0.45. Converted from inches (× 2.54), the density is in the normal range, so the
   warning suggests 51 × 33 × 27 cm.
5. **Wrong field order.** A density far from the typical value for the category (outside a
   factor of 4) gives the warning "fields swapped?". For example, 27 kg per unit and a case
   height of 1 cm give 294.55 kg per liter for produce.
6. **Near-duplicate products.** [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) compares
   the name with all product names. "Bananas Organic" is 97 % similar to "Organic Banana"
   (product 104), so the form shows a warning.
7. **Suspicious data goes to a human.** An entry with only warnings can be saved. The app
   appends it to `out/entries.csv` with the status "needs review" and the warning messages.
8. **Real-time indicators.** The panel "Data quality check" next to the form lists the errors
   and warnings per field, or "All checks pass", and it updates after each change.
9. **Visible data work.** The tab "Data quality scorecard" counts, for each person, the
   entries that were accepted and those that needed a review, and the share accepted without
   review. The data work of each person becomes visible, as a starting point for training.

`test_app.py` fills in the form without a browser and checks four cases: a good product is
accepted and saved, inch dimensions get a warning, a short GTIN disables "Save", and "Bananas
Organic" is flagged as a possible duplicate. All 4 tests pass.

## Tools

- [Streamlit](https://streamlit.io): a Python library for small web apps; each change of a
  widget runs the script again. Here: the form, the check panel, and the scorecard.
  [`AppTest`](https://docs.streamlit.io/develop/api-reference/app-testing) runs the app in a
  test without a browser.
- [Pydantic](https://docs.pydantic.dev): data validation with Python type hints. Here: the
  schema `NewProduct` with types, ranges, and allowed values.
- [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz): fast fuzzy string matching. Here: the
  most similar existing product name (`token_sort_ratio`, warning at 80 % or more).
- [pandas](https://pandas.pydata.org): data frames. Here: the product catalog and the saved
  entries.
- [pytest](https://docs.pytest.org): a test framework. Here: runs the four `AppTest` cases.
- [`inventory-data`](../inventory-data/): the shared dataset. Here: the product catalog, the
  suppliers, the GTIN check digit, and the typical density per category.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run streamlit run app.py   # then open http://localhost:8501
uv run pytest                 # AppTest fills in the form without a browser
```

Try the Target Canada mistake: enter a produce item with a case of 19.9 × 13 × 10.6 (inches),
18 units of 1 kg, and the name "Bananas Organic".
