"""Shared CLI text and package-version helpers.

The executable entry point remains in :mod:`tonviewer.cli`; this module keeps
help/version/update functions reusable and avoids putting help text in EPILOG.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Optional

from colorama import Fore, Style


PACKAGE_NAME = "Tonviewer"


def _package_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"


def help() -> str:
    """Return the public CLI help text."""
    return f"""{Fore.RED}Tonviewer{Fore.WHITE} — TON Wallet, Transactions, NFTs and Fragment CLI

Usage:
  {Fore.RED}Tonviewer{Fore.WHITE} [OPTIONS]

Global:
  {Fore.RED}-h, --help{Fore.WHITE}                 Show this help message
  {Fore.RED}-v, -V, --version{Fore.WHITE}          Show version and project links
  {Fore.RED}--check-update{Fore.WHITE}              Check PyPI for a newer release
  {Fore.RED}--json{Fore.WHITE}                     Prefer JSON output where supported

Wallet and transactions:
  {Fore.RED}-w, --wallet ADDRESS{Fore.WHITE}      Wallet address
  {Fore.RED}-i, --info{Fore.WHITE}                Wallet info and NFT count
  {Fore.RED}-t, --transactions [ADDRESS]{Fore.WHITE} Parsed transactions
  {Fore.RED}-r, --raw-transactions{Fore.WHITE}    Raw TON Center v3 transactions
  {Fore.RED}-l, --limit N{Fore.WHITE}              Maximum result count (default: 5)
  {Fore.RED}--offset N{Fore.WHITE}                 Raw transaction offset
  {Fore.RED}--sort asc|desc{Fore.WHITE}            Raw transaction order
  {Fore.RED}-n, --number N{Fore.WHITE}             Transaction number after filtering
  {Fore.RED}-a, --action TYPE{Fore.WHITE}         sent ton, received ton, jetton, nft, scam

Hash, price and Fragment:
  {Fore.RED}-H, --hash, --hashtx HASH{Fore.WHITE} Resolve event/transaction hash
  {Fore.RED}-p, --price{Fore.WHITE}               Live TON/USDT price
  {Fore.RED}-u, -f, --username USERNAME{Fore.WHITE} Fragment username lookup
""".rstrip()


def versions() -> str:
    """Return installed version and project links."""
    pkg_version = _package_version()
    return f"""{Fore.RED}Tonviewer{Fore.WHITE} Version: {Fore.RED}{pkg_version}{Fore.WHITE}
GitHub:   https://github.com/z9zzzz/Tonviewer
PyPI:     https://pypi.org/project/Tonviewer/
""".rstrip()


def check_for_update(package_name: str = PACKAGE_NAME) -> Optional[str]:
    """Return a notice when a newer PyPI version exists, otherwise None."""
    try:
        import requests

        current = _package_version()
        response = requests.get(
            f"https://pypi.org/pypi/{package_name}/json",
            timeout=5,
        )
        response.raise_for_status()
        latest = str(response.json()["info"]["version"])
        if current != "unknown" and latest != current:
            return (
                f"[{Fore.BLUE}notice{Fore.WHITE}] New release available: "
                f"{Fore.RED}{current}{Fore.WHITE} → {Fore.GREEN}{latest}{Fore.WHITE}\n"
                f"Run: {Fore.GREEN}python -m pip install --upgrade {package_name}{Fore.WHITE}"
            )
    except Exception:
        pass
    return None
