"""Enforce a schema on the exchanged files: Frictionless Table Schema (CSV) and JSON Schema."""

import json

from frictionless import Package
from jsonschema import Draft202012Validator

print("=== CSV: Frictionless data package (datapackage.yaml) ===\n")
report = Package("datapackage.yaml").validate()
print(f"valid: {report.valid}\n")
for task, row, field, kind, note in report.flatten(
        ["taskNumber", "rowNumber", "fieldName", "type", "note"]):
    print(f"  row {row or '-':>3}  {field or '':<13} {kind:<17} {note}")

print("\n=== JSON: JSON Schema (feed.schema.json) ===\n")
validator = Draft202012Validator(json.load(open("feed.schema.json")))
feed = json.load(open("supplier_feed.json"))
for error in sorted(validator.iter_errors(feed), key=lambda e: list(e.path)):
    path = "/".join(str(p) for p in error.path)
    print(f"  {path:<16} {error.message}")
