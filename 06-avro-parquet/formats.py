"""The same POS events as CSV, JSON Lines, Avro, and Parquet: size, speed, and types."""

import json
import time
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from fastavro import parse_schema, reader, writer

import inventory_data as d

OUT = Path("out")
OUT.mkdir(exist_ok=True)
events = d.pos_events()
events = pd.concat([events.assign(event_id=events.event_id + f"-{k}") for k in range(20)],
                   ignore_index=True)
events["event_time"] = events.event_time.dt.floor("ms")
schema = parse_schema(json.load(open("schemas/sale_event.v1.avsc")))
columns = [f["name"] for f in json.load(open("schemas/sale_event.v1.avsc"))["fields"]]
events = events[columns]


def write_avro(path: Path) -> None:
    rows = events.assign(unit_price=events.unit_price.map(lambda p: Decimal(f"{p:.2f}")))
    with open(path, "wb") as f:
        writer(f, schema, rows.to_dict("records"), codec="deflate")


def read_avro(path: Path) -> pd.DataFrame:
    with open(path, "rb") as f:
        return pd.DataFrame(reader(f))


formats = {
    "CSV": ("events.csv", lambda p: events.to_csv(p, index=False), pd.read_csv),
    "JSON Lines": ("events.jsonl", lambda p: events.to_json(p, orient="records", lines=True,
                                                            date_format="iso"),
                   lambda p: pd.read_json(p, lines=True)),
    "Avro (deflate)": ("events.avro", write_avro, read_avro),
    "Parquet (zstd)": ("events.parquet", lambda p: events.to_parquet(p, compression="zstd"),
                       pd.read_parquet),
}
rows, back = [], {}
for name, (file, write, read) in formats.items():
    path = OUT / file
    t0 = time.perf_counter()
    write(path)
    t1 = time.perf_counter()
    back[name] = read(path)
    t2 = time.perf_counter()
    rows.append((name, path.stat().st_size / 1e6, (t1 - t0) * 1000, (t2 - t1) * 1000))

print(f"{len(events):,} POS events\n")
print(pd.DataFrame(rows, columns=["format", "MB", "write ms", "read ms"]).round(2)
      .to_string(index=False))

print("\nTypes after reading the file back:\n")
types = pd.DataFrame({name: df.dtypes.astype(str) for name, df in back.items()})
print(types.loc[["event_id", "event_time", "unit", "unit_price", "promo"]].to_string())

print("\nParquet stores the schema in the file:\n")
print(pq.read_schema(OUT / "events.parquet").remove_metadata())
