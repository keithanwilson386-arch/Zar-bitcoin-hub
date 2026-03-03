"""Minimal PayPal Payout helper using REST API (requests).

This helper supports sandbox and live modes via the `sandbox` flag.
It does not depend on any PayPal SDK so it's easy to inspect and run.

Environment / usage:
 - Set `PAYPAL_CLIENT_ID` and `PAYPAL_SECRET` environment variables
 - Set `PAYPAL_SANDBOX=1` to use sandbox endpoints (recommended for testing)

Note: Using real payouts requires a PayPal account with Payouts permissions.
"""
from __future__ import annotations

import base64
import os
import requests
from typing import Tuple, Dict, Any


def _base_url(sandbox: bool) -> str:
    return "https://api.sandbox.paypal.com" if sandbox else "https://api.paypal.com"


def get_access_token(client_id: str, secret: str, sandbox: bool = True) -> Tuple[str, str]:
    """Obtain OAuth2 access token from PayPal.

    Returns (access_token, token_type).
    """
    url = f"{_base_url(sandbox)}/v1/oauth2/token"
    auth = (client_id, secret)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data, auth=auth, timeout=15)
    r.raise_for_status()
    j = r.json()
    return j["access_token"], j.get("token_type", "Bearer")


def create_payout(access_token: str, receiver_email: str, amount: float, currency: str = "ZAR", sandbox: bool = True, note: str = "Payout") -> Dict[str, Any]:
    """Create a single payout to a PayPal account (email). Returns JSON response.

    This uses the Payouts API v1. For production use read PayPal docs and
    handle idempotency and errors appropriately.
    """
    url = f"{_base_url(sandbox)}/v1/payments/payouts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    body = {
        "sender_batch_header": {
            "sender_batch_id": "batch_" + base64.urlsafe_b64encode(os.urandom(6)).decode("ascii"),
            "email_subject": "You have a payout",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "receiver": receiver_email,
                "note": note,
            }
        ],
    }
    r = requests.post(url, headers=headers, json=body, timeout=20)
    r.raise_for_status()
    return r.json()


def payout_via_paypal(client_id: str, secret: str, receiver_email: str, amount: float, currency: str = "ZAR", sandbox: bool = True) -> Dict[str, Any]:
    """High-level helper: gets token and issues a payout.
    Raises requests.HTTPError on failure.
    """
    token, _ = get_access_token(client_id, secret, sandbox=sandbox)
    return create_payout(token, receiver_email, amount, currency=currency, sandbox=sandbox)


if __name__ == "__main__":
    print("paypal_client helper module")
