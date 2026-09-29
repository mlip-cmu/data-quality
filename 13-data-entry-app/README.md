# 13 · Data entry with live data quality feedback

Store staff of a supermarket chain enter new products into the catalog
([dataset](../inventory-data/)). The forecasts and the orders depend on this data, for example
on the case dimensions (see [`12-data-cascades`](../12-data-cascades/)).

**Problem.** Manual data entry without validation accepts anything: dimensions in inches in a
cm field, values in the wrong field, a GTIN with a typo, a second entry for a product that
already exists. The people who enter the data do not see the consequences, and their work is
measured by speed, not by quality.

**Idea.** Check each entry while the person types it, and show the result next to the form.
Errors that are certain block saving; plausible but suspicious values are warnings, and the
entry is saved as "needs review" with the reason. A scorecard makes the quality of each
person's data work visible.

Hard rules are a Pydantic model; if it fails, the entry cannot be saved (`checks.py`):

```python
class NewProduct(BaseModel):
    gtin: str = Field(pattern=r"^\d{13}$", description="13 digits, with the leading zero")
    unit: Literal["count", "kg", "liter"]
    unit_price: float = Field(gt=0, le=500)
    case_length_cm: float = Field(gt=0, le=200)
    ...
```

A plausibility check finds dimensions in inches: if a full case is far too heavy for its
volume, but plausible after a conversion from inches to cm, the app shows a warning:

```python
volume_l = p.case_length_cm * p.case_width_cm * p.case_height_cm / 1000
density = p.unit_weight_kg * p.case_pack / volume_l
if density > 3 * typical and density / 2.54**3 < 3 * typical:
    found.append(Finding("warning", "case dimensions", "... look like inches, not cm ..."))
```

## What the code shows

- `app.py`: a form with a "Data quality check" panel that updates after each change.
  - Errors: schema violations, a wrong GTIN check digit, a GTIN that already exists, a unit that
    does not fit the category.
  - Warnings: dimensions that look like inches, an implausible weight/volume ratio (fields
    swapped?), and a name that is very similar to an existing product.
  - The supplier comes from a list, so a supplier that does not exist cannot be entered.
  - The scorecard tab shows for each person how many entries needed a review.
- `test_app.py`: fills in the form without a browser and checks the errors, the warnings, and
  the saved entries.

Try it: enter a produce item with a case of 19.9 × 13 × 10.6 (inches), 18 units of 1 kg, and
the name "Bananas Organic".

## Tools

- [Streamlit](https://streamlit.io): builds interactive web apps from Python scripts. Here: the
  form and the scorecard; `AppTest` tests the app without a browser.
- [Pydantic](https://docs.pydantic.dev): data validation with Python type hints. Here: the
  hard rules for a new product.
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz): fast fuzzy string matching. Here: it
  finds possible duplicates of existing products.
- [pandas](https://pandas.pydata.org): data frames. Here: the catalog and the saved entries.
- [pytest](https://pytest.org): the Python test framework. Here: it runs the app tests.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run streamlit run app.py   # then open http://localhost:8501
uv run pytest                 # AppTest fills in the form without a browser
```
