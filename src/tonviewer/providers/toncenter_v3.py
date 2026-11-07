"""TON Center API v3 provider for indexed, raw blockchain data."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseProvider


class TonCenterV3Provider(BaseProvider):
    """Indexed transaction/action access.

    v3 is the canonical source for raw transaction history.  It uses
    offset-based pagination and supports up to 1000 rows per request.
    """

    name = "toncenter_v3"

    async def get_account(self, address: str) -> Dict[str, Any]:
        """Fetch the indexed account state when callers use the base contract."""
        return await self.async_.get("accountStates", params={"address": address})

    def get_account_sync(self, address: str) -> Dict[str, Any]:
        return self.sync.get("accountStates", params={"address": address})

    async def get_transactions(
        self,
        address: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "desc",
        hash_: Optional[str] = None,
        lt: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "account": address,
            "limit": max(1, min(int(limit), 1000)),
            "offset": max(0, int(offset)),
            "sort": sort if sort in {"asc", "desc"} else "desc",
        }
        if hash_:
            params["hash"] = hash_
        if lt is not None:
            params["lt"] = lt
        return await self.async_.get("transactions", params=params)

    def get_transactions_sync(
        self,
        address: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "desc",
        hash_: Optional[str] = None,
        lt: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "account": address,
            "limit": max(1, min(int(limit), 1000)),
            "offset": max(0, int(offset)),
            "sort": sort if sort in {"asc", "desc"} else "desc",
        }
        if hash_:
            params["hash"] = hash_
        if lt is not None:
            params["lt"] = lt
        return self.sync.get("transactions", params=params)

    async def get_actions(
        self,
        address: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "desc",
        include_accounts: bool = True,
        include_transactions: bool = True,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "account": address,
            "limit": max(1, min(int(limit), 1000)),
            "offset": max(0, int(offset)),
            "sort": sort if sort in {"asc", "desc"} else "desc",
            "include_accounts": include_accounts,
            "include_transactions": include_transactions,
        }
        return await self.async_.get("actions", params=params)
