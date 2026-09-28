# 07 · Schema checks after loading

**Slides:** *Schema Checks after Loading* (Great Expectations) · *Data Schema* ("protects against
change; explicit interface between components") · *What Happens When New Data Violates Schema?*
· *Detecting Data Drift* ("distributions can be manually specified or learned")

```sh
uv run gx_validate.py       # Great Expectations on one month of delivery records
uv run pandera_validate.py  # Pandera schema for the product master data, with a quarantine
```

`gx_validate.py` translates the expectations from the slide to the current GX Core 1.x API
(`gx.expectations.ExpectColumnValuesToBeOfType(column="quantity", type_="float64")` instead of
`expect_column_values_to_be_of_type("quantity", "float")`) and adds checks of the distribution
(median, standard deviation, maximum) and of combinations of columns. It validates a clean month
of deliveries (all pass) and the same month as typed in by the receiving clerks (7 of 14
fail: negative quantities, the 80,000 kg banana delivery, unit spellings, a supplier name in
the category column, the placeholder date 1900-01-01, duplicate deliveries). Note that a unique
`delivery_id` does not mean unique deliveries. The HTML report is in `out/gx_docs/index.html`.

`pandera_validate.py`:
1. The schema is a Python class (`ProductMaster`) with types, ranges, allowed values, a GTIN
   check digit, and a check across columns (produce is sold by count or kg).
2. Lazy validation collects all failures. The bad rows go to `out/quarantine.csv` with a reason,
   the good rows go on. A value that cannot be converted hides the other checks on that
   column, so the script validates again until the rest passes.
3. `@pa.check_types` makes the schema the interface of a function: bad input fails at the call.
4. `infer_schema` learns ranges from February and checks March. The learned bounds find the
   errors, but also flag normal values that are only a bit larger than before.

Most problems that are left (case dimensions in inches, a price that is too low, near-duplicate
products) are plausible values one by one. They need rules across rows and tables (`08`) or
statistical detection (`09`).
