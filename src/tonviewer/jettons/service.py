"""
Jetton (token) service.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..providers.tonapi import TonAPIProvider
from ..exceptions import JettonError, AddressError
from ..utils.address import is_valid_address, normalize_address


class JettonBalance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    balance: str = "0"
    balance_human: Optional[float] = None
    decimals: int = 9
    image: Optional[str] = None
    verification: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class JettonService:
    def __init__(self, tonapi: Optional[TonAPIProvider] = None):
        self.tonapi = tonapi

    def _ensure(self) -> TonAPIProvider:
        if not self.tonapi:
            raise JettonError("TONAPI provider is not configured")
        return self.tonapi

    async def get_balances(self, address: str) -> List[JettonBalance]:
        if not is_valid_address(address):
            raise AddressError(f"Invalid address: {address}")
        addr = normalize_address(address)
        provider = self._ensure()
        try:
            data = await provider.get_jettons(addr)
        except Exception as exc:
            raise JettonError(f"Failed to fetch jettons for {addr}") from exc

        balances: List[JettonBalance] = []
        items = data.get("balances") or data.get("jettons") or []
        for item in items:
            jetton = item.get("jetton") or {}
            raw_balance = item.get("balance", "0")
            raw_decimals = jetton.get("decimals")
            decimals = 9 if raw_decimals is None else int(raw_decimals)
            try:
                human = int(raw_balance) / (10 ** decimals)
            except Exception:
                human = None
            balances.append(
                JettonBalance(
                    address=jetton.get("address") or "",
                    symbol=jetton.get("symbol"),
                    name=jetton.get("name"),
                    balance=str(raw_balance),
                    balance_human=human,
                    decimals=decimals,
                    image=jetton.get("image"),
                    verification=jetton.get("verification"),
                    raw=item,
                )
            )
        return balances

    def get_balances_sync(self, address: str) -> List[JettonBalance]:
        # thin sync wrapper using the provider's sync path is limited;
        # for simplicity we raise and recommend async for jettons in this version
        raise JettonError("Use async get_balances() for jetton portfolio")
