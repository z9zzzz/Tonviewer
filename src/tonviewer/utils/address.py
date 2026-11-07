"""
TON address utilities — validation, normalization, conversion.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from tonsdk.utils import Address as TonAddress

from ..exceptions import AddressError


# Common regex patterns
_USER_FRIENDLY_RE = re.compile(r"^[EUeu][Qq][A-Za-z0-9_-]{46}$")
_RAW_RE = re.compile(r"^-?[0-9]+:[a-fA-F0-9]{64}$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def is_valid_address(addr: str) -> bool:
    """Quick syntactic check (does not guarantee the address exists on-chain)."""
    if not addr or not isinstance(addr, str):
        return False
    addr = addr.strip()
    try:
        TonAddress(addr)
        return True
    except Exception:
        return False


def normalize_address(
    addr: str,
    *,
    bounceable: bool = False,
    url_safe: bool = True,
    test_only: bool = False,
) -> str:
    """
    Normalize any supported address form to a user-friendly string.

    Raises AddressError on invalid input.
    """
    if not addr or not isinstance(addr, str):
        raise AddressError("Address must be a non-empty string")
    addr = addr.strip()
    try:
        a = TonAddress(addr)
        return a.to_string(
            is_user_friendly=True,
            is_url_safe=url_safe,
            is_bounceable=bounceable,
            is_test_only=test_only,
        )
    except Exception as exc:
        raise AddressError(f"Invalid TON address: {addr}") from exc


def to_raw(addr: str) -> str:
    """Return raw form workchain:hex."""
    try:
        a = TonAddress(addr)
        return a.to_string(is_user_friendly=False)
    except Exception as exc:
        raise AddressError(f"Invalid TON address: {addr}") from exc


def parse_address(addr: str) -> Tuple[int, bytes]:
    """Return (workchain, hash_part) as bytes."""
    try:
        a = TonAddress(addr)
        return a.wc, a.hash_part
    except Exception as exc:
        raise AddressError(f"Invalid TON address: {addr}") from exc


def detect_address_type(addr: str) -> str:
    """Return one of: user_friendly, raw, hex, invalid."""
    if not addr or not isinstance(addr, str):
        return "invalid"
    addr = addr.strip()
    if not is_valid_address(addr):
        return "invalid"
    try:
        parsed = TonAddress(addr)
        return "user_friendly" if parsed.is_user_friendly else "raw"
    except Exception:
        if _HEX_RE.fullmatch(addr):
            return "hex"
    return "invalid"


def safe_normalize(addr: Optional[str]) -> Optional[str]:
    """Normalize or return None on failure (never raises)."""
    if not addr:
        return None
    try:
        return normalize_address(addr)
    except AddressError:
        return None
