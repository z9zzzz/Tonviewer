"""
NFT service — ownership, metadata, collections via TONAPI.

Categories:
  - usernames  → Telegram Usernames NFTs
  - gifts      → Telegram Gifts / Collectibles (Whip Cupcake, Chill Flame, …)
  - others     → everything else (domains, numbers, regular NFTs, …)
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from ..providers.tonapi import TonAPIProvider
from ..exceptions import NFTError, AddressError
from ..utils.address import is_valid_address, normalize_address


# TONAPI allows up to 1000 items per request
_PAGE_SIZE = 1000

NFTCategory = Literal["username", "gift", "other"]

# Pattern: "Name #12345" or "Name #05493 · extra" — typical Telegram collectible gift
_GIFT_SERIAL_RE = re.compile(r"#\s*\d+", re.IGNORECASE)

# Collections / names that are clearly NOT gifts
_NOT_GIFT_MARKERS = (
    "telegram username",
    "telegram usernames",
    "username",
    "getgems domain",
    "domains",
    "anonymous telegram number",
    "telegram number",
    "chainsim",
    ".ton",
    "dns",
)

# Strong gift indicators (name or collection)
_GIFT_KEYWORDS = (
    "gift",
    "gifts",
    "collectible",
    "collectibles",
    "durov",
    "plush pepe",
    "star notepad",
    "hanging star",
    "zargates",
    "telegram gift",
)


class NFTAttribute(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trait_type: Optional[str] = None
    value: Optional[str] = None


class NFTItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: str
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    collection_address: Optional[str] = None
    collection_name: Optional[str] = None
    owner: Optional[str] = None
    attributes: List[NFTAttribute] = Field(default_factory=list)
    is_telegram_gift: bool = False
    category: NFTCategory = "other"
    # Optional floor price if available later (TON)
    floor_price_ton: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None


class NFTOwnedResult(BaseModel):
    """
    Structured result from get_categorized().

    Supports:
        result.search("chill flame")
        result.filter_by(lambda n: ...)
        result.has("@monk")
        result.value_summary()
    """

    model_config = ConfigDict(extra="ignore")

    all: List[NFTItem] = Field(default_factory=list)
    usernames: List[NFTItem] = Field(default_factory=list)
    gifts: List[NFTItem] = Field(default_factory=list)
    others: List[NFTItem] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.all)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def search(self, query: str) -> List[NFTItem]:
        """Case-insensitive search in name + collection_name."""
        q = (query or "").strip().lower()
        if not q:
            return list(self.all)
        hits = []
        for item in self.all:
            hay = f"{item.name or ''} {item.collection_name or ''}".lower()
            if q in hay:
                hits.append(item)
        return hits

    def filter_by(self, predicate: Callable[[NFTItem], bool]) -> List[NFTItem]:
        """Return items matching a custom predicate."""
        return [item for item in self.all if predicate(item)]

    def has(self, query: str) -> bool:
        """True if any item matches the search query (name/collection)."""
        return len(self.search(query)) > 0

    def value_summary(self) -> Dict[str, float]:
        """
        Estimated portfolio value in TON using floor_price_ton when present.

        Returns:
            {
                "usernames": float,
                "gifts": float,
                "others": float,
                "total": float,
            }
        Note: floor prices are not fetched by default (most items will be 0).
        """
        def _sum(items: List[NFTItem]) -> float:
            total = 0.0
            for i in items:
                if i.floor_price_ton is not None:
                    total += float(i.floor_price_ton)
            return total

        users = _sum(self.usernames)
        gifts = _sum(self.gifts)
        etc = _sum(self.others)
        return {
            "usernames": users,
            "gifts": gifts,
            "others": etc,
            "total": users + gifts + etc,
        }

    def by_category(self, category: NFTCategory) -> List[NFTItem]:
        if category == "username":
            return list(self.usernames)
        if category == "gift":
            return list(self.gifts)
        return list(self.others)


class NFTClient:
    """
    NFT client (works both as modern service and backward-compatible name).

    Main methods:
        get_owned(address)          → List[NFTItem]   (default: ALL items)
        get_usernames(address)      → List[NFTItem]
        get_gifts(address)          → List[NFTItem]
        get_others(address)         → List[NFTItem]
        get_categorized(address)    → NFTOwnedResult  (all + usernames/gifts/others)
    """

    def __init__(self, tonapi: Optional[TonAPIProvider] = None):
        self.tonapi = tonapi

    def _ensure(self) -> TonAPIProvider:
        if not self.tonapi:
            raise NFTError("TONAPI provider is not configured")
        return self.tonapi

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify(self, coll_name: str, name: Optional[str]) -> NFTCategory:
        """
        Decide whether an NFT is a Telegram username, a gift/collectible, or other.

        Rules (in order):
        1. Usernames → collection/name contains "username" (and not gift)
        2. Explicit gift keywords
        3. Classic Telegram collectible pattern: "Something #12345"
           AND not a domain / number / username collection
        4. Otherwise → other
        """
        coll = (coll_name or "").strip()
        nm = (name or "").strip()
        text = f"{coll} {nm}".lower()

        # --- 1. Usernames ---
        if "telegram username" in text or "telegram usernames" in text:
            return "username"
        if "username" in text and "gift" not in text and "collectible" not in text:
            return "username"
        # Name looks like a handle
        if nm.startswith("@") and "username" in (coll.lower() or "username"):
            return "username"

        # --- 2. Explicit gift keywords ---
        if any(k in text for k in _GIFT_KEYWORDS):
            return "gift"

        # --- 3. Numbered collectible pattern (Whip Cupcake #150, Chill Flame #117665, …) ---
        is_not_gift_collection = any(m in text for m in _NOT_GIFT_MARKERS)
        has_serial = bool(_GIFT_SERIAL_RE.search(nm)) or bool(_GIFT_SERIAL_RE.search(coll))

        if has_serial and not is_not_gift_collection:
            # Most Telegram gift collections use "Name #Serial"
            return "gift"

        # Extra: collection name ends with common gift-style plurals and has serial-like items
        # (already covered by serial check above in practice)

        return "other"

    def _parse_item(self, raw: Dict[str, Any]) -> NFTItem:
        meta = raw.get("metadata") or {}
        collection = raw.get("collection") or {}
        owner_obj = raw.get("owner") or {}
        owner = owner_obj.get("address") if isinstance(owner_obj, dict) else owner_obj
        attrs = []
        for a in meta.get("attributes") or []:
            attrs.append(
                NFTAttribute(trait_type=a.get("trait_type"), value=str(a.get("value")))
            )

        name = meta.get("name") or raw.get("name")
        image = meta.get("image")
        if not image and raw.get("previews"):
            try:
                image = raw["previews"][0].get("url")
            except Exception:
                pass

        coll_name = (collection.get("name") or "")
        category = self._classify(coll_name, name)
        is_gift = category == "gift"

        return NFTItem(
            address=raw.get("address") or "",
            name=name,
            description=meta.get("description"),
            image=image,
            collection_address=collection.get("address"),
            collection_name=coll_name or None,
            owner=owner,
            attributes=attrs,
            is_telegram_gift=is_gift,
            category=category,
            floor_price_ton=None,
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Core fetch (with automatic pagination when limit is None)
    # ------------------------------------------------------------------

    async def _fetch_page(
        self,
        addr: str,
        *,
        limit: int,
        offset: int,
        collection: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        provider = self._ensure()
        data = await provider.get_nfts(
            addr, limit=limit, offset=offset, collection=collection
        )
        return data.get("nft_items") or data.get("items") or []

    async def get_owned(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        collection: Optional[str] = None,
    ) -> List[NFTItem]:
        """
        Return NFTs owned by the address.

        Parameters
        ----------
        limit :
            - None (default) → fetch **all** NFTs (paginated internally).
            - int            → fetch at most that many items (starting from offset).
        offset :
            Starting index (only meaningful when limit is an int).
        collection :
            Optional collection address filter.
        """
        if not is_valid_address(address):
            raise AddressError(f"Invalid address: {address}")
        addr = normalize_address(address)

        try:
            if limit == 0:
                return []
            if limit is not None:
                raw_items = await self._fetch_page(
                    addr, limit=limit, offset=offset, collection=collection
                )
                return [self._parse_item(i) for i in raw_items]

            # Default: pull everything page by page
            all_items: List[NFTItem] = []
            seen = set()
            current_offset = 0
            while True:
                page = await self._fetch_page(
                    addr,
                    limit=_PAGE_SIZE,
                    offset=current_offset,
                    collection=collection,
                )
                if not page:
                    break
                for raw in page:
                    item = self._parse_item(raw)
                    key = item.address or None
                    if key is None or key not in seen:
                        all_items.append(item)
                        if key is not None:
                            seen.add(key)
                if len(page) < _PAGE_SIZE:
                    break
                current_offset += _PAGE_SIZE

            return all_items

        except AddressError:
            raise
        except Exception as exc:
            raise NFTError(f"Failed to fetch NFTs for {addr}") from exc

    # ------------------------------------------------------------------
    # Category helpers
    # ------------------------------------------------------------------

    async def _get_filtered_category(
        self,
        address: str,
        *,
        category: NFTCategory,
        limit: Optional[int],
        offset: int,
    ) -> List[NFTItem]:
        """Filter a bounded page at a time, then apply category offset and limit."""
        if not is_valid_address(address):
            raise AddressError(f"Invalid address: {address}")
        if limit == 0:
            return []
        if offset < 0 or (limit is not None and limit < 0):
            raise ValueError("limit and offset must be non-negative")
        addr = normalize_address(address)
        matches: List[NFTItem] = []
        seen = set()
        current_offset = 0
        skipped = 0
        try:
            while limit is None or len(matches) < limit:
                page = await self._fetch_page(addr, limit=_PAGE_SIZE, offset=current_offset)
                if not page:
                    break
                for raw in page:
                    item = self._parse_item(raw)
                    if item.category != category or (item.address and item.address in seen):
                        continue
                    if item.address:
                        seen.add(item.address)
                    if skipped < offset:
                        skipped += 1
                        continue
                    matches.append(item)
                    if limit is not None and len(matches) >= limit:
                        break
                if len(page) < _PAGE_SIZE:
                    break
                current_offset += _PAGE_SIZE
            return matches
        except (AddressError, ValueError):
            raise
        except Exception as exc:
            raise NFTError(f"Failed to fetch {category} NFTs for {addr}") from exc

    async def get_usernames(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[NFTItem]:
        """Return matching username NFTs; offset and limit apply after category filtering."""
        return await self._get_filtered_category(address, category="username", limit=limit, offset=offset)

    async def get_gifts(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[NFTItem]:
        """Return matching gift NFTs; offset and limit apply after category filtering."""
        return await self._get_filtered_category(address, category="gift", limit=limit, offset=offset)

    async def get_others(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[NFTItem]:
        """Return other NFTs; offset and limit apply after category filtering."""
        return await self._get_filtered_category(address, category="other", limit=limit, offset=offset)

    async def get_categorized(
        self,
        address: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> NFTOwnedResult:
        """
        Fetch once and return a structured result with
        .all / .usernames / .gifts / .others

        Also supports:
            result.search("chill flame")
            result.filter_by(lambda n: ...)
            result.has("@monk")
            result.value_summary()
        """
        items = await self.get_owned(address, limit=limit, offset=offset)
        return NFTOwnedResult(
            all=items,
            usernames=[i for i in items if i.category == "username"],
            gifts=[i for i in items if i.category == "gift"],
            others=[i for i in items if i.category == "other"],
        )

    # ------------------------------------------------------------------
    # Single item + raw helper
    # ------------------------------------------------------------------

    async def get_item(self, nft_address: str) -> NFTItem:
        if not is_valid_address(nft_address):
            raise AddressError(f"Invalid NFT address: {nft_address}")
        provider = self._ensure()
        try:
            raw = await provider.get_nft_item(normalize_address(nft_address))
            return self._parse_item(raw)
        except Exception as exc:
            raise NFTError("Failed to fetch NFT item") from exc

    async def get_owned_raw(self, address: str, **kwargs) -> Dict[str, Any]:
        items = await self.get_owned(address, **kwargs)
        return {
            "count": len(items),
            "items": [i.model_dump(exclude={"raw"}) for i in items],
        }
