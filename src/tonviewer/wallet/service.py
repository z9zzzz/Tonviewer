"""
Wallet service — high-level wallet intelligence.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TonviewerConfig
from ..core.models import AccountState, AddressInfo, ProviderMetadata, PriceInfo
from ..exceptions import AddressError, WalletError, APIError
from ..providers.tonapi import TonAPIProvider
from ..providers.toncenter_v2 import TonCenterV2Provider
from ..providers.toncenter_v3 import TonCenterV3Provider
from ..utils.address import normalize_address, is_valid_address, safe_normalize
from .models import WalletBalance, WalletInfo


TON_DECIMALS = 1_000_000_000
_NFT_ENRICH_CONCURRENCY = 8


def _dedupe_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove repeated indexed events without collapsing rows lacking an id."""
    seen = set()
    unique = []
    for event in events:
        event_id = event.get("event_id") if isinstance(event, dict) else None
        if event_id and event_id in seen:
            continue
        if event_id:
            seen.add(event_id)
        unique.append(event)
    return unique


def _strictly_before(events: List[Dict[str, Any]], cursor: Optional[int]) -> List[Dict[str, Any]]:
    if cursor is None:
        return events
    filtered = []
    for event in events:
        try:
            logical_time = event.get("lt")
            if logical_time is not None and int(logical_time) >= int(cursor):
                continue
        except (TypeError, ValueError):
            pass
        filtered.append(event)
    return filtered


