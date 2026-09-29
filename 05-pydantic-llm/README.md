# 05 · Pydantic: schemas for LLM output and REST APIs

Suppliers of a supermarket chain announce deliveries by e-mail (`emails/`). An LLM changes
each e-mail into a structured delivery notice ([dataset](../inventory-data/)).

**Problem.** LLM output is text. Even with a requested format, it can have the wrong
structure, wrong units (`lbs`), impossible values (`0.5` items), or product names that are not
in the catalog. The same is true for data that arrives through a REST API.

**Idea.** Define the expected data once as a Pydantic model (`schema.py`). Its JSON schema
constrains the *shape* of the LLM output (types, the unit enum, no extra fields); its
validators check the *meaning* (positive quantities, whole numbers for `count`). Validate
each answer, retry once with the validation errors, and put what still fails in a quarantine
for a human. The same model can protect a REST endpoint.

The model defines both the shape and the meaning of the data (`schema.py`):

```python
class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product: str = Field(description="product name, as in the supermarket catalog if possible")
    quantity: float = Field(description="number of units in `unit`")
    unit: Literal["count", "kg", "liter"] = Field(description="convert lb to kg, gallons to count")

    @model_validator(mode="after")
    def plausible(self) -> "LineItem":
        if self.unit == "count" and not float(self.quantity).is_integer():
            raise ValueError(f"{self.quantity} is not a whole number of items")
        return self
```

`extract.py` passes the model as the output format, validates the answer, and sends the
validation errors back to the LLM once before it quarantines the e-mail (simplified):

```python
response = litellm.completion(model=MODEL, messages=messages, response_format=DeliveryNotice)
answer = response.choices[0].message.content
try:
    notice = DeliveryNotice.model_validate_json(answer)
except ValidationError as e:  # retry once with the errors, then quarantine
    messages += [
        {"role": "assistant", "content": answer},
        {"role": "user", "content": f"Your answer is not valid: {e}. ..."},
    ]
```

## What the code shows

- `extract.py`, variant 1: a hand-written JSON schema as `response_format` (it is
  `DeliveryNotice.model_json_schema()`, see `schema.json`). Variant 2:
  `response_format=DeliveryNotice`.
- `extract.py`, validate → retry → quarantine: `50 lbs of potatoes` comes back with the unit
  `lbs` and is fixed on the retry; a truncated JSON answer is fixed on the retry; `half a
  pallet` of water is still `0.5` items and goes to `out/quarantine.json`. A catalog lookup
  checks the product names.
- `extract_anthropic.py`: the same extraction with the Anthropic SDK, which returns a
  validated `DeliveryNotice` directly and reports refusals.
- `api.py`: FastAPI uses the same model to reject a bad payload with HTTP 422 (one error for
  each field) and to publish the schema in `/openapi.json`.

Replay mode (the default) uses the recorded LLM responses in `recorded/`, so the result is the
same each time and no API key is necessary. The code path is the same as in live mode.

## Tools

- [Pydantic](https://docs.pydantic.dev): data validation with Python type hints. A model class
  defines the fields, and Pydantic parses, checks, and exports it as JSON Schema.
- [LiteLLM](https://docs.litellm.ai): one Python API for many LLM providers. Here: the calls
  with `response_format`, and `mock_response` for replay mode.
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python): the official
  client for the Claude API. Here: `client.beta.messages.parse` with a Pydantic model.
- [FastAPI](https://fastapi.tiangolo.com): a web framework that validates requests with
  Pydantic models. Its `TestClient` (based on [HTTPX](https://www.python-httpx.org)) calls the
  endpoint without a server.
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz): fast fuzzy string matching. Here: it
  matches the product names to the catalog.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
uv run extract.py                                           # replay mode
ANTHROPIC_API_KEY=... uv run extract.py --live              # live, default model anthropic/claude-opus-5
LLM_MODEL=gemini/gemini-2.5-flash uv run extract.py --live  # any LiteLLM model (with its key)
ANTHROPIC_API_KEY=... uv run extract_anthropic.py           # the Anthropic SDK
uv run api.py                                               # the FastAPI endpoint
```
