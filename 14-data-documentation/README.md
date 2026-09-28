# 14 · Data documentation and defensive monitoring

**Slides:** *Data Documentation* · *Data Quality is a System-Wide Concern* ("documentation at
the interfaces is important") · *Data Quality Documentation* ("teams rarely document
expectations of data quantity or quality … some teams adopt defensive monitoring: local tests
about assumed structure and distribution of data; identify drift early and reach out to
producing teams") · *Data Card* · *Entries in data card* · *Poor Cross-organizational
Documentation* (paper: "collaborators changing schema without understanding context")

```sh
uv run datacard_stats.py   # update the generated statistics in DATACARD.md
uv run pytest              # the forecasting team's checks of each new POS batch
```

- `DATACARD.md` documents the dataset of this repository with the sections of Google's Data
  Cards (creator and purpose, how to use, fields with units, an example datapoint, sources and
  their reliability, the "labeling process", distributions, noise, drift, biases, curation).
  The distribution section is generated from the data, so it stays correct. Note the
  labeling section: the label is the recorded sales, which is a proxy for demand.
- `pos_checks.py` + `tests/`: the consumer (the forecasting team) writes down what it assumes
  about the data it receives from the POS team: a Pandera schema for the structure, and a
  distribution check against the same month of the last year. The tests show that the POS
  update to lb passes the schema (the types and ranges do not change) but fails the
  distribution check for stores 7 and 8, so the forecasting team can call the POS team before
  the bad data reaches the model. The same checks find the POS outage (missing store-days)
  and the double upload (duplicate keys).
