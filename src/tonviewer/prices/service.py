"""TON/USD lookup with reusable sync/async HTTP clients and optional TTL caching."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, Optional

from ..config import ProviderConfig, TonviewerConfig
from ..core.http import AsyncHTTP, SyncHTTP
from ..core.models import PriceInfo
from ..exceptions import NetworkError


class PriceService:
    """Fetch TON/USD from TONAPI, falling back to CoinGecko."""

    def __init__(self, config: Optional[TonviewerConfig] = None):
        self.config = config or TonviewerConfig()
        self._last_source: Optional[str] = None
        self._cached_price: Optional[float] = None
        self._cache_expires = 0.0
        self._sync_clients: Dict[str, SyncHTTP] = {}
        self._async_clients: Dict[str, AsyncHTTP] = {}

    def _provider_config(self, name: str, base_url: str) -> ProviderConfig:
        source = self.config.tonapi
        return ProviderConfig(
            base_url=base_url,
            timeout=source.timeout,
            max_retries=source.max_retries,
            enabled=True,
            proxy=source.proxy,
            retry_backoff=source.retry_backoff,
            rate_limit_rps=source.rate_limit_rps,
            enable_cache=source.enable_cache,
            cache_ttl=source.cache_ttl,
        )

    def _sync_client(self, base_url: str) -> SyncHTTP:
        if base_url not in self._sync_clients:
            self._sync_clients[base_url] = SyncHTTP(self._provider_config("price", base_url))
        return self._sync_clients[base_url]

    def _async_client(self, base_url: str) -> AsyncHTTP:
        if base_url not in self._async_clients:
            self._async_clients[base_url] = AsyncHTTP(self._provider_config("price", base_url))
        return self._async_clients[base_url]

    def _read_cache(self) -> Optional[float]:
        if not self.config.enable_cache or self.config.cache_ttl <= 0:
            return None
        if self._cached_price is not None and time.monotonic() < self._cache_expires:
            return self._cached_price
        return None

    def _write_cache(self, price: float, source: str) -> float:
        self._last_source = source
        self._cached_price = price
        self._cache_expires = time.monotonic() + max(0.0, self.config.cache_ttl)
        return price

    def get_ton_usd(self) -> float:
        cached = self._read_cache()
        if cached is not None:
            return cached
        try:
            data = self._sync_client("https://tonapi.io/v2").get(
                "rates", params={"tokens": "ton", "currencies": "usd"}, timeout=10
            )
            return self._write_cache(float(data["rates"]["TON"]["prices"]["USD"]), "tonapi")
        except Exception as primary_error:
            try:
                data = self._sync_client("https://api.coingecko.com").get(
                    "api/v3/simple/price",
                    params={"ids": "the-open-network", "vs_currencies": "usd"}, timeout=8
                )
                return self._write_cache(float(data["the-open-network"]["usd"]), "coingecko")
            except Exception as fallback_error:
                raise NetworkError(f"Failed to fetch TON price: {fallback_error}") from primary_error

    async def get_ton_usd_async(self) -> float:
        cached = self._read_cache()
        if cached is not None:
            return cached
        try:
            data = await self._async_client("https://tonapi.io/v2").get(
                "rates", params={"tokens": "ton", "currencies": "usd"}, timeout=10
            )
            return self._write_cache(float(data["rates"]["TON"]["prices"]["USD"]), "tonapi")
        except Exception as primary_error:
            try:
                data = await self._async_client("https://api.coingecko.com").get(
                    "api/v3/simple/price",
                    params={"ids": "the-open-network", "vs_currencies": "usd"}, timeout=8
                )
                return self._write_cache(float(data["the-open-network"]["usd"]), "coingecko")
            except Exception as fallback_error:
                raise NetworkError(f"Failed to fetch TON price: {fallback_error}") from primary_error

    def get_price_info(self) -> PriceInfo:
        price = self.get_ton_usd()
        return PriceInfo(ton_usd=price, source=self._last_source, timestamp=datetime.now(timezone.utc))

    def close(self) -> None:
        for client in self._sync_clients.values():
            client.close()
        self._sync_clients.clear()

    async def aclose(self) -> None:
        self.close()
        for client in self._async_clients.values():
            await client.aclose()
        self._async_clients.clear()
