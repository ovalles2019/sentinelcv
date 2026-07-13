"""Tests for TxDOT ITS camera URL parsing and snapshot decoding."""

import base64

import pytest

from app.poller import decode_txdot_snippet, parse_txdot_url


def test_parse_txdot_url():
    district, icd = parse_txdot_url("txdot://DAL/US75 @ IH635 North")
    assert district == "DAL"
    assert icd == "US75 @ IH635 North"


def test_parse_txdot_url_rejects_bad():
    with pytest.raises(ValueError):
        parse_txdot_url("https://example.com/cam.jpg")
    with pytest.raises(ValueError):
        parse_txdot_url("txdot://DAL")


def test_decode_txdot_snippet_jpeg():
    # Minimal valid JPEG SOI + EOI
    jpeg = bytes([0xFF, 0xD8, 0xFF, 0xD9])
    snippet = base64.b64encode(jpeg).decode("ascii")
    assert decode_txdot_snippet(snippet)[:2] == b"\xff\xd8"
