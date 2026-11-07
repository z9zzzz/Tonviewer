"""
Backward-compatible synchronous wrappers matching the original public API.
Also exposes rich transaction formatting.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

from .config import TonviewerConfig
from .providers.tonapi import TonAPIProvider
from .providers.toncenter_v2 import TonCenterV2Provider
from .providers.toncenter_v3 import TonCenterV3Provider
from .wallet.service import WalletService
from .prices.service import PriceService
from .exceptions import TonviewerError, AddressError
from .wallet.transactions import _looks_like_scam, _try_friendly


def _drop_empty(value: Any) -> Any:
    """Remove None, blank strings and empty containers from printed output."""
    if isinstance(value, dict):
        cleaned = {}
        for key, raw in value.items():
            item = _drop_empty(raw)
            if item is not None and item != "" and item != [] and item != {}:
                cleaned[key] = item
        return cleaned
    if isinstance(value, list):
        return [item for raw in value if (item := _drop_empty(raw)) is not None and item != "" and item != [] and item != {}]
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _event_time(timestamp: Any) -> str:
    """Format an event timestamp in the same local time style as the CLI output."""
    if not timestamp:
        return ""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %I:%M:%S %p")
    except (TypeError, ValueError, OSError):
        return str(timestamp)


def _address(value: Any) -> str:
    """Return a friendly address with an optional cleaned account name."""
    name = ""
    if isinstance(value, dict):
        name = " ".join(str(value.get("name") or "").split())
        value = value.get("address") or ""
    if not value:
        return name
    address = _try_friendly(value)
    if name and name not in {str(value).strip(), address}:
        return f"{address} ({name})"
    return address


def _status(value: Any) -> str:
    status = str(value or "unknown").strip().lower()
    if status in {"ok", "success", "completed", "confirmed", "finalized"}:
        return "SUCCESS"
    if status in {"failed", "fail", "error", "reverted"}:
        return "FAILED"
    return status.upper()


def _action_type(action: dict[str, Any]) -> str:
    raw = str(action.get("type") or "Action")
    names = {
        "TonTransfer": "TON Transfer",
        "JettonTransfer": "Jetton Transfer",
        "JettonMint": "Jetton Mint",
        "JettonBurn": "Jetton Burn",
        "NftItemTransfer": "NFT Transfer",
        "NftPurchase": "NFT Purchase",
        "ContractDeploy": "Contract Deploy",
        "SmartContractExec": "Smart Contract Execution",
    }
    if raw in names:
        return names[raw]
    # Keep unknown future TONAPI actions readable without dropping them.
    return " ".join(part for part in raw.replace("_", " ").split())


def _clean_number(value: Decimal) -> str:
    # Keep the output compact (the CLI examples use four decimals), but do
    # not turn a small non-zero transfer into "0" after rounding.
    rounded = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if value != 0 and rounded == 0:
        rounded = value.quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)
    text = format(rounded, "f").rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _format_amount(
    amount: Any,
    *,
    decimals: int = 9,
    symbol: str = "Ton",
    raw_units: bool = True,
) -> str:
    try:
        number = Decimal(str(amount))
        if raw_units:
            number /= Decimal(10) ** int(decimals)
    except (InvalidOperation, TypeError, ValueError, ArithmeticError):
        return ""
    return f"{_clean_number(number)} {symbol or 'Ton'}"


def _format_price_object(value: Any) -> str:
    """Format TONAPI Price objects without assuming one currency shape."""
    if not isinstance(value, dict):
        return ""
    amount = value.get("amount")
    if amount is None:
        amount = value.get("value")
    if amount is None:
        return ""
    currency = value.get("currency") or {}
    if not isinstance(currency, dict):
        currency = {}
    currency_type = str(currency.get("type") or "native").lower()
    if currency_type in {"native", "ton", "gram", "grams"}:
        return _format_amount(amount, decimals=9, symbol="Ton")
    jetton = currency.get("jetton") or {}
    if not isinstance(jetton, dict):
        jetton = {}
    symbol = (
        jetton.get("symbol")
        or currency.get("symbol")
        or currency.get("name")
        or "Jetton"
    )
    decimals = jetton.get("decimals", currency.get("decimals", 9))
    return _format_amount(amount, decimals=int(decimals or 0), symbol=str(symbol))


def _action_price(kind: str, payload: dict[str, Any], preview: dict[str, Any]) -> str:
    """Return the most specific user-facing value for an action."""
    # TONAPI's native amounts are nanotons; keep exact values until formatting.
    if kind in {"TonTransfer", "SmartContractExec", "ContractDeploy"}:
        for key in ("amount", "ton_attached", "gram_attached"):
            if key in payload and payload.get(key) is not None:
                return _format_amount(payload[key], decimals=9, symbol="Ton")

    if kind == "GasRelay":
        if payload.get("amount") is not None:
            return _format_amount(payload["amount"], decimals=9, symbol="Ton")
        fee = payload.get("relayer_fee") or payload.get("relayerFee")
        return _format_price_object({"amount": (fee or {}).get("amount"), "currency": {"jetton": fee.get("jetton")}}) if isinstance(fee, dict) else ""

    # These actions can have a preview value (for example, "1 NFT"), but
    # that is not a monetary price. Leave Price empty unless TONAPI supplies
    # an actual price/amount field for them.
    if kind in {
        "NftItemTransfer",
        "ContractDeploy",
        "SetSignatureAllowed",
        "PoolRoundTransition",
    }:
        return ""

    if kind in {"JettonTransfer", "FlawedJettonTransfer", "JettonMint", "JettonBurn"}:
        amount = (
            payload.get("received_amount")
            or payload.get("amount")
            or payload.get("sent_amount")
        )
        jetton = payload.get("jetton") or {}
        if not isinstance(jetton, dict):
            jetton = {}
        return _format_amount(
            amount,
            decimals=int(jetton.get("decimals", 9) or 0),
            symbol=str(jetton.get("symbol") or "Jetton"),
        ) if amount is not None else ""

    if kind in {"NftPurchase", "Subscribe", "UnSubscribe", "AuctionBid", "Purchase"}:
        formatted = _format_price_object(payload.get("price") or payload.get("amount"))
        if formatted:
            return formatted

    if kind in {"ExtraCurrencyTransfer"}:
        currency = payload.get("currency") or {}
        if not isinstance(currency, dict):
            currency = {}
        return _format_amount(
            payload.get("amount"),
            decimals=int(currency.get("decimals", 0) or 0),
            symbol=str(currency.get("symbol") or "Extra Currency"),
        ) if payload.get("amount") is not None else ""

    # A preview is the last resort for newly introduced actions. It is never
    # used in preference to a numeric field from the action payload.
    preview_value = preview.get("value") or preview.get("fiat_value") or ""
    return " ".join(str(preview_value).split())


def _payload_and_comment(payload: dict[str, Any]) -> tuple[str, str]:
    """Split TONAPI payload/comment text into compact display fields."""
    def clean_comment(value: Any) -> str:
        # TONAPI appends payment references such as Ref#r1WRdaFho;
        # they are implementation metadata, not a user-facing comment.
        text = re.sub(r"Ref#\S+", "", str(value or ""), flags=re.IGNORECASE)
        return " ".join(text.split())

    raw_payload = payload.get("payload")
    raw_comment = payload.get("comment")

    if raw_payload is not None:
        payload_text = " ".join(str(raw_payload).split())
        comment_text = clean_comment(raw_comment)
        return payload_text, comment_text

    if raw_comment is None:
        return "", ""

    lines = [
        clean_comment(line)
        for line in str(raw_comment).splitlines()
        if clean_comment(line)
    ]
    if not lines:
        return "", ""
    return lines[0], " ".join(lines[1:])


def _normalized_event(
    data: dict[str, Any],
    *,
    nft_resolver: Any = None,
) -> dict[str, Any]:
    """Convert a TONAPI event into the compact public HashTx representation."""
    timestamp = data.get("timestamp")
    formatted_time = _event_time(timestamp)
    normalized: list[dict[str, Any]] = []

    for action_number, action in enumerate(data.get("actions") or [], start=1):
        if not isinstance(action, dict):
            continue
        kind = str(action.get("type") or "")
        payload = action.get(kind) or {}
        if not isinstance(payload, dict):
            payload = {}

        # TONAPI uses different participant names by action type. Keep this
        # table display-oriented: events are for presentation, not accounting.
        participant_keys = {
            "TonTransfer": (("sender",), ("recipient",)),
            "ExtraCurrencyTransfer": (("sender",), ("recipient",)),
            "SmartContractExec": (("executor", "sender"), ("contract", "recipient")),
            "GasRelay": (("relayer",), ("target",)),
            "NftItemTransfer": (("sender",), ("recipient",)),
            "NftPurchase": (("seller", "sender"), ("buyer", "recipient")),
            "JettonTransfer": (("sender",), ("recipient",)),
            "FlawedJettonTransfer": (("sender",), ("recipient",)),
            "JettonMint": (("jetton",), ("recipient",)),
            "JettonBurn": (("owner", "sender"), ("senders_wallet",)),
            "ContractDeploy": (("deployer", "sender"), ("address", "contract")),
            "Subscribe": (("subscriber",), ("withdraw_to", "beneficiary", "admin")),
            "UnSubscribe": (("subscriber",), ("withdraw_to", "beneficiary", "admin")),
            "ElectionsDepositStake": (("staker",), ("elector",)),
            "ElectionsRecoverStake": (("elector",), ("staker",)),
            "DepositStake": (("staker",), ("pool",)),
            "WithdrawStake": (("pool",), ("staker",)),
            "WithdrawStakeRequest": (("staker",), ("pool",)),
            "DepositTokenStake": (("staker",), ("protocol",)),
            "WithdrawTokenStakeRequest": (("staker",), ("protocol",)),
            "JettonSwap": (("user_wallet", "userWallet"), ("router",)),
            "AuctionBid": (("bidder",), ("auction",)),
            "DomainRenew": (("renewer",), ("item", "contract_address")),
            "Purchase": (("source",), ("destination",)),
            "AddExtension": (("wallet",), ("extension",)),
            "RemoveExtension": (("wallet",), ("extension",)),
            "SetSignatureAllowed": (("wallet",), ()),
            "LiquidityDeposit": (("from",), ()),
            "OracleRequest": (("requester",), ("response_to", "oracle")),
            "BuyXTR": ((), ("recipient",)),
            "DepositXTR": ((), ("recipient",)),
            "WithdrawXTR": (("user",), ("jetton_master",)),
            "LoanRequest": (("borrower",), ("pool",)),
            "LoanIssue": (("pool",), ("borrower",)),
            "LoanRepayment": (("borrower",), ("pool",)),
            "PoolRoundTransition": (("pool",), ()),
        }

        def pick(keys: tuple[str, ...]) -> Any:
            for key in keys:
                value = payload.get(key)
                if value:
                    return value
            return {}

        known_participant_shape = kind in participant_keys
        from_keys, to_keys = participant_keys.get(
            kind, (("sender", "executor", "source", "from"), ("recipient", "contract", "destination", "to"))
        )
        from_obj = pick(from_keys)
        to_obj = pick(to_keys)

        # Future/unknown actions may expose only preview accounts. This keeps
        # From/To useful without guessing a semantic direction for known fields.
        preview = action.get("simple_preview") or {}
        preview_accounts = preview.get("accounts") or []
        if not known_participant_shape:
            if not from_obj and preview_accounts:
                from_obj = preview_accounts[0]
            if not to_obj and len(preview_accounts) > 1:
                to_obj = preview_accounts[1]

        nft = payload.get("nft") or payload.get("item") or ""
        if isinstance(nft, dict):
            nft_name = (
                nft.get("name")
                or nft.get("dns")
                or (nft.get("metadata") or {}).get("name")
                or nft.get("address")
                or ""
            )
        else:
            nft_name = str(nft) if nft else ""

        # The event payload usually contains only the NFT address. Resolve its
        # metadata once so usernames, domains, and collectible names are shown.
        if kind in {"NftItemTransfer", "NftPurchase"} and nft_name and nft_resolver:
            try:
                nft_data = nft_resolver(nft_name)
                metadata = nft_data.get("metadata") or {}
                nft_name = (
                    nft_data.get("dns")
                    or metadata.get("name")
                    or nft_data.get("name")
                    or nft_name
                )
            except Exception:
                pass

        # A transfer action often carries the username/domain on the recipient,
        # while generic NFTs only expose their address. Prefer explicit metadata.
        if kind in {"NftItemTransfer", "NftPurchase"} and not nft_name:
            nft_name = str(
                (to_obj or {}).get("name")
                or (from_obj or {}).get("name")
                or ""
            )

        payload_text, comment_text = _payload_and_comment(payload)
        item = {
            "Type": _action_type(action),
            "Status": _status(action.get("status")),
            "Time": formatted_time,
            "From": _address(from_obj),
            "To": _address(to_obj),
            "Price": _action_price(kind, payload, preview),
            "Scam": _looks_like_scam(
                event_scam=bool(data.get("is_scam")),
                sender=from_obj,
                recipient=to_obj,
                comment=f"{payload_text} {comment_text}".strip(),
                preview=preview,
            ),
        }
        if kind in {"NftItemTransfer", "NftPurchase"}:
            item["NFT"] = nft_name
        item["Payload"] = payload_text
        item["#"] = action_number
        normalized.append(_drop_empty(item))

    return _drop_empty({
        "event_id": data.get("event_id") or "",
        "timestamp": formatted_time,
        "action_count": len(normalized),
        "actions": normalized,
    })


class Wallet:
    """
    Original synchronous Wallet interface.

    Example:
        from tonviewer import Wallet
        w = Wallet("UQ...")
        print(w.info())
        print(w.transactions(limit=5))
        print(w.action(action="sent ton", limit=10))
        print(w.transactions(limit=20, number=3))  # only transaction #3
    """

    def __init__(self, wallet: Optional[str] = None):
        self.wallet = wallet
        self._config = TonviewerConfig()
        self._tonapi = TonAPIProvider(self._config.tonapi) if self._config.use_tonapi else None
        self._v2 = TonCenterV2Provider(self._config.toncenter_v2) if self._config.use_toncenter_v2 else None
        self._v3 = TonCenterV3Provider(self._config.toncenter_v3) if self._config.use_toncenter_v3 else None
        self._price = None
        price_service = PriceService(self._config)
        try:
            self._price = price_service.get_ton_usd()
        except Exception:
            pass
        finally:
            price_service.close()
        self._svc = WalletService(
            self._config,
            tonapi=self._tonapi,
            v2=self._v2,
            v3=self._v3,
            price_ton_usd=self._price,
        )

    def info(self) -> str:
        if not self.wallet:
            return json.dumps({"error": "No wallet address provided"}, indent=2)
        try:
            info = self._svc.get_info_sync(self.wallet)
            return json.dumps(_drop_empty(info.to_legacy_json()), indent=2, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False)

    def transactions(
        self,
        limit: int = 10,
        *,
        action: Optional[str] = None,
        number: Optional[int] = None,
        before_lt: Optional[int] = None,
        lt: Optional[int] = None,
    ) -> str:
        """
        Rich transaction list.

        Parameters
        ----------
        limit : max rows to return
        action : filter, e.g. "sent ton", "received ton", "jetton", "nft", "scam"
        number : return only the transaction with this display number (#)
        """
        if not self.wallet:
            return json.dumps({"error": "No wallet address provided"}, indent=2)
        try:
            payload = self._svc.get_transactions_sync(
                self.wallet,
                limit=limit,
                action=action,
                number=number,
                before_lt=before_lt,
                lt=lt,
            )
            return json.dumps(_drop_empty(payload), indent=2, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False)

    def action(self, action: str = "sent ton", limit: int = 10, number: Optional[int] = None) -> str:
        """
        Filtered transactions by action type.

        Examples:
            wallet.action(action="sent ton", limit=10)
            wallet.action(action="received ton", limit=5)
            wallet.action(action="scam", limit=20)
        """
        return self.transactions(limit=limit, action=action, number=number)

    def raw_transactions(self, limit: int = 1000, offset: int = 0, sort: str = "desc") -> str:
        """Return raw TON Center v3 transactions without event reshaping."""
        try:
            data = self._svc.get_raw_transactions_sync(
                self.wallet, limit=limit, offset=offset, sort=sort
            )
            return json.dumps(_drop_empty(data), indent=2, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False)


class HashTx:
    """
    Resolve a transaction / event by hash or event id.
    """

    def __init__(self, hashtx: Optional[str] = None):
        self.hashtx = hashtx
        self._config = TonviewerConfig()
        self._tonapi = TonAPIProvider(self._config.tonapi) if self._config.use_tonapi else None

    def get(self) -> str:
        if not self.hashtx:
            return json.dumps({"error": "No hash provided"}, indent=2)
        try:
            if self._tonapi:
                data = self._tonapi.get_event_sync(self.hashtx)
                nft_cache: dict[str, dict[str, Any]] = {}

                def resolve_nft(address: str) -> dict[str, Any]:
                    if address not in nft_cache:
                        nft_cache[address] = self._tonapi.get_nft_item_sync(address)
                    return nft_cache[address]

                return json.dumps(
                    _drop_empty(_normalized_event(data, nft_resolver=resolve_nft)),
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            return json.dumps({"error": "TONAPI provider required for event resolution"}, indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False)
