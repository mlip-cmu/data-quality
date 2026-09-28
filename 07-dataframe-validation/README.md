# 07 · Schema checks after loading

**Slides:** *Schema Checks after Loading* · *Data Schema* · *What Happens When New Data
Violates Schema?* · *Detecting Data Drift* (distributions can be specified or learned)

## What this project illustrates

| Point | Where to see it |
|---|---|
| Schema checks after loading, with Great Expectations | `gx_validate.py`: the expectations from the slide (types, a unique ID, a range, a value set) as GX Core 1.x classes, on one month of delivery records. |
| More expectations on the same batch | `gx_validate.py`: known suppliers and categories, a date range, `entered_at` ≥ `received_at`, unique combinations of columns, and the median, standard deviation, and maximum of the quantity. |
| Clean data passes, entered data does not | `gx_validate.py`: the clean month passes all checks. The same month as typed in by the clerks fails 7 of 14: negative quantities, the 80,000 kg banana delivery, unit spellings, a supplier name in the category column, the placeholder date 1900-01-01, and duplicate deliveries. |
| A unique ID does not mean unique records | `gx_validate.py`: `delivery_id` is unique, but the same delivery is in the data two times. |
| A human-readable validation report | `out/gx_docs/index.html` (GX Data Docs). |
| A schema as a Python class | `pandera_validate.py`, step 1: `ProductMaster` with types, ranges, allowed values, the GTIN check digit, and a check across columns (produce is sold by count or kg). |
| Quarantine instead of stop | `pandera_validate.py`, step 2: lazy validation collects all failures; bad rows go to `out/quarantine.csv` with a reason, good rows go on. |
| The schema as the interface of a function | `pandera_validate.py`, step 3: `@pa.check_types` rejects bad input at the call. |
| Learned (inferred) schemas | `pandera_validate.py`, step 4: `infer_schema` learns ranges from February and checks March. The learned bounds find the errors, but also flag normal values that are only a bit larger. |
| The limits of schema checks | Plausible single values (case dimensions in inches, a price that is too low, near-duplicate products) pass. See `08` and `09`. |

## Run

```sh
uv run gx_validate.py       # Great Expectations on one month of delivery records
uv run pandera_validate.py  # Pandera schema for the product master data, with a quarantine
```
