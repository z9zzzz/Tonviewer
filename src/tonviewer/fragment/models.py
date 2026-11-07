"""
Fragment models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UsernameStatus(str, Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    TAKEN = "taken"
    ON_AUCTION = "on_auction"
    ON_SALE = "on_sale"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class FragmentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str
    status: UsernameStatus = UsernameStatus.UNKNOWN
    owner_wallet: Optional[str] = None
    owner_display: Optional[str] = None
    price: Optional[str] = None
    price_ton: Optional[float] = None
    min_bid: Optional[str] = None
    auction_ends: Optional[str] = None
    bids: Optional[int] = None
    is_collectible: bool = False
    nfts: Optional[int] = None
    purchased: Optional[str] = None
    balance: Optional[str] = None
    raw_html_snippet: Optional[str] = None
    source: str = "fragment.com"
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump(exclude_none=True)
        for key, display_key in (
            ("nfts", "NFTs"),
            ("purchased", "Purchased"),
            ("balance", "Balance"),
        ):
            if key in data:
                data[display_key] = data.pop(key)
        def remove_empty(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: cleaned for k, raw in value.items() if (cleaned := remove_empty(raw)) not in (None, "", [], {})}
            if isinstance(value, list):
                return [cleaned for raw in value if (cleaned := remove_empty(raw)) not in (None, "", [], {})]
            if isinstance(value, str):
                return " ".join(value.split())
            return value
        return remove_empty(data)
