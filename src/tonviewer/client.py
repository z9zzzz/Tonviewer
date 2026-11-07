"""
Main asynchronous client.
"""

from __future__ import annotations

from typing import Any, Optional

from .config import TonviewerConfig
from .providers.tonapi import TonAPIProvider
from .providers.toncenter_v2 import TonCenterV2Provider
from .providers.toncenter_v3 import TonCenterV3Provider
from .wallet.service import WalletService
from .prices.service import PriceService
from .fragment.client import FragmentClient
from .nfts.service import NFTClient
from .jettons.service import JettonService
from .gifts.service import GiftService


class TonviewerClient:
    """
    Primary async entry point for the Tonviewer SDK.

    Example:
        async with TonviewerClient(api_key="YOUR_KEY") as client:
            info = await client.wallet.get_info("UQ...")
            jettons = await client.jettons.get_balances("UQ...")
            nfts = await client.nfts.get_owned("UQ...")
            gifts = await client.gifts.get_owned_gifts("UQ...")
            user = await client.fragment.get_username("durov")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        config: Optional[TonviewerConfig] = None,
        network: str = "mainnet",
        tonapi_key: Optional[str] = None,
        **kwargs: Any,
    ):
        if config is None:
            config = TonviewerConfig(
                api_key=api_key,
                tonapi_key=tonapi_key,
                network=network,  # type: ignore
                **kwargs,
            )
        self.config = config

        # Providers
        self._tonapi = TonAPIProvider(config.tonapi, config.user_agent) if config.use_tonapi else None
        self._v2 = TonCenterV2Provider(config.toncenter_v2, config.user_agent) if config.use_toncenter_v2 else None
        self._v3 = TonCenterV3Provider(config.toncenter_v3, config.user_agent) if config.use_toncenter_v3 else None

        # Services
        self.prices = PriceService(config)
        self._price_cache: Optional[float] = None

        self.wallet = WalletService(
            config,
            tonapi=self._tonapi,
            v2=self._v2,
            v3=self._v3,
            price_ton_usd=None,
        )
        self.fragment = FragmentClient(proxy=config.proxy, tonapi=self._tonapi)
        self.nfts = NFTClient(tonapi=self._tonapi)
        self.jettons = JettonService(tonapi=self._tonapi)
        self.gifts = GiftService(tonapi=self._tonapi, nft_client=self.nfts)

    async def __aenter__(self) -> "TonviewerClient":
        try:
            self._price_cache = await self.prices.get_ton_usd_async()
            self.wallet._price = self._price_cache
        except Exception:
            pass
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._tonapi:
            await self._tonapi.aclose()
        if self._v2:
            await self._v2.aclose()
        if self._v3:
            await self._v3.aclose()
        await self.fragment.aclose()
        await self.prices.aclose()

    async def get_wallet_info(self, address: str):
        if self.wallet._price is None:
            try:
                self.wallet._price = await self.prices.get_ton_usd_async()
            except Exception:
                pass
        return await self.wallet.get_info(address)
