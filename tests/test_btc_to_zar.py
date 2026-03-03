import os
import sys

# add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import btc_to_zar


def run_main_with_args(args, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["btc_to_zar.py"] + args)
    # monkeypatch price to avoid network
    monkeypatch.setattr(btc_to_zar, "fetch_btc_zar_price", lambda: 100000.0)
    # run in try/except to catch SystemExit if any
    try:
        btc_to_zar.main()
    except SystemExit as e:
        # allow exits with 0 or others
        pass


def test_conversion_and_price(monkeypatch, capsys):
    run_main_with_args(["0.01", "--price"], monkeypatch, capsys)
    captured = capsys.readouterr()
    assert "Current BTC price" in captured.out
    assert "0.01 BTC =" in captured.out


def test_withdraw_bank_simulation(monkeypatch, capsys):
    run_main_with_args(["0.01", "--withdraw-bank", "ACC123"], monkeypatch, capsys)
    out = capsys.readouterr().out
    assert "Bank withdrawal" in out
    assert "Gross:" in out
    assert "Net received:" in out


def test_withdraw_paypal_simulation(monkeypatch, capsys):
    run_main_with_args(["0.01", "--withdraw-paypal", "me@example.com"], monkeypatch, capsys)
    out = capsys.readouterr().out
    assert "PayPal withdrawal" in out
    assert "Gross:" in out
