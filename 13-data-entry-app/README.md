# 13 · Data entry with live data quality feedback

**Slides:** *Garbage In, Garbage Out: Target Canada* ("75,000 products entered manually … by
inexperienced staff with minimal training; no data validation rules, the system accepted
anything … wrong units (inches vs. cm), wrong field order") · *Conflicting Reward Systems*
("provide incentives & training"). **Paper:** a practitioner gave field partners "real-time
data quality indicators", and the data quality went up.

A Streamlit form for store staff to enter a new product. The checks run while you type
(`checks.py`):
- **errors** block saving: the Pydantic schema (types, ranges, allowed values), the GTIN
  check digit, a GTIN that already exists, a unit that does not fit the category. The
  supplier comes from a list, so a dangling supplier ID is not possible;
- **warnings** can be saved as "needs review" with the reason: case dimensions that look like
  inches (a full case would be far too heavy for its volume), an implausible weight/volume
  ratio (fields swapped?), and a name that is very similar to an existing product.

The scorecard tab shows, for each person, how many entries needed a review. It makes the data
work visible (and a reason for training, not blame).

```sh
uv run streamlit run app.py   # then open http://localhost:8501
uv run pytest                 # AppTest: fills in the form without a browser
```

Try the Target Canada mistake: enter a produce item with a case of 19.9 × 13 × 10.6 (inches),
18 units of 1 kg, and the name "Bananas Organic".
