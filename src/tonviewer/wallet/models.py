"""
Wallet-related data models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..core.models import AccountState, AddressInfo, PriceInfo, ProviderMetadata


class WalletBalance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nanotons: int = 0
    ton: float = 0.0
    usd: Optional[float] = None
    price: Optional[PriceInfo] = None


class WalletInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: str
    address_info: Optional[AddressInfo] = None
    balance: WalletBalance = Field(default_factory=WalletBalance)
    status: AccountState = AccountState.UNKNOWN
    is_wallet: Optional[bool] = None
    last_activity: Optional[datetime] = None
    name: Optional[str] = None
    icon: Optional[str] = None
    nfts_count: Optional[int] = None
    interfaces: List[str] = Field(default_factory=list)
    contract_type: Optional[str] = None
    wallet_version: Optional[str] = None
    explorer_url: Optional[str] = None
    provider: Optional[ProviderMetadata] = None
    raw: Optional[Dict[str, Any]] = None

    def to_legacy_json(self) -> Dict[str, Any]:
        """Format compatible with old Wallet.info() output."""
        bal = self.balance
        usd_part = f" ≈ {bal.usd:,.3f} $" if bal.usd is not None else ""
        return {
            "Balance": f"{bal.ton:,.3f} TON{usd_part}",
            "Status": self.status.value if isinstance(self.status, AccountState) else str(self.status),
            "Is_wallet": self.is_wallet,
            "Last_activity": self.last_activity.strftime("%Y-%m-%d %I:%M:%S %p") if self.last_activity else None,
            "Name": self.name or "",
            "Icon": self.icon,
            "NFTs": self.nfts_count,
            "Address": self.address,
        }
