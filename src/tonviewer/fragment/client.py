"""
Fragment.com username resolution via public HTML pages.
No official API — careful parsing with clear error types.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional

import httpx
from bs4 import BeautifulSoup

from ..exceptions import (
    FragmentBlockedError,
    FragmentFetchError,
    FragmentParseError,
    UserNotFoundError,
    FragmentError,
)
from ..utils.address import safe_normalize
from .models import FragmentResult, UsernameStatus


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://fragment.com/",
}


class FragmentClient:
    BASE = "https://fragment.com"

    def __init__(
        self,
        timeout: float = 25.0,
        proxy: Optional[str] = None,
        tonapi: Any = None,
    ):
        self.timeout = timeout
        self.proxy = proxy
        self.tonapi = tonapi
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=_HEADERS,
                follow_redirects=True,
                proxy=self.proxy,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_username(self, username: str) -> FragmentResult:
        username = username.lstrip("@").lower().strip()
        if not username or not re.match(r"^[a-z0-9_]{4,32}$", username):
            raise FragmentError(f"Invalid username format: {username}")

        url = f"{self.BASE}/username/{username}"
        client = await self._get_client()

        try:
            resp = await client.get(url)
        except httpx.RequestError as exc:
            raise FragmentFetchError(f"Network error fetching @{username}: {exc}") from exc

        if resp.status_code == 403:
            raise FragmentBlockedError(
                "Fragment blocked the request (HTTP 403)",
                details={"url": url, "status": 403},
            )
        if resp.status_code == 404:
            raise UserNotFoundError(username)
        if resp.status_code >= 400:
            raise FragmentFetchError(
                f"HTTP {resp.status_code} for @{username}",
                details={"status": resp.status_code},
            )

        html = resp.text
        if "Just a moment" in html or "cf-browser-verification" in html:
            raise FragmentBlockedError("Cloudflare challenge page detected")

        try:
            result = self._parse(username, html)
            if result.owner_wallet and self.tonapi:
                await self._enrich_owner(result)
            return result
        except Exception as exc:
            if isinstance(exc, FragmentError):
                raise
            raise FragmentParseError(
                f"Failed to parse Fragment page for @{username}: {exc}"
            ) from exc

    def _parse(self, username: str, html: str) -> FragmentResult:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        status = UsernameStatus.UNKNOWN
        if "available" in text and "buy" in text:
            status = UsernameStatus.AVAILABLE
        elif "on auction" in text or "auction" in text:
            status = UsernameStatus.ON_AUCTION
        elif "for sale" in text or "on sale" in text:
            status = UsernameStatus.ON_SALE
        elif "sold" in text:
            status = UsernameStatus.SOLD
        elif "taken" in text:
            status = UsernameStatus.TAKEN

        # Header status span
        status_tag = soup.find("span", class_=re.compile(r"tm-section-header-status", re.I))
        if status_tag:
            st = status_tag.get_text(strip=True).lower()
            if "sold" in st:
                status = UsernameStatus.SOLD
            elif "available" in st:
                status = UsernameStatus.AVAILABLE
            elif "auction" in st:
                status = UsernameStatus.ON_AUCTION
            elif "taken" in st:
                status = UsernameStatus.TAKEN

        # Wallet links — Fragment currently uses gram.org/address/EQ... and also
        # shows raw UQ/EQ addresses in offer tables.
        owner_wallet = None
        owner_display = None
        addr_re = re.compile(
            r"([EUeu][Qq][A-Za-z0-9_-]{46}|EQ[A-Za-z0-9_-]{46}|UQ[A-Za-z0-9_-]{46})"
        )

        # 1) Prefer explicit address links (gram.org, tonviewer, tonscan, ton.org)
        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            if any(x in href for x in (
                "gram.org/address/", "tonviewer.com/", "tonscan.org/",
                "ton.org/", "tonapi.io/", "getgems.io/"
            )):
                m = addr_re.search(href)
                if m:
                    candidate = m.group(1)
                    owner_wallet = safe_normalize(candidate) or candidate
                    owner_display = a.get_text(strip=True) or owner_wallet
                    break

        # 2) Fallback: first plausible address appearing in the page text
        if not owner_wallet:
            for m in addr_re.finditer(html):
                candidate = m.group(1)
                # skip very short / obvious non-owner noise if needed
                norm = safe_normalize(candidate)
                if norm:
                    owner_wallet = norm
                    owner_display = candidate
                    break

        # Price
        price = None
        price_ton = None
        for cls in ("tm-section-header-domain-price", "tm-value", "table-cell-value"):
            tag = soup.find(class_=re.compile(cls, re.I))
            if tag:
                price = tag.get_text(" ", strip=True)
                m = re.search(r"([\d.,]+)\s*TON", price, re.I)
                if m:
                    try:
                        price_ton = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
                break

        # Auction end
        auction_ends = None
        timer = soup.find(attrs={"data-deadline": True})
        if timer:
            try:
                ts = int(timer["data-deadline"])
                auction_ends = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                pass

        purchased = None
        for info in soup.find_all(class_=re.compile(r"tm-bid-info-text", re.I)):
            if "purchased" not in info.get_text(" ", strip=True).lower():
                continue
            time_tag = info.find("time")
            if not time_tag:
                continue
            try:
                raw_dt = time_tag.get("datetime")
                if raw_dt:
                    purchased_dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                    if purchased_dt.tzinfo is None:
                        purchased_dt = purchased_dt.replace(tzinfo=timezone.utc)
                    purchased_dt = purchased_dt.astimezone()
                    purchased = f"{purchased_dt.day} {purchased_dt.strftime('%b %Y at %H:%M')}"
                else:
                    purchased = time_tag.get_text(" ", strip=True)
            except Exception:
                purchased = time_tag.get_text(" ", strip=True)
            break

        # Fragment explicitly labels these pages as Telegram collectible
        # usernames. Do not infer collectibility from the sale status alone.
        is_collectible = bool(re.search(r"collectible\s+username", text, re.I))

        return FragmentResult(
            username=username,
            status=status,
            owner_wallet=owner_wallet,
            owner_display=owner_display,
            price=price,
            price_ton=price_ton,
            auction_ends=auction_ends,
            purchased=purchased,
            is_collectible=is_collectible,
            fetched_at=datetime.utcnow(),
        )

    async def _enrich_owner(self, result: FragmentResult) -> None:
        """Add owner balance/NFT count; enrichment never breaks Fragment lookup."""
        try:
            account = await self.tonapi.get_account(result.owner_wallet)
            balance_nano = int(account.get("balance", 0) or 0)
            result.nfts = (account.get("stats") or {}).get("nfts_count")
            balance_gram = Decimal(balance_nano) / Decimal(1_000_000_000)

            # Match the compact Fragment-style display while retaining useful
            # USD precision. Truncation avoids displaying a balance above the
            # actual on-chain amount.
            gram_text = balance_gram.quantize(Decimal("0.001"), rounding=ROUND_DOWN)
        except Exception:
            return

        try:
            rates = await self.tonapi.get_rates()
            usd_rate = (((rates.get("rates") or {}).get("TON") or {}).get("prices") or {}).get("USD")
            usd = (balance_gram * Decimal(str(usd_rate))) if usd_rate is not None else None
            result.balance = (
                f"{gram_text:.3f} GRAM ≈ ${usd:.4f}"
                if usd is not None
                else f"{gram_text:.3f} GRAM"
            )
        except Exception:
            result.balance = f"{gram_text:.3f} GRAM"