def _add_next_cursor(payload: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = []
    for event in events:
        try:
            if event.get("lt") is not None:
                values.append(int(event["lt"]))
        except (TypeError, ValueError):
            continue
    if values:
        payload["next_before_lt"] = min(values)
    return payload


def _map_status(raw: Optional[str]) -> AccountState:
    if not raw:
        return AccountState.UNKNOWN
    raw = raw.lower()
    mapping = {
        "active": AccountState.ACTIVE,
        "uninit": AccountState.UNINITIALIZED,
        "uninitialized": AccountState.UNINITIALIZED,
        "frozen": AccountState.FROZEN,
        "nonexist": AccountState.NONEXISTENT,
        "nonexistent": AccountState.NONEXISTENT,
        "empty": AccountState.EMPTY,
        "inactive": AccountState.INACTIVE,
    }
    return mapping.get(raw, AccountState.UNKNOWN)


class WalletService:
    def __init__(
        self,
        config: TonviewerConfig,
        tonapi: Optional[TonAPIProvider] = None,
        v2: Optional[TonCenterV2Provider] = None,
        v3: Optional[TonCenterV3Provider] = None,
        price_ton_usd: Optional[float] = None,
    ):
        self.config = config
        self.tonapi = tonapi
        self.v2 = v2
        self.v3 = v3
        self._price = price_ton_usd

    def _normalize(self, address: str) -> str:
        if not is_valid_address(address):
            raise AddressError(f"Invalid TON address: {address}")
        return normalize_address(address)

    async def _get_nfts_count(self, address: str, known_count: Optional[int] = None) -> Optional[int]:
        if known_count is not None:
            return int(known_count)
        if not self.tonapi:
            return None
        try:
            total = 0
            offset = 0
            while True:
                data = await self.tonapi.get_nfts(address, limit=1000, offset=offset)
                items = data.get("nft_items") or data.get("items") or []
                total += len(items)
                if len(items) < 1000:
                    return total
                offset += len(items)
        except Exception:
            return None

    def _get_nfts_count_sync(self, address: str, known_count: Optional[int] = None) -> Optional[int]:
        if known_count is not None:
            return int(known_count)
        if not self.tonapi:
            return None
        try:
            total = 0
            offset = 0
            while True:
                data = self.tonapi.get_nfts_sync(address, limit=1000, offset=offset)
                items = data.get("nft_items") or data.get("items") or []
                total += len(items)
                if len(items) < 1000:
                    return total
                offset += len(items)
        except Exception:
            return None

    async def _enrich_nft_names(self, events: List[Dict[str, Any]]) -> None:
        """Attach NFT metadata names to transfer actions when available."""
        if not self.tonapi:
            return
        targets: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            for action in event.get("actions") or []:
                kind = action.get("type")
                payload = (action.get(kind) or {}) if kind else {}
                if kind not in {"NftItemTransfer", "NftPurchase"} or not isinstance(payload, dict):
                    continue
                nft = payload.get("nft") or payload.get("item") or payload.get("nft_item")
                if isinstance(nft, dict):
                    if nft.get("name"):
                        payload["nft_name"] = nft["name"]
                    nft = nft.get("address")
                if nft:
                    targets.setdefault(str(nft), []).append(payload)
        if not targets:
            return
        semaphore = asyncio.Semaphore(_NFT_ENRICH_CONCURRENCY)

        async def resolve(address: str):
            async with semaphore:
                try:
                    return address, await self.tonapi.get_nft_item(address)
                except Exception:
                    # Metadata enrichment is optional; do not drop the action.
                    return address, None

        results = await asyncio.gather(*(resolve(address) for address in targets))
        for address, result in results:
            if not isinstance(result, dict):
                continue
            metadata = result.get("metadata") or {}
            name = metadata.get("name") or result.get("name")
            if name:
                for payload in targets[address]:
                    payload["nft_name"] = name

    def _enrich_nft_names_sync(self, events: List[Dict[str, Any]]) -> None:
        if not self.tonapi:
            return
        seen = set()
        for event in events:
            for action in event.get("actions") or []:
                kind = action.get("type")
                payload = (action.get(kind) or {}) if kind else {}
                if kind not in {"NftItemTransfer", "NftPurchase"} or not isinstance(payload, dict):
                    continue
                nft = payload.get("nft") or payload.get("item") or payload.get("nft_item")
                if isinstance(nft, dict):
                    if nft.get("name"):
                        payload["nft_name"] = nft["name"]
                    nft = nft.get("address")
                if not nft:
                    continue
                nft = str(nft)
                if nft in seen:
                    continue
                seen.add(nft)
                try:
                    result = self.tonapi.get_nft_item_sync(nft)
                    metadata = result.get("metadata") or {}
                    name = metadata.get("name") or result.get("name")
                    if name:
                        payload["nft_name"] = name
                except Exception:
                    continue

    async def get_info(self, address: str) -> WalletInfo:
        addr = self._normalize(address)
        last_err: Optional[Exception] = None

        # Prefer TONAPI for rich metadata
        if self.tonapi and self.config.use_tonapi:
            try:
                data = await self.tonapi.get_account(addr)
                data["_nfts_count"] = await self._get_nfts_count(addr, (data.get("stats") or {}).get("nfts_count"))
                return self._from_tonapi(addr, data)
            except Exception as exc:
                last_err = exc

        # Fallback to TON Center v2
        if self.v2 and self.config.use_toncenter_v2:
            try:
                data = await self.v2.get_account(addr)
                return self._from_v2(addr, data)
            except Exception as exc:
                last_err = exc

        if last_err:
            raise WalletError(
                f"Failed to fetch wallet info for {addr}",
                details={"cause": str(last_err)},
            ) from last_err
        raise WalletError("No providers available for wallet info")

    def get_info_sync(self, address: str) -> WalletInfo:
        addr = self._normalize(address)
        last_err: Optional[Exception] = None

        if self.tonapi and self.config.use_tonapi:
            try:
                data = self.tonapi.get_account_sync(addr)
                data["_nfts_count"] = self._get_nfts_count_sync(addr, (data.get("stats") or {}).get("nfts_count"))
                return self._from_tonapi(addr, data)
            except Exception as exc:
                last_err = exc

        if self.v2 and self.config.use_toncenter_v2:
            try:
                data = self.v2.get_account_sync(addr)
                return self._from_v2(addr, data)
            except Exception as exc:
                last_err = exc

        if last_err:
            raise WalletError(
                f"Failed to fetch wallet info for {addr}",
                details={"cause": str(last_err)},
            ) from last_err
        raise WalletError("No providers available for wallet info")

    async def get_balance(self, address: str) -> WalletBalance:
        info = await self.get_info(address)
        return info.balance

    def get_balance_sync(self, address: str) -> WalletBalance:
        info = self.get_info_sync(address)
        return info.balance

    def _from_tonapi(self, addr: str, data: Dict[str, Any]) -> WalletInfo:
        balance_nano = int(data.get("balance", 0) or 0)
        ton = balance_nano / TON_DECIMALS
        usd = (ton * self._price) if self._price is not None else None

        status = _map_status(data.get("status"))
        last_act = data.get("last_activity")
        last_dt = None
        if last_act:
            try:
                last_dt = datetime.utcfromtimestamp(int(last_act))
            except Exception:
                pass

        interfaces = data.get("interfaces") or []
        is_wallet = data.get("is_wallet")
        if is_wallet is None and interfaces:
            is_wallet = any("wallet" in i.lower() for i in interfaces)

        return WalletInfo(
            address=addr,
            address_info=AddressInfo(
                user_friendly=addr,
                raw=data.get("address"),
                is_valid=True,
            ),
            balance=WalletBalance(
                nanotons=balance_nano,
                ton=ton,
                usd=usd,
                price=PriceInfo(ton_usd=self._price, source="binance") if self._price else None,
            ),
            status=status,
            is_wallet=is_wallet,
            last_activity=last_dt,
            name=data.get("name"),
            icon=data.get("icon"),
            nfts_count=(data.get("stats") or {}).get("nfts_count") if data.get("_nfts_count") is None else data.get("_nfts_count"),
            interfaces=list(interfaces),
            contract_type=interfaces[0] if interfaces else None,
            explorer_url=f"https://tonviewer.com/{addr}",
            provider=ProviderMetadata(provider="tonapi", raw=data if self.config.enable_cache else None),
            raw=data,
        )

    def _from_v2(self, addr: str, data: Dict[str, Any]) -> WalletInfo:
        # TON Center v2 getAddressInformation shape
        balance_nano = int(data.get("balance", 0) or 0)
        ton = balance_nano / TON_DECIMALS
        usd = (ton * self._price) if self._price is not None else None
        state = data.get("state", "unknown")
        status = _map_status(state)

        return WalletInfo(
            address=addr,
            balance=WalletBalance(nanotons=balance_nano, ton=ton, usd=usd),
            status=status,
            is_wallet=None,
            explorer_url=f"https://tonviewer.com/{addr}",
            provider=ProviderMetadata(provider="toncenter_v2", raw=data if self.config.enable_cache else None),
            raw=data,
        )


    # ------------------------------------------------------------------
    # Transactions / Actions
    # ------------------------------------------------------------------

    async def get_raw_transactions(
        self, address: str, *, limit: int = 1000, offset: int = 0, sort: str = "desc"
    ) -> Dict[str, Any]:
        """Return raw indexed transactions from TON Center v3 for auditing."""
        addr = self._normalize(address)
        if not self.v3:
            raise WalletError("TON Center v3 provider is required for raw transactions")
        return await self.v3.get_transactions(addr, limit=limit, offset=offset, sort=sort)

    def get_raw_transactions_sync(
        self, address: str, *, limit: int = 1000, offset: int = 0, sort: str = "desc"
    ) -> Dict[str, Any]:
        addr = self._normalize(address)
        if not self.v3:
            raise WalletError("TON Center v3 provider is required for raw transactions")
        return self.v3.get_transactions_sync(addr, limit=limit, offset=offset, sort=sort)

    async def get_transactions(
        self,
        address: str,
        *,
        limit: int = 20,
        action: Optional[str] = None,
        number: Optional[int] = None,
        before_lt: Optional[int] = None,
        lt: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch and parse account events into the rich transactions format."""
        from .transactions import build_transactions_payload

        addr = self._normalize(address)
        if not self.tonapi:
            raise WalletError("TONAPI provider required for transactions")
        if before_lt is not None and lt is not None and before_lt != lt:
            raise ValueError("before_lt and lt must match when both are supplied")
        cursor = before_lt if before_lt is not None else lt

        # Fetch a bit more when filtering so limit still returns enough rows
        fetch_limit = limit
        if action or number is not None:
            fetch_limit = max(limit * 3, 50)

        try:
            data = await self.tonapi.get_account_events(
                addr, limit=fetch_limit, before_lt=cursor
            )
            events = _strictly_before(_dedupe_events(data.get("events") or data.get("items") or []), cursor)
            await self._enrich_nft_names(events)
        except APIError:
            raise
        except Exception as exc:
            raise WalletError(f"Failed to fetch transactions for {addr}") from exc

        payload = build_transactions_payload(
            events,
            wallet_address=addr,
            dollar_rate=self._price,
            action=action,
            limit=limit,
            number=number,
        )
        return _add_next_cursor(payload, events)

    def get_transactions_sync(
        self,
        address: str,
        *,
        limit: int = 20,
        action: Optional[str] = None,
        number: Optional[int] = None,
        before_lt: Optional[int] = None,
        lt: Optional[int] = None,
    ) -> Dict[str, Any]:
        from .transactions import build_transactions_payload

        addr = self._normalize(address)
        if not self.tonapi:
            raise WalletError("TONAPI provider required for transactions")
        if before_lt is not None and lt is not None and before_lt != lt:
            raise ValueError("before_lt and lt must match when both are supplied")
        cursor = before_lt if before_lt is not None else lt

        fetch_limit = limit
        if action or number is not None:
            fetch_limit = max(limit * 3, 50)

        try:
            data = self.tonapi.get_account_events_sync(
                addr, limit=fetch_limit, before_lt=cursor
            )
            events = _strictly_before(_dedupe_events(data.get("events") or data.get("items") or []), cursor)
            self._enrich_nft_names_sync(events)
        except APIError:
            raise
        except Exception as exc:
            raise WalletError(f"Failed to fetch transactions for {addr}") from exc

        payload = build_transactions_payload(
            events,
            wallet_address=addr,
            dollar_rate=self._price,
            action=action,
            limit=limit,
            number=number,
        )
        return _add_next_cursor(payload, events)
