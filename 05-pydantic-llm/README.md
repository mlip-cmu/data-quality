# 05 · Pydantic: schemas for LLM output and REST APIs

**Slides:** *Pydantic* (LiteLLM with a hand-written JSON schema, and with `response_format=` a
Pydantic model) · *Schema-Less Data Exchange* (REST API calls) · *What Happens When New Data
Violates Schema?*

Suppliers announce deliveries by e-mail (`emails/`). An LLM turns each e-mail into a
`DeliveryNotice` (`schema.py`). The JSON schema constrains the *shape* (types, the unit enum,
no extra fields); Pydantic validators check the *meaning* afterwards (positive quantities,
whole numbers for `count`); a catalog lookup checks the product names.

```sh
uv run extract.py             # replay mode: recorded LLM responses, no API key needed
ANTHROPIC_API_KEY=... uv run extract.py --live            # live, default model anthropic/claude-opus-5
LLM_MODEL=gemini/gemini-2.5-flash uv run extract.py --live  # any LiteLLM model (with its key)
ANTHROPIC_API_KEY=... uv run extract_anthropic.py         # the same with the official Anthropic SDK
uv run api.py                 # the same model protects a FastAPI endpoint
```

What to look for in `extract.py`:
- Variant 1 passes a JSON schema dict (as on the first slide); the dict is simply
  `DeliveryNotice.model_json_schema()` (see `schema.json`). Variant 2 passes the class.
- Validate, retry once with the validation errors, then quarantine: `50 lbs of potatoes`
  comes back with the unit `lbs` and is fixed on the retry; a truncated JSON answer is fixed on
  the retry; `half a pallet` of water is still `0.5` items and goes to `out/quarantine.json`
  for a human. The recorded responses in `recorded/` make this reproducible in class.
- In replay mode LiteLLM's `mock_response` returns the recorded text, so the code path is the
  same as in live mode.

`extract_anthropic.py` uses `client.beta.messages.parse(..., output_format=DeliveryNotice)`,
which returns a validated `DeliveryNotice`. It checks for `stop_reason == "refusal"` and turns
on the server-side refusal fallback (`fallbacks="default"`). `api.py` shows that the same model
is the contract of a REST endpoint: FastAPI rejects a bad payload with HTTP 422 and a precise
error for each field, and publishes the schema in `/openapi.json`.
