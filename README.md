# moncashconnect

Official Python SDK for [MonCashConnect](https://moncashconnect.com) — the easiest way to integrate MonCash payments in your Python application.

**Zero dependencies** — uses only the Python standard library.

> **Note:** MonCashConnect is not affiliated with Digicel or the official MonCash service.

## Requirements

- Python 3.9+

## Installation

```bash
pip install moncashconnect
```

## Quick Start

```python
import os
from moncashconnect import MonCashClient

client = MonCashClient(os.environ["MCC_SECRET_KEY"])

payment = client.create_payment(
    1500,
    "order-001",
    return_url="https://yoursite.com/payment/success",
    customer_name="Jean Dupont",
)

# Redirect the customer
print(payment["paymentUrl"])
```

Your secret key starts with `sk_proj_` — get it from **Developer → Projects** in your dashboard.

## Check Payment Status

```python
tx = client.get_payment_status("order-001")

print(tx["status"])    # "pending" | "completed" | "failed"
print(tx["netAmount"]) # Amount after commission deduction
```

## Get Account Balance

```python
balance = client.get_balance()

print(balance["balanceHtg"])      # Total available
print(balance["withdrawableHtg"]) # Can withdraw now
```

## Webhooks

Configure a webhook URL in your project. MonCashConnect sends a signed `POST` when a payment is finalized.

Always read the **raw** body **before** any `json.loads()`.

```python
from moncashconnect import construct_event, MonCashError

# Django
def webhook(request):
    raw_body  = request.body          # bytes — read before any parsing
    signature = request.META.get("HTTP_X_MCC_SIGNATURE", "")
    timestamp = request.META.get("HTTP_X_MCC_TIMESTAMP", "")

    try:
        event = construct_event(
            raw_body, signature, timestamp,
            os.environ["MCC_WEBHOOK_SECRET"],
        )
    except MonCashError as exc:
        return HttpResponse(str(exc), status=exc.status_code)

    if event["event"] == "payment.completed":
        Order.objects.filter(reference=event["reference"]).update(status="paid")
    elif event["event"] == "payment.failed":
        Order.objects.filter(reference=event["reference"]).update(status="failed")

    return HttpResponse("OK")
```

### Flask

```python
from flask import Flask, request, abort
from moncashconnect import construct_event, MonCashError

app = Flask(__name__)

@app.route("/webhooks/moncash", methods=["POST"])
def moncash_webhook():
    raw_body  = request.get_data()   # bytes
    signature = request.headers.get("X-MCC-Signature", "")
    timestamp = request.headers.get("X-MCC-Timestamp", "")

    try:
        event = construct_event(
            raw_body, signature, timestamp,
            os.environ["MCC_WEBHOOK_SECRET"],
        )
    except MonCashError as exc:
        abort(exc.status_code, description=str(exc))

    if event["event"] == "payment.completed":
        mark_order_paid(event["reference"])

    return "OK", 200
```

### FastAPI

```python
from fastapi import FastAPI, Header, HTTPException, Request
from moncashconnect import construct_event, MonCashError

app = FastAPI()

@app.post("/webhooks/moncash")
async def moncash_webhook(
    request: Request,
    x_mcc_signature: str = Header(...),
    x_mcc_timestamp: str = Header(...),
):
    raw_body = await request.body()
    try:
        event = construct_event(
            raw_body, x_mcc_signature, x_mcc_timestamp,
            os.environ["MCC_WEBHOOK_SECRET"],
        )
    except MonCashError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    if event["event"] == "payment.completed":
        await mark_order_paid(event["reference"])

    return {"ok": True}
```

## Error Handling

```python
from moncashconnect import MonCashClient, MonCashError

try:
    payment = client.create_payment(500, "order-42")
except MonCashError as exc:
    print(exc)             # "referenceId already exists for this project"
    print(exc.status_code) # 409
    print(exc.context)     # Full API response dict, or None
```

## License

MIT
