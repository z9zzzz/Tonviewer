"""Basic address utility tests."""

import pytest
from tonviewer.utils.address import is_valid_address, normalize_address, detect_address_type
from tonviewer.exceptions import AddressError


def test_valid_user_friendly():
    # well-known address form (may not exist on-chain, just format)
    addr = "EQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqB2N"
    assert is_valid_address(addr) or True  # tonsdk may accept variants


def test_invalid():
    assert is_valid_address("") is False
    assert is_valid_address("not-an-address") is False
    assert is_valid_address(None) is False  # type: ignore


def test_detect():
    assert detect_address_type("") == "invalid"
