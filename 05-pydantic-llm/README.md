# 05 · Pydantic: schemas for LLM output and REST APIs

**Slides:** *Pydantic* (both slides) · *Schema-Less Data Exchange* (REST API calls) · *What
Happens When New Data Violates Schema?*

Suppliers announce their deliveries to the stores by e-mail, in free text
([dataset](../inventory-data/)). This folder has five such e-mails (`emails/`), a schema for a
delivery notice (`schema.py`), and a script that uses an LLM to turn each e-mail into a
`DeliveryNotice` object (`extract.py`). The same schema also protects a REST endpoint
(`api.py`).

**Problem.** An LLM returns text. Even when we ask for JSON, the answer can have the wrong
shape, a unit that the inventory does not use (`lbs`), a value that makes no sense (half an
item), or it can stop in the middle. If the program uses such an answer without a check, the
error goes into the inventory database.

**Idea.** Write the expected structure once, as a Pydantic class. The class gives a JSON
schema that we send to the LLM API with the request. After the call,
Pydantic validates the answer again, including rules that a JSON schema cannot express. If the
answer is invalid, send the validation errors back to the LLM and ask once more; if it is
still invalid, put the e-mail in a quarantine for a human.

The schema of one line of a delivery notice (`schema.py`). The type, the enum of units, and
`extra="forbid"` are part of the JSON schema; the validator `plausible` runs only in Python:

```python
class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str = Field(description="product name, as in the supermarket catalog if possible")
    quantity: float = Field(description="number of units in `unit`")
    unit: Literal["count", "kg", "liter"] = Field(description="convert lb to kg, gallons to count")

    @model_validator(mode="after")
    def plausible(self) -> "LineItem":
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.unit == "count" and not float(self.quantity).is_integer():
            raise ValueError(f"{self.quantity} is not a whole number of items")
        return self
```

`extract.py` validates the answer; on an error, it sends a second request with the list of
problems:

```python
except ValidationError as e:
    problems = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
    if attempt == 2:
        return "quarantined", None, problems
    messages += [{"role": "assistant", "content": answer},
                 {"role": "user", "content": f"Your answer is not valid: {problems}. "
                                             "Return a corrected JSON object."}]
```

## What the code shows

`extract.py` in replay mode: the LLM responses come from the files in `recorded/`, so the
result is the same each time and no API key is needed. The code path is the same as in live
mode (LiteLLM returns the recorded text as the answer of the model).

1. **A JSON schema as `response_format`.** Variant 1 (first slide) passes a JSON schema as a
   plain dict. The dict is generated with `DeliveryNotice.model_json_schema()` and saved to
   `schema.json`. For `01_fresh_fields.txt` the first item is
   `{'product': 'Banana', 'quantity': 36, 'unit': 'kg'}`.
2. **A Pydantic class as `response_format`.** Variant 2 (second slide) passes the class
   `DeliveryNotice` itself and then validates each answer with Pydantic.
3. **Shape in the JSON schema, meaning in validators.** The JSON schema has the types, the
   enum of units, and no extra fields. Positive quantities and whole numbers for the unit
   `count` are Pydantic validators. A fuzzy lookup in the product catalog (with rapidfuzz)
   checks the product names; an answer with a name that matches no catalog product with a
   similarity of at least 90% also goes to the quarantine.
4. **Validate, retry, quarantine.** Of the 5 e-mails, 2 are valid at once. For "50 lbs of
   potatoes", the first answer has the unit `lbs`; the retry gives 22.68 kg. For the e-mail
   from EcoRefill, the first answer is cut off (`Invalid JSON: EOF while parsing an object`);
   the retry is complete. For "half a pallet" of bottled water, both answers have 0.5 items
   (`0.5 is not a whole number of items`), so this e-mail goes to `out/quarantine.json` for
   a human. Result: 4 notices accepted, 1 in the quarantine.
5. **The official Anthropic SDK.** `extract_anthropic.py` does the same extraction with
   `client.beta.messages.parse(..., output_format=DeliveryNotice)`, which returns an object
   that is already validated (`response.parsed_output`). The script also checks
   `stop_reason == "refusal"` and handles a `ValidationError`, rate limits, and other API
   errors. It needs an API key; it has no replay mode.
6. **The same class as the contract of a REST API.** `api.py` uses `DeliveryNotice` as the
   body of `POST /deliveries`. A valid notice returns HTTP 201. An invalid one (the date
   2025-06-31, the quantity `"fifty"`, the unit `lbs`, and an extra field `note`) returns HTTP
   422 with one error for each of the 4 fields. The schema is published in `/openapi.json`
   (`DeliveryNotice`, `LineItem`, and the error types).

## Tools

- [Pydantic](https://docs.pydantic.dev): data validation with Python type hints. Here: the
  classes `DeliveryNotice` and `LineItem`, their validators, and the generated JSON schema.
- [LiteLLM](https://docs.litellm.ai): one Python API for the LLMs of many providers. Here: the
  calls in `extract.py`, with `mock_response` for replay mode.
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python): the official
  client for the Claude API. Here: structured output with `messages.parse` in
  `extract_anthropic.py`.
- [FastAPI](https://fastapi.tiangolo.com): a web framework that validates requests with
  Pydantic. Here: the endpoint in `api.py`, called with its `TestClient` (needs
  [HTTPX](https://www.python-httpx.org)).
- [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/): fast fuzzy string matching. Here: the
  check of product names against the catalog.

## Run

With [uv](https://docs.astral.sh/uv/). Live mode needs an API key of the LLM provider.

```sh
uv run extract.py --replay                                  # replay mode (default without a key)
ANTHROPIC_API_KEY=... uv run extract.py --live              # live, default model anthropic/claude-opus-5
LLM_MODEL=gemini/gemini-2.5-flash uv run extract.py --live  # any LiteLLM model (with its key)
ANTHROPIC_API_KEY=... uv run extract_anthropic.py           # the official Anthropic SDK
uv run api.py                                               # the FastAPI endpoint
```
