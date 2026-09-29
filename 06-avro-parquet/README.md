# 06 · Avro and Parquet

The checkout terminals of a supermarket chain send one event for each receipt line
(`schemas/sale_event.v1.avsc`, [dataset](../inventory-data/)). In a real system the events go
through a message broker such as Kafka.

**Problem.** Producers and consumers of an event stream are different teams and change at
different times. A producer can send a malformed event, or change the event format in a way
that breaks the consumers weeks later.

**Idea.** Use a data format that has a schema: the writer validates each record against it,
and each change of the schema is checked for compatibility (can old consumers read new data,
and new consumers old data?) before a producer may use it. As a side benefit, binary formats
with a schema are smaller and keep the types.

The writer validates each record against the schema (`avro_demo.py`), and the reader resolves
the differences between the writer's schema and its own schema:

```python
writer(buf, write_schema, rows, codec="deflate", validator=True, strict=True)
buf.seek(0)
return list(reader(buf, reader_schema=read_schema))
```

A compatible change adds a field with a default (`schemas/sale_event.v2.avsc`), so old data
can still be read with the new schema:

```json
{"name": "loyalty_id", "type": ["null", "string"], "default": null}
```

## What the code shows

- `avro_demo.py`:
  1. The writer rejects a text quantity, the unit `lbs` (not in the enum), a missing field,
     and an unknown extra field.
  2. v2 adds an optional field with a default: compatible in both directions. v3 changes the
     type of `quantity` and renames a field: reading fails with `SchemaResolutionError`.
  3. `can_read` does the check of a schema registry (for example, the Confluent Schema
     Registry for Kafka), so an incompatible change fails at the producer, not at the consumer.
- `formats.py`: CSV vs JSON Lines vs Avro vs Parquet. Avro (deflate) is about 6× and Parquet
  about 20× smaller than CSV. CSV changes timestamps to text; only Avro keeps the decimal price.

## Tools

- [fastavro](https://fastavro.readthedocs.io): a fast Python implementation of
  [Apache Avro](https://avro.apache.org), a row-based binary format with a JSON schema, often
  used for Kafka events. Here: validation on write and schema resolution between versions.
- [PyArrow](https://arrow.apache.org/docs/python/): the Python library for Apache Arrow. Here:
  it writes and reads [Apache Parquet](https://parquet.apache.org), a column-based, compressed
  file format with a schema, common for analytics.
- [pandas](https://pandas.pydata.org): data frames. Here: CSV and JSON Lines for comparison.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run avro_demo.py   # validation on write, schema evolution, compatibility check
uv run formats.py     # CSV vs JSON Lines vs Avro vs Parquet: size, speed, types
```
