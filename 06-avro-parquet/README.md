# 06 · Avro and Parquet

**Slides:** *Apache Avro (e.g. for Kafka)* · *Many Schema Libraries/Formats*

The checkout terminals send one event for each receipt line (`schemas/sale_event.v1.avsc`).
In a real system these events go through Kafka, and a schema registry keeps the schemas.

## What this project illustrates

| Point | Where to see it |
|---|---|
| The schema is enforced when data is written | `avro_demo.py`, step 1: the writer rejects a text quantity, the unit `lbs` (not in the enum), a missing field, and an unknown extra field (`strict=True`). |
| Schema evolution: compatible change | `avro_demo.py`, step 2: v2 adds an optional field with a default. New consumers read old data, and old consumers read new data. |
| Schema evolution: incompatible change | `avro_demo.py`, step 2: v3 changes the type of `quantity` and renames a field; the reader fails with `SchemaResolutionError`. |
| A schema registry checks compatibility before publishing | `avro_demo.py`, step 3: `can_read` does the check of a registry (for example, the Confluent Schema Registry), so an incompatible change fails at the producer, not later at the consumer. |
| Side benefit: more efficient storage | `formats.py`: Avro with deflate is about 6× and Parquet about 20× smaller than CSV. |
| Formats with a schema keep the types | `formats.py`: CSV changes timestamps to text; only Avro keeps the decimal price. |

## Run

```sh
uv run avro_demo.py   # validation on write, schema evolution, compatibility check
uv run formats.py     # CSV vs JSON Lines vs Avro vs Parquet: size, speed, types
```
