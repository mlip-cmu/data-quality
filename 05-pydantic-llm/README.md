# 05 · Pydantic: schemas for LLM output and REST APIs

**Slides:** *Pydantic* (both slides) · *Schema-Less Data Exchange* (REST API calls) · *What
Happens When New Data Violates Schema?*

Suppliers announce deliveries by e-mail (`emails/`). An LLM changes each e-mail into a
`DeliveryNotice` (`schema.py`).

## What this project illustrates

| Point | Where to see it |
|---|---|
| A schema for LLM output as a hand-written JSON schema | `extract.py`, variant 1: `response_format` with a JSON schema dict. The dict is `DeliveryNotice.model_json_schema()` (see `schema.json`). |
| A schema for LLM output as a Pydantic model | `extract.py`, variant 2: `response_format=DeliveryNotice`. |
| The JSON schema constrains the shape; validators check the meaning | `schema.py`: types, the unit enum, and no extra fields are in the JSON schema; positive quantities and whole numbers for `count` are Pydantic validators. A catalog lookup checks the product names. |
| What happens when the output violates the schema | `extract.py`: validate, retry once with the validation errors, then quarantine. `50 lbs of potatoes` comes back with the unit `lbs` and is fixed on the retry. A truncated JSON answer is fixed on the retry. `half a pallet` of water is still `0.5` items and goes to `out/quarantine.json` for a human. |
| Structured output with the official Anthropic SDK | `extract_anthropic.py`: `client.beta.messages.parse(..., output_format=DeliveryNotice)` returns a validated object; the script checks `stop_reason == "refusal"`. |
| The same model is the contract of a REST API | `api.py`: FastAPI rejects a bad payload with HTTP 422 and one error for each field, and publishes the schema in `/openapi.json`. |

Replay mode uses the recorded LLM responses in `recorded/` (LiteLLM `mock_response`), so the
demo gives the same result in class and needs no API key. The code path is the same as in live
mode.

## Run

```sh
uv run extract.py                                           # replay mode
ANTHROPIC_API_KEY=... uv run extract.py --live              # live, default model anthropic/claude-opus-5
LLM_MODEL=gemini/gemini-2.5-flash uv run extract.py --live  # any LiteLLM model (with its key)
ANTHROPIC_API_KEY=... uv run extract_anthropic.py           # the official Anthropic SDK
uv run api.py                                               # the FastAPI endpoint
```
