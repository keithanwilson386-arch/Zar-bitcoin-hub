#!/usr/bin/env python3
"""
Simple BTC -> ZAR converter using CoinGecko public API.
Usage: python btc_to_zar.py <amount_in_btc>
"""
import argparse
import sys
import os

try:
    import requests
except Exception:
    requests = None

from paypal_client import payout_via_paypal
from bank_payout import send_bank_payout, simulate_bank_payout

API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=zar"

def fetch_btc_zar_price():
    if requests is None:
        raise RuntimeError("'requests' is not installed. See requirements.txt")
    r = requests.get(API_URL, timeout=10)
    r.raise_for_status()
    data = r.json()
    return float(data["bitcoin"]["zar"])  # may raise KeyError if API changes

def format_zar(amount):
    return f"{amount:,.2f} ZAR"

def main():
    p = argparse.ArgumentParser(description="Convert BTC to ZAR using live rates from CoinGecko")
    p.add_argument("amount", type=float, help="Amount in BTC to convert")
    p.add_argument("--price", action="store_true", help="Show current BTC price in ZAR")

    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--withdraw-bank", metavar="ACCOUNT", help="Simulate withdraw to bank account (provide account id)")
    grp.add_argument("--withdraw-paypal", metavar="EMAIL", help="Simulate withdraw to PayPal (provide email)")

    p.add_argument("--validate-address", metavar="ADDRESS", help="Validate a Bitcoin address (format + checksum)")
    p.add_argument("--confirm-pubkey", nargs=2, metavar=("ADDRESS", "PUBKEY_HEX"),
                   help="Confirm that a hex public key corresponds to ADDRESS")
    p.add_argument("--verify-message", nargs=3, metavar=("ADDRESS", "MESSAGE", "SIG_BASE64"),
                   help="Verify a Bitcoin signed message against ADDRESS")

    args = p.parse_args()

    # early ops that don't need the price
    if args.validate_address:
        from btc_utils import is_valid_btc_address
        ok = is_valid_btc_address(args.validate_address)
        print(f"Address {args.validate_address} valid: {ok}")
        sys.exit(0 if ok else 2)

    if args.confirm_pubkey:
        from btc_utils import confirm_pubkey_matches_address
        address, pubkey_hex = args.confirm_pubkey
        ok = confirm_pubkey_matches_address(pubkey_hex, address)
        print(f"Pubkey matches address: {ok}")
        sys.exit(0 if ok else 2)

    if args.verify_message:
        from btc_utils import verify_message
        address, message, sig = args.verify_message
        try:
            ok = verify_message(address, message, sig)
        except Exception as e:
            print(f"Verification error: {e}", file=sys.stderr)
            sys.exit(2)
        print(f"Message verification result: {ok}")
        sys.exit(0 if ok else 2)

    # fetch price for subsequent operations
    try:
        price = fetch_btc_zar_price()
    except Exception as e:
        print(f"Error fetching price: {e}", file=sys.stderr)
        sys.exit(2)

    converted = price * args.amount
    if args.price:
        print(f"Current BTC price: {format_zar(price)}")
    print(f"{args.amount} BTC = {format_zar(converted)}")

    if args.withdraw_bank:
        pct_fee = converted * 0.005  # 0.5%
        bank_fixed = 10.0
        total_fees = pct_fee + bank_fixed
        net = converted - total_fees
        print("--- Bank withdrawal ---")
        print(f"Account: {args.withdraw_bank}")
        print(f"Gross: {format_zar(converted)}")
        print(f"Percentage fee (0.5%): {format_zar(pct_fee)}")
        print(f"Fixed fee: {format_zar(bank_fixed)}")
        print(f"Total fees: {format_zar(total_fees)}")
        print(f"Net received: {format_zar(max(net, 0.0))}")

        bank_api_url = os.getenv("BANK_API_URL")
        bank_api_key = os.getenv("BANK_API_KEY")
        if bank_api_url and bank_api_key:
            try:
                resp = send_bank_payout(bank_api_url, bank_api_key, args.withdraw_bank,
                                        net, currency="ZAR", reference="btc_to_zar")
                print("Bank payout response:", resp)
            except Exception as e:
                print(f"Bank payout failed: {e}", file=sys.stderr)
        else:
            print("Bank payout not configured; simulation: ", simulate_bank_payout(args.withdraw_bank, net))

    if args.withdraw_paypal:
        paypal_fee_pct = 0.029  # 2.9%
        paypal_fixed = 5.0
        pct_fee = converted * paypal_fee_pct
        total_fees = pct_fee + paypal_fixed
        net = converted - total_fees
        print("--- PayPal withdrawal ---")
        print(f"PayPal email: {args.withdraw_paypal}")
        print(f"Gross: {format_zar(converted)}")
        print(f"Percentage fee (2.9%): {format_zar(pct_fee)}")
        print(f"Fixed fee: {format_zar(paypal_fixed)}")
        print(f"Total fees: {format_zar(total_fees)}")
        print(f"Net received: {format_zar(max(net, 0.0))}")

        paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
        paypal_secret = os.getenv("PAYPAL_SECRET")
        paypal_sandbox = os.getenv("PAYPAL_SANDBOX", "1") in ("1", "true", "True")
        if paypal_client_id and paypal_secret:
            try:
                resp = payout_via_paypal(paypal_client_id, paypal_secret, args.withdraw_paypal,
                                         net, currency="ZAR", sandbox=paypal_sandbox)
                print("PayPal payout response:", resp)
            except Exception as e:
                print(f"PayPal payout failed: {e}", file=sys.stderr)
        else:
            print("PayPal payout not configured; run with PAYPAL_CLIENT_ID and PAYPAL_SECRET set to perform real payout")

if __name__ == '__main__':
    main()
