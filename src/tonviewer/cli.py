"""Professional command-line interface for Tonviewer."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from colorama import Fore, Style, init as colorama_init

from .client import TonviewerClient
from .compat import HashTx, Wallet, _drop_empty
from .main import check_for_update, help as cli_help, versions
from .prices.service import PriceService

colorama_init(autoreset=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Tonviewer",
        description="Tonviewer — TON Wallet, Transactions, NFTs and Fragment CLI",
        add_help=False,
    )

    # Global actions
    parser.add_argument(
        "-h", "--help", action="store_true",
        help="show the full help text from main.py",
    )
    parser.add_argument(
        "-v",
        "-V",
        "--version",
        action="store_true",
        help="show the installed Tonviewer version and project links",
    )
    parser.add_argument(
        "--check-update", action="store_true",
        help="check PyPI for a newer Tonviewer release",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="force JSON output where a command supports multiple formats",
    )

    # Wallet and transaction actions
    wallet_group = parser.add_argument_group("Wallet and transactions")
    wallet_group.add_argument(
        "-w",
        "--wallet",
        metavar="ADDRESS",
        help="wallet address (used with --info, --transactions or --raw-transactions)",
    )
    wallet_group.add_argument(
        "-i",
        "--info",
        action="store_true",
        help="show balance, status, activity, name, icon and NFT count",
    )
    wallet_group.add_argument(
        "-t",
        "--transactions",
        nargs="?",
        const="",
        default=None,
        metavar="ADDRESS",
        help="show parsed transactions; optionally provide the wallet address",
    )
    wallet_group.add_argument(
        "-r",
        "--raw-transactions",
        action="store_true",
        help="show raw TON Center v3 transactions without event reshaping",
    )
    wallet_group.add_argument(
        "-l",
        "--limit",
        type=int,
        default=5,
        metavar="N",
        help="maximum transactions/actions to return (default: 5)",
    )
    wallet_group.add_argument(
        "--offset",
        type=int,
        default=0,
        metavar="N",
        help="raw transaction offset for pagination (default: 0)",
    )
    wallet_group.add_argument(
        "--sort",
        choices=("asc", "desc"),
        default="desc",
        help="raw transaction order (default: desc)",
    )
    wallet_group.add_argument(
        "-n",
        "--number",
        type=int,
        default=None,
        metavar="N",
        help="return only transaction number N after filtering",
    )
    wallet_group.add_argument(
        "-a",
        "--action",
        default=None,
        metavar="TYPE",
        help="filter: sent ton, received ton, jetton, nft, scam",
    )

    # Hash and utility actions
    utility_group = parser.add_argument_group("Hash and utilities")
    utility_group.add_argument(
        "-H",
        "--hash",
        "--hashtx",
        dest="hashtx",
        metavar="HASH",
        help="resolve an event/transaction hash into its action breakdown",
    )
    utility_group.add_argument(
        "-p",
        "--price",
        action="store_true",
        help="show the live TON/USDT price",
    )
    utility_group.add_argument(
        "-u",
        "--username",
        "-f",
        "--fragment",
        dest="username",
        metavar="USERNAME",
        help="look up a Fragment username (with or without @)",
    )

    return parser


def _print_version() -> None:
    print(versions())


def _print_error(exc: Exception) -> None:
    print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.help:
        print(cli_help())
        return 0
    if args.version:
        _print_version()
        if args.check_update:
            notice = check_for_update()
            if notice:
                print(notice)
        return 0

    if args.check_update:
        notice = check_for_update()
        print(notice or "Tonviewer is up to date or the update check was unavailable.")
        return 0

    if args.limit < 0:
        parser.error("--limit must be greater than or equal to 0")
    if args.offset < 0:
        parser.error("--offset must be greater than or equal to 0")
    if args.number is not None and args.number < 1:
        parser.error("--number must be greater than or equal to 1")

    if args.price:
        try:
            price = PriceService().get_ton_usd()
            print(f"{Fore.GREEN}TON/USDT: {price:.4f}{Style.RESET_ALL}")
            return 0
        except Exception as exc:
            _print_error(exc)
            return 1

    if args.hashtx:
        try:
            print(HashTx(hashtx=args.hashtx).get())
            return 0
        except Exception as exc:
            _print_error(exc)
            return 1

    if args.username:
        async def _run_fragment() -> None:
            client = TonviewerClient()
            try:
                result = await client.fragment.get_username(args.username.lstrip("@"))
                print(json.dumps(_drop_empty(result.to_dict()), indent=2, ensure_ascii=False, default=str))
            finally:
                await client.aclose()

        try:
            asyncio.run(_run_fragment())
            return 0
        except Exception as exc:
            _print_error(exc)
            return 1

    # Resolve address: explicit -w wins; otherwise use -t ADDRESS.
    address = args.wallet
    wants_transactions = args.transactions is not None
    if wants_transactions and args.transactions:
        address = args.transactions

    if args.raw_transactions and not address:
        parser.error("--raw-transactions requires -w/--wallet or -t ADDRESS")

    if args.raw_transactions and (args.action or args.number is not None):
        parser.error("--raw-transactions cannot be combined with --action or --number")

    if address:
        wallet = Wallet(address)

        if args.raw_transactions:
            try:
                print(wallet.raw_transactions(limit=args.limit, offset=args.offset, sort=args.sort))
                return 0
            except Exception as exc:
                _print_error(exc)
                return 1

        if args.info or not wants_transactions:
            print(wallet.info())
        if wants_transactions:
            print(
                wallet.transactions(
                    limit=args.limit,
                    action=args.action,
                    number=args.number,
                )
            )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
