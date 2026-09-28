# 14 · Data documentation and defensive monitoring

**Slides:** *Data Documentation* · *Data Quality is a System-Wide Concern* · *Data Quality
Documentation* · *Data Card* · *Entries in data card* · *Poor Cross-organizational
Documentation*

## What this project illustrates

| Point | Where to see it |
|---|---|
| A data card | `DATACARD.md`: the dataset of this repository with the sections of a data card (creator and purpose, how to use, fields with units, an example datapoint, sources and their reliability, labeling, distributions, noise, drift, biases, curation). |
| The label is often a proxy | `DATACARD.md`, labeling: the label is the recorded sales, a proxy for demand. |
| Documentation that stays correct | `datacard_stats.py` generates the statistics section of `DATACARD.md` from the data. |
| Document expectations at the interface | `pos_checks.py`: the consumer (the forecasting team) writes down what it assumes about the POS data: a Pandera schema for the structure and a distribution check against the same month of the last year. |
| Defensive monitoring: local tests of structure and distribution | `tests/test_incoming_pos_data.py`: the tests run on each new batch before training. |
| A schema change without notice (poor cross-organizational documentation) | The POS update to lb passes the schema (the types and ranges do not change) but fails the distribution check for stores 7 and 8, so the forecasting team can call the POS team before the bad data reaches the model. |
| The same tests find other problems | The POS outage (missing store-days) and the double upload (duplicate keys). |

## Run

```sh
uv run datacard_stats.py   # update the generated statistics in DATACARD.md
uv run pytest              # the checks of the forecasting team on each new POS batch
```
