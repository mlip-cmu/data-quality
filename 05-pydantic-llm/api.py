"""The same Pydantic model protects a REST endpoint: suppliers can post delivery notices."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from schema import DeliveryNotice

app = FastAPI(title="Delivery notices")
received: list[DeliveryNotice] = []


@app.post("/deliveries", status_code=201)
def post_delivery(notice: DeliveryNotice) -> dict:
    received.append(notice)
    return {"accepted": len(notice.items)}


if __name__ == "__main__":
    client = TestClient(app)
    good = {
        "supplier": "Fresh Fields Produce",
        "store_city": "Pittsburgh",
        "delivery_date": "2025-06-06",
        "items": [{"product": "Banana", "quantity": 36, "unit": "kg"}],
    }
    bad = {
        "supplier": "Fresh Fields Produce",
        "store_city": "Pittsburgh",
        "delivery_date": "2025-06-31",
        "items": [{"product": "Banana", "quantity": "fifty", "unit": "lbs"}],
        "note": "urgent",
    }
    for label, payload in [("valid notice", good), ("invalid notice", bad)]:
        r = client.post("/deliveries", json=payload)
        print(f"{label}: HTTP {r.status_code}")
        if r.status_code == 422:
            for err in r.json()["detail"]:
                print(f"  {'.'.join(map(str, err['loc'][1:])):<22} {err['msg']}")
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    print(f"\nThe OpenAPI contract at /openapi.json documents the schema: {sorted(schema)}")
