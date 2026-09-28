# 13 · Data entry with live data quality feedback

**Slides:** *Garbage In, Garbage Out: Target Canada* · *Conflicting Reward Systems*.
**Paper:** field partners got real-time data quality indicators, and the data quality went up.

A Streamlit form for store staff to enter a new product. The checks (`checks.py`) run again
after each change of a field.

## What this project illustrates

| Point | Where to see it |
|---|---|
| Validate data at entry (Target Canada had no validation rules) | Errors block saving: the Pydantic schema (types, ranges, allowed values), the GTIN check digit, a GTIN that already exists, a unit that does not fit the category. |
| Prevent errors by design | The supplier comes from a list, so a supplier ID that does not exist is not possible. |
| Wrong units (inches vs cm) and wrong field order | Warnings: case dimensions that look like inches (a full case is far too heavy for its volume), and an implausible weight/volume ratio (fields swapped). |
| Near-duplicate products | Warning: a name that is very similar to an existing product (rapidfuzz). |
| Plausible but suspicious data goes to a human | Entries with warnings can be saved as "needs review", with the reason. |
| Real-time data quality indicators for the people who collect the data | The panel "Data quality check" next to the form shows the errors and warnings for each field, and updates after each change. |
| Make data work visible (conflicting reward systems) | The scorecard tab shows for each person how many entries needed a review: a reason for training, not blame. |

## Run

```sh
uv run streamlit run app.py   # then open http://localhost:8501
uv run pytest                 # AppTest fills in the form without a browser
```

Try the Target Canada mistake: enter a produce item with a case of 19.9 × 13 × 10.6 (inches),
18 units of 1 kg, and the name "Bananas Organic".
