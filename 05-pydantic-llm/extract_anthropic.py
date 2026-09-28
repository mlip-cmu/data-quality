"""The same extraction with the official Anthropic SDK: messages.parse validates the Pydantic model."""

import os
import sys
from pathlib import Path

import anthropic
from pydantic import ValidationError

import inventory_data as d
from schema import DeliveryNotice

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Set ANTHROPIC_API_KEY to run this live demo (extract.py has a replay mode).")
    sys.exit(0)

client = anthropic.Anthropic()
system = ("Extract the delivery notice from the supplier e-mail. Use the product names of the "
          "supermarket catalog: " + ", ".join(d.products().name))

for email in sorted(Path("emails").glob("*.txt")):
    try:
        response = client.beta.messages.parse(
            model="claude-opus-5",
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": email.read_text()}],
            output_format=DeliveryNotice,
        )
    except ValidationError as e:
        print(f"{email.name}: the answer breaks the schema's rules: {e.errors()[0]['msg']}")
        continue
    except anthropic.RateLimitError:
        print("Rate limited: try again later.")
        break
    except anthropic.APIStatusError as e:
        print(f"{email.name}: API error {e.status_code}: {e.message}")
        continue
    if response.stop_reason == "refusal":
        print(f"{email.name}: the model declined the request")
        continue
    notice = response.parsed_output
    print(f"{email.name}: {notice.supplier}, {notice.delivery_date}, "
          f"{[(i.product, i.quantity, i.unit) for i in notice.items]}")
