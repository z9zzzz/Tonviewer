"""
TONAPI (tonapi.io) provider — rich indexed data, good for NFTs, Jettons, events.
Used as primary or strong fallback for high-level wallet intelligence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseProvider


class TonAPIProvider(BaseProvider):
    name = "tonapi"

    async def get_account(self, address: str) -> Dict[str, Any]:
        return await self.async_.get(f"accounts/{address}")

    async def get_rates(self, *, tokens: str = "ton", currencies: str = "usd") -> Dict[str, Any]:
        return await self.async_.get(
            "rates",
            params={"tokens": tokens, "currencies": currencies},
        )

    def get_account_sync(self, address: str) -> Dict[str, Any]:
        return self.sync.get(f"accounts/{address}")

    async def get_account_events(
        self,
        address: str,
        *,
        limit: int = 20,
        before_lt: Optional[int] = None,
        lt: Optional[int] = None,
        subject_only: bool = False,
    ) -> Dict[str, Any]:
        if before_lt is not None and lt is not None and before_lt != lt:
            raise ValueError("before_lt and lt must match when both are supplied")
        cursor = before_lt if before_lt is not None else lt
        params: Dict[str, Any] = {"limit": limit, "subject_only": subject_only}
        if cursor is not None:
            params["before_lt"] = cursor
        return await self.async_.get(f"accounts/{address}/events", params=params)

    def get_account_events_sync(
        self,
        address: str,
        *,
        limit: int = 20,
        before_lt: Optional[int] = None,
        lt: Optional[int] = None,
    ) -> Dict[str, Any]:
        if before_lt is not None and lt is not None and before_lt != lt:
            raise ValueError("before_lt and lt must match when both are supplied")
        cursor = before_lt if before_lt is not None else lt
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["before_lt"] = cursor
        return self.sync.get(f"accounts/{address}/events", params=params)

    async def get_jettons(self, address: str) -> Dict[str, Any]:
        return await self.async_.get(f"accounts/{address}/jettons")

    async def get_nfts(
        self,
        address: str,
        *,
        limit: int = 100,
        offset: int = 0,
        collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if collection:
            params["collection"] = collection
        return await self.async_.get(f"accounts/{address}/nfts", params=params)

    def get_nfts_sync(
        self,
        address: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if collection:
            params["collection"] = collection
        return self.sync.get(f"accounts/{address}/nfts", params=params)

    async def get_event(self, event_id: str) -> Dict[str, Any]:
        return await self.async_.get(f"events/{event_id}")

    def get_event_sync(self, event_id: str) -> Dict[str, Any]:
        return self.sync.get(f"events/{event_id}")

    async def get_nft_item(self, address: str) -> Dict[str, Any]:
        return await self.async_.get(f"nfts/{address}")

    def get_nft_item_sync(self, address: str) -> Dict[str, Any]:
        return self.sync.get(f"nfts/{address}")

    async def search_nfts(self, query: str, limit: int = 20) -> Dict[str, Any]:
        # Note: TONAPI search endpoints evolve; this is a best-effort path
        return await self.async_.get("nfts/search", params={"q": query, "limit": limit})
