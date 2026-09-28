"""Avro: the schema travels with the data, is checked on write, and can evolve."""

import io
import json
from decimal import Decimal

from fastavro import parse_schema, reader, writer
from fastavro.read import SchemaResolutionError
from fastavro.validation import ValidationError

import inventory_data as d


def load(version: int) -> dict:
    return parse_schema(json.load(open(f"schemas/sale_event.v{version}.avsc")))


def records(n: int = 5) -> list[dict]:
    events = d.pos_events().head(n)
    return [
        {
            "event_id": e.event_id,
            "event_time": e.event_time.floor("ms").to_pydatetime(),
            "store_id": int(e.store_id),
            "terminal_id": e.terminal_id,
            "product_id": int(e.product_id),
            "quantity": float(e.quantity),
            "unit": e.unit,
            "unit_price": Decimal(str(e.unit_price)),
            "promo": bool(e.promo),
        }
        for e in events.itertuples()
    ]


def roundtrip(rows: list[dict], write_schema: dict, read_schema: dict) -> list[dict]:
    buf = io.BytesIO()
    writer(buf, write_schema, rows, codec="deflate", validator=True, strict=True)
    buf.seek(0)
    return list(reader(buf, reader_schema=read_schema))


v1, v2, v3 = load(1), load(2), load(3)
good = records()

print("=== 1. The writer checks every record against the schema ===\n")
bad = {
    "quantity='fifty'": good[0] | {"quantity": "fifty"},
    "unit='lbs'": good[0] | {"unit": "lbs"},
    "no store_id": {k: v for k, v in good[0].items() if k != "store_id"},
    "extra field cashier": good[0] | {"cashier": "C25"},
}
for label, record in bad.items():
    try:
        roundtrip([record], v1, v1)
        print(f"  {label:<20} accepted")
    except (ValidationError, ValueError) as e:
        reason = "; ".join(json.loads(str(e))) if isinstance(e, ValidationError) else str(e)
        if reason.startswith(" is <"):
            reason = "not a valid SaleEvent (a field without a default is missing)"
        print(f"  {label:<20} rejected: {reason[:80]}")

print("\n=== 2. Schema evolution ===\n")
old = roundtrip(good, v1, v2)
print(f"  v1 data, v2 reader (new consumer, old data):  loyalty_id = {old[0]['loyalty_id']}")
new = roundtrip([r | {"loyalty_id": "L-0042"} for r in good], v2, v1)
print(f"  v2 data, v1 reader (old consumer, new data):  fields = {sorted(new[0])[:4]}...")
try:
    roundtrip(good, v1, v3)
except SchemaResolutionError as e:
    print(f"  v1 data, v3 reader: SchemaResolutionError: {e}")


def can_read(write_schema: dict, read_schema: dict, rows: list[dict]) -> bool:
    try:
        roundtrip(rows, write_schema, read_schema)
        return True
    except SchemaResolutionError:
        return False


print(
    "\n=== 3. A schema registry checks compatibility before a producer may use a new schema ===\n"
)
v2_rows = [r | {"loyalty_id": None} for r in good]
v3_rows = [
    {k: v for k, v in r.items() if k != "terminal_id"}
    | {"quantity": str(r["quantity"]), "register_id": r["terminal_id"]}
    for r in good
]
for name, schema, rows in [
    ("v2: adds an optional loyalty_id", v2, v2_rows),
    ("v3: quantity as text, terminal_id renamed", v3, v3_rows),
]:
    backward = can_read(v1, schema, good)
    forward = can_read(schema, v1, rows)
    verdict = "compatible, register it" if backward and forward else "incompatible, reject it"
    print(
        f"  {name:<42} new reads old: {backward!s:<5}  old reads new: {forward!s:<5} -> {verdict}"
    )
