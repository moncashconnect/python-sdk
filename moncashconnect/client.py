"""MonCashConnect API client."""

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .exceptions import MonCashError

_BASE_URL = "https://hvlmeoqyxaguzcujpmit.supabase.co/functions/v1"
_SDK_VERSION = "1.1.0"


class MonCashClient:
    """
    Client for the MonCashConnect payment API.

    Args:
        secret_key: Your project secret key. Live keys start with ``sk_proj_``
                    and sandbox keys start with ``sk_test_proj_``.
        timeout:    Request timeout in seconds (default 20).
        base_url:   Override the API base URL (defaults to the MonCashConnect
                    production endpoint). Useful for testing or staging.

    Example::

        from moncashconnect import MonCashClient

        client = MonCashClient(os.environ["MCC_SECRET_KEY"])
        payment = client.create_payment(500, "order_001",
                                        return_url="https://site.ht/merci")
        # Redirect customer to payment["paymentUrl"]
    """

    def __init__(
        self,
        secret_key: str,
        timeout: int = 20,
        *,
        base_url: str | None = None,
    ) -> None:
        if not (
            secret_key.startswith("sk_proj_")
            or secret_key.startswith("sk_test_proj_")
        ):
            raise MonCashError(
                'Secret key must start with "sk_proj_" (live) '
                'or "sk_test_proj_" (sandbox)'
            )
        self._secret_key = secret_key
        self._timeout = timeout
        self._base_url = (base_url or _BASE_URL).rstrip("/")
        self.is_sandbox = secret_key.startswith("sk_test_proj_")

    def create_payment(
        self,
        amount: int,
        reference_id: str,
        *,
        return_url: str,
        customer_name: str | None = None,
        customer_email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a payment and return the MonCash redirect URL.

        Args:
            amount:          Amount in HTG (integer, 1–1 000 000).
            reference_id:    Unique reference ``[a-zA-Z0-9-_]``, max 100 chars.
            return_url:      HTTPS URL to redirect the customer after payment
                             (required).
            customer_name:   Customer name shown on the MonCash payment page.
            customer_email:  Customer email stored on the transaction.
            idempotency_key: Optional key sent as the ``Idempotency-Key`` header
                             so retried requests do not create duplicate
                             payments.

        Returns:
            ``{"paymentUrl": str, "reference": str, "expiresAt": str}``

        Raises:
            MonCashError: on any API or network error.
        """
        payload: dict[str, Any] = {
            "amount": amount,
            "referenceId": reference_id,
            "returnUrl": return_url,
        }
        if customer_name:
            payload["customerName"] = customer_name
        if customer_email:
            payload["customerEmail"] = customer_email
        headers: dict[str, str] | None = None
        if idempotency_key:
            headers = {"Idempotency-Key": idempotency_key}
        return self._request("POST", "/pay-create", payload, headers=headers)

    def get_payment_status(self, reference_id: str) -> dict[str, Any]:
        """
        Get the status of a payment by your reference ID.

        Returns:
            Transaction dict with keys: ``status``, ``amount``, ``netAmount``,
            ``completedAt``, ``failedAt``, ``failureReason``, etc.
        """
        from urllib.parse import quote
        return self._request("GET", f"/pay-status?referenceId={quote(reference_id)}")

    def get_balance(self) -> dict[str, Any]:
        """
        Get your account balance and daily withdrawal cap.

        Returns:
            ``{"balanceHtg": int, "withdrawableHtg": int, "dailyCapHtg": int, "usedTodayHtg": int}``
        """
        return self._request("GET", "/pay-balance")

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._base_url + path
        data = json.dumps(body).encode() if body is not None else None
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._secret_key}",
            "User-Agent": f"MonCashConnect-Python-SDK/{_SDK_VERSION}",
        }
        if headers:
            request_headers.update(headers)
        req = Request(
            url,
            data=data,
            method=method,
            headers=request_headers,
        )
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                status = resp.status
        except URLError as exc:
            raise MonCashError(f"Network error: {exc.reason}") from exc

        try:
            data_resp: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MonCashError("Invalid JSON response from API.", status) from exc

        if status < 200 or status >= 300:
            message = data_resp.get("error", f"HTTP {status}")
            code = data_resp.get("code")
            raise MonCashError(str(message), status, data_resp, code=code)

        return data_resp
