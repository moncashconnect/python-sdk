"""Webhook signature verification helpers."""

import hashlib
import hmac
import json
import time
from typing import Any

from .exceptions import MonCashError


def verify_signature(
    raw_body: bytes | str,
    signature: str,
    timestamp: str,
    secret: str,
) -> bool:
    """
    Verify a MonCashConnect webhook signature.

    Args:
        raw_body:  Raw request body — read BEFORE any json.loads().
        signature: Value of the X-MCC-Signature header (sha256=<hex>).
        timestamp: Value of the X-MCC-Timestamp header (Unix seconds).
        secret:    Your project's webhook secret (whsec_…).

    Returns:
        True if the signature is valid and the timestamp is within 5 minutes.
    """
    if not raw_body or not signature or not timestamp or not secret:
        return False

    # Reject stale webhooks (> 5 minutes)
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 300:
        return False

    body_bytes = raw_body.encode() if isinstance(raw_body, str) else raw_body
    expected = "sha256=" + hmac.new(
        secret.encode(), body_bytes, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def construct_event(
    raw_body: bytes | str,
    signature: str,
    timestamp: str,
    secret: str,
) -> dict[str, Any]:
    """
    Verify signature + timestamp and return the parsed webhook event.

    Raises:
        MonCashError(401): if signature verification fails.
        MonCashError(400): if the payload is not valid JSON.
    """
    if not verify_signature(raw_body, signature, timestamp, secret):
        raise MonCashError("Webhook signature verification failed.", 401)

    body_str = raw_body.decode() if isinstance(raw_body, bytes) else raw_body
    try:
        event = json.loads(body_str)
    except json.JSONDecodeError as exc:
        raise MonCashError("Invalid webhook payload — could not parse JSON.", 400) from exc

    if not isinstance(event, dict) or "event" not in event or "reference" not in event:
        raise MonCashError("Invalid webhook payload — missing required fields.", 400)

    return event
