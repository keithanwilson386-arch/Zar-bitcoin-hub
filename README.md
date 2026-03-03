# Zar-bitcoin-hub
Bitcoin exchange app

## BTC to ZAR converter

A tiny CLI tool to convert BTC amounts to South African Rand (ZAR) using CoinGecko's public API.

Usage:

```bash
python btc_to_zar.py 0.01
# show price and conversion
python btc_to_zar.py 0.01 --price
```

Real payouts (PayPal)

To perform real PayPal payouts you must have a PayPal account with Payouts enabled and set these environment variables (use sandbox credentials for testing):

```bash
export PAYPAL_CLIENT_ID="your-client-id"
export PAYPAL_SECRET="your-secret"
# optional: set to 0 to use live endpoints
export PAYPAL_SANDBOX=1
```

Then run:

```bash
python btc_to_zar.py 0.01 --withdraw-paypal "me@example.com"
```

If credentials are missing the CLI will only simulate the payout and print instructions.

Real payouts (Bank provider)

This repo provides a small `bank_payout` wrapper that POSTs to a configurable bank/provider endpoint. Configure these env vars for real bank payouts:

```bash
export BANK_API_URL="https://api.your-bank-provider.example/payouts"
export BANK_API_KEY="secret-api-key"
```

If `BANK_API_URL`/`BANK_API_KEY` are not set the CLI will print a simulated bank payout instead.

Security

Never commit your API credentials. Use environment variables or a secrets manager for production.

Address & key utilities

This project includes simple BTC address validation and pubkey->address confirmation utilities in `btc_utils.py`.

Usage examples:

```bash
# Validate an address
python btc_to_zar.py 0.0 --validate-address "bc1q..."

# Confirm a hex public key matches an address
python btc_to_zar.py 0.0 --confirm-pubkey "1A1zP1..." "03ab..."
```

Notes:
- `--validate-address` checks format and checksum for Base58 and Bech32 addresses.
- `--confirm-pubkey` computes P2PKH and P2WPKH addresses from the provided public key
	and compares to the given address (works for common mainnet address types).+- `--verify-message` checks a standard Bitcoin signed message (base64 sig) and
+  confirms that it was created by the private key corresponding to the given
+  address. Requires `coincurve` (added to requirements). The signature must be
+  the 65‑byte recovery signature encoded in base64, as produced by many
+  wallets and libraries.
Install requirements:

```bash
pip install -r requirements.txt
```

Development and testing

```bash
pip install -e .[dev]    # installs package in editable mode plus pytest
pytest                   # run unit tests
```

Packaging

The project uses PEP 621 metadata in `pyproject.toml`. You can build a wheel with:

```bash
python -m build
```

and then publish to PyPI using `twine`:

```bash
python -m twine upload dist/*
```


Withdrawal simulation

You can simulate withdrawing the converted ZAR to a bank account or to PayPal. These are simulations that apply simple example fees:

- Bank: 0.5% + 10 ZAR fixed
- PayPal: 2.9% + 5 ZAR fixed

Examples:

```bash
# Convert only
python btc_to_zar.py 0.01

# Show price and conversion
python btc_to_zar.py 0.01 --price

# Simulate withdraw to bank
python btc_to_zar.py 0.01 --withdraw-bank "NL00BANK0123456789"

# Simulate withdraw to PayPal
python btc_to_zar.py 0.01 --withdraw-paypal "me@example.com"
```
