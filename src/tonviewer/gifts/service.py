"""
Telegram Gifts & Collectibles intelligence.

Distinguishes:
- Ordinary Telegram Gifts
- Upgraded / Collectible Gifts (on-chain NFTs)
- Gifts listed on Fragment
- Gifts owned by a wallet
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..nfts.service import NFTClient, NFTItem
from ..providers.tonapi import TonAPIProvider
from ..exceptions import NFTError, AddressError
from ..utils.address import is_valid_address, normalize_address


class GiftInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    collection: Optional[str] = None
    address: Optional[str] = None
    owner: Optional[str] = None
    image: Optional[str] = None
    is_collectible: bool = False
    is_listed: bool = False
    is_on_chain: bool = True
    attributes: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "tonapi"
    raw: Optional[Dict[str, Any]] = None


class GiftService:
    """
    High-level view of Telegram gifts / collectibles owned by a wallet.

    Note: Pure Telegram (non-NFT) gifts are not fully queryable from public
    blockchain APIs. We surface on-chain collectible gifts and mark them clearly.
    """

    def __init__(self, tonapi: Optional[TonAPIProvider] = None, nft_client: Optional[NFTClient] = None):
        self.tonapi = tonapi
        self.nft = nft_client or NFTClient(tonapi=tonapi)

    async def get_owned_gifts(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
    ) -> List[GiftInfo]:
        """Return gifts / collectibles owned by the wallet that appear as NFTs.

        limit=None (default) fetches all owned gift NFTs.
        """
        if not is_valid_address(address):
            raise AddressError(f"Invalid address: {address}")

        # Prefer the dedicated NFT filter when available
        try:
            items = await self.nft.get_gifts(address, limit=limit)
        except Exception:
            # Fallback for older NFTClient without get_gifts
            items = await self.nft.get_owned(address, limit=limit)
            items = [i for i in items if i.is_telegram_gift or self._looks_like_gift(i)]

        gifts: List[GiftInfo] = []
        for item in items:
            gifts.append(
                GiftInfo(
                    name=item.name,
                    collection=item.collection_name,
                    address=item.address,
                    owner=item.owner or address,
                    image=item.image,
                    is_collectible=True,
                    is_on_chain=True,
                    attributes=[{"trait_type": a.trait_type, "value": a.value} for a in item.attributes],
                    source="tonapi",
                    raw=item.raw,
                )
            )
        return gifts

    def _looks_like_gift(self, item: NFTItem) -> bool:
        text = f"{item.name or ''} {item.collection_name or ''}".lower()
        keywords = ("gift", "telegram", "collectible", "star", "unique gift", "limited")
        return any(k in text for k in keywords)
