"""
TON Center API v2 provider — direct blockchain access.
Docs: https://docs.ton.org/api/v2/overview
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseProvider


class TonCenterV2Provider(BaseProvider):
    name = "toncenter_v2"

    async def get_account(self, address: str) -> Dict[str, Any]:
        return await self.async_.get("getAddressInformation", params={"address": address})

    def get_account_sync(self, address: str) -> Dict[str, Any]:
        return self.sync.get("getAddressInformation", params={"address": address})

    async def get_balance(self, address: str) -> int:
        data = await self.async_.get("getAddressBalance", params={"address": address})
        # returns string of nanotons
        return int(data) if not isinstance(data, dict) else int(data.get("balance", 0))

    def get_balance_sync(self, address: str) -> int:
        data = self.sync.get("getAddressBalance", params={"address": address})
        return int(data) if not isinstance(data, dict) else int(data.get("balance", 0))

    async def get_transactions(
        self,
        address: str,
        *,
        limit: int = 10,
        lt: Optional[str] = None,
        hash_: Optional[str] = None,
        to_lt: Optional[str] = None,
        archival: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "address": address,
            "limit": limit,
            "archival": archival,
        }
        if lt is not None:
            params["lt"] = lt
        if hash_ is not None:
            params["hash"] = hash_
        if to_lt is not None:
            params["to_lt"] = to_lt
        data = await self.async_.get("getTransactions", params=params)
        return data if isinstance(data, list) else []

    def get_transactions_sync(
        self,
        address: str,
        *,
        limit: int = 10,
        lt: Optional[str] = None,
        hash_: Optional[str] = None,
        to_lt: Optional[str] = None,
        archival: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "address": address,
            "limit": limit,
            "archival": archival,
        }
        if lt is not None:
            params["lt"] = lt
        if hash_ is not None:
            params["hash"] = hash_
        if to_lt is not None:
            params["to_lt"] = to_lt
        data = self.sync.get("getTransactions", params=params)
        return data if isinstance(data, list) else []

    async def run_get_method(
        self,
        address: str,
        method: str,
        stack: Optional[List] = None,
    ) -> Dict[str, Any]:
        payload = {
            "address": address,
            "method": method,
            "stack": stack or [],
        }
        return await self.async_.post("runGetMethod", json=payload)

    async def detect_address(self, address: str) -> Dict[str, Any]:
        return await self.async_.get("detectAddress", params={"address": address})
