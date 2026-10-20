# 06 · Avro and Parquet

**Slides:** *Apache Avro (e.g. for Kafka)* · *Many Schema Libraries/Formats*

The checkout terminals of the supermarket send one event for each line of a receipt
([dataset](../inventory-data/), table `pos_events`). In a real system these events go through
a message queue such as Kafka, and a schema registry stores the schemas. This folder has the
Avro schema of the event in three versions (`schemas/sale_event.v1.avsc` to `v3`), a script
about schemas on write and schema evolution (`avro_demo.py`), and a comparison of file formats
(`formats.py`).

**Problem.** Many producers and consumers exchange the same events, and each team changes its
code at its own pace. In a format without a schema (CSV, JSON), a terminal can send a quantity
as text or a new unit, and the error shows up much later at a consumer. When a producer adds,
renames, or retypes a field, consumers break, often without a clear error.

**Idea.** Write a schema for the events and check every record against it when it is written.
Avro stores the schema with the data, and a reader can use a newer or older schema: Avro
resolves the differences by field name and fills in defaults. A schema registry tests each new
version for compatibility before a producer may use it. Formats with a schema also keep the
types and store the data more compactly.

Version 1 of the schema (`schemas/sale_event.v1.avsc`, trimmed). Version 2 adds an optional
field `loyalty_id` with the default `null`:

```json
{"type": "record", "name": "SaleEvent", "namespace": "supermarket.pos",
 "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "event_time", "type": {"type": "long", "logicalType": "timestamp-millis"}},
    {"name": "quantity", "type": "double"},
    {"name": "unit", "type": {"type": "enum", "name": "Unit", "symbols": ["count", "kg", "liter"]}},
    {"name": "unit_price", "type": {"type": "bytes", "logicalType": "decimal", "precision": 8, "scale": 2}},
    {"name": "promo", "type": "boolean", "default": false}]}
```

All checks in `avro_demo.py` write records with one schema and read them with another:

```python
def roundtrip(rows: list[dict], write_schema: dict, read_schema: dict) -> list[dict]:
    buf = io.BytesIO()
    writer(buf, write_schema, rows, codec="deflate", validator=True, strict=True)
    buf.seek(0)
    return list(reader(buf, reader_schema=read_schema))
```

## What the code shows

- `avro_demo.py`, on the first 5 POS events:
  1. **Validation on write.** The writer rejects all 4 bad records: a quantity as text
     (`'fifty'`), the unit `lbs` (not in the enum), a record without `store_id`, and a record
     with an unknown extra field `cashier` (because of `strict=True`).
  2. **Compatible change.** Version 2 adds an optional field with a default. A v2 reader reads
     v1 data (`loyalty_id = None`), and a v1 reader reads v2 data (it skips the new field).
  3. **Incompatible change.** Version 3 changes the type of `quantity` to text and renames
     `terminal_id` to `register_id`. A v3 reader fails on v1 data with
     `SchemaResolutionError: Schema mismatch: double is not string`.
  4. **Compatibility check of a registry.** The function `can_read` tests both directions
     (new reads old, old reads new), as a schema registry such as the Confluent Schema
     Registry does. v2 passes both and is registered; v3 fails both and is rejected. The
     incompatible change fails at the producer, before any consumer reads the data.
- `formats.py`, on 64,560 POS events (the 3,228 events of the dataset, 20 times):
  1. **Size.** CSV 5.31 MB, JSON Lines 11.96 MB, Avro with deflate 0.91 MB (about 6× smaller
     than CSV), Parquet with zstd 0.27 MB (about 20× smaller). Parquet also writes and reads
     fastest here (about 20 ms and 5 ms; CSV about 300 ms and 50 ms).
  2. **Types after reading back.** From CSV, `event_time` comes back as text; JSON Lines,
     Avro, and Parquet return a timestamp. Only Avro keeps `unit_price` as an exact decimal
     (`object`, Python `Decimal`); the others return a float.
  3. **Schema in the file.** Parquet stores the schema in the file, for example
     `event_time: timestamp[us, tz=UTC]` and `quantity: double`.

## Tools

- [Apache Avro](https://avro.apache.org) with [fastavro](https://fastavro.readthedocs.io): a
  row-based binary format with a schema in JSON, common for messages in Kafka; fastavro is a
  fast Python implementation. Here: validation on write, schema evolution, and one of the
  file formats.
- [Apache Parquet](https://parquet.apache.org) with [PyArrow](https://arrow.apache.org/docs/python/):
  a compressed, column-based file format for analytics. Here: the smallest of the four files
  and its stored schema.
- [pandas](https://pandas.pydata.org): data frames. Here: writes and reads CSV, JSON Lines,
  and Parquet.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run avro_demo.py   # validation on write, schema evolution, compatibility check
uv run formats.py     # CSV, JSON Lines, Avro, Parquet: size, speed, types (files in out/)
```
