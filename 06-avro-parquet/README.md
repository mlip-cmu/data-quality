# 06 · Avro and Parquet

**Slides:** *Apache Avro (e.g. for Kafka)* (side benefit: more efficient storage) · *Many Schema
Libraries/Formats* (Avro, XML Schema, Protobuf, Thrift, Parquet, ORC)

The checkout terminals send one event per receipt line (`schemas/sale_event.v1.avsc`). In a
real system these events go through Kafka, and a schema registry stores the schemas.

```sh
uv run avro_demo.py   # validation on write, schema evolution, compatibility check
uv run formats.py     # CSV vs JSON Lines vs Avro vs Parquet: size, speed, types
```

What to look for in `avro_demo.py`:
1. The writer rejects records that do not match the schema: a text quantity, the unit `lbs`
   (not in the enum), a missing field, and an unknown extra field (`strict=True`).
2. Schema evolution. v2 adds an optional field with a default: new consumers can read old data,
   and old consumers can read new data. v3 changes the type of `quantity` and renames a field:
   the reader fails (`SchemaResolutionError`).
3. A schema registry (e.g., the Confluent Schema Registry for Kafka) does this check *before* a
   producer may publish with a new schema, so an incompatible change fails at the producer, not
   weeks later at the consumer. `can_read` simulates the check with fastavro's schema resolution.

What to look for in `formats.py`: binary formats with a schema are much smaller (Avro with
deflate ~6×, Parquet ~20× smaller than CSV), and they keep the types. CSV turns timestamps
into text; only Avro keeps the decimal price.
