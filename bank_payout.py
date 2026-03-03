"""Generic bank payout helper.

This module provides a minimal interface to send a bank payout via a
configurable HTTP API. Most real bank integrations will use a provider-specific
API (e.g., Stripe ACH, Dwolla, MangoPay, local banking API). Here we implement
a small wrapper that POSTs to a configured endpoint with an API key header.

If no `BANK_API_URL` is configured, callers should fallback to simulation mode.
"""
from __future__ import annotations

import os
import requests
from typing import Dict, Any


def send_bank_payout(api_url: str, api_key: str, account: str, amount: float, currency: str = "ZAR", reference: str | None = None) -> Dict[str, Any]:
    """Send a bank payout by POSTing to `api_url` using `api_key`.

    The exact payload expected depends on the provider. This function sends a
    simple JSON body with commonly required fields. Providers will need adapting.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "account": account,
        "amount": {"value": f"{amount:.2f}", "currency": currency},
    }
    if reference:
        payload["reference"] = reference

    r = requests.post(api_url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def simulate_bank_payout(account: str, amount: float, currency: str = "ZAR", reference: str | None = None) -> Dict[str, Any]:
    return {
        "status": "simulated",
        "account": account,
        "amount": f"{amount:.2f} {currency}",
        "reference": reference or "SIM-REF",
    }


if __name__ == "__main__":
    print("bank_payout helper module")
