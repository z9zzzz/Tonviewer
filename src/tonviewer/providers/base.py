"""
Base provider interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..config import ProviderConfig
from ..core.http import AsyncHTTP, SyncHTTP
from ..wallet.models import WalletInfo


class BaseProvider(ABC):
    name: str = "base"

    def __init__(self, config: ProviderConfig, user_agent: str = "Tonviewer/2.2.5"):
        self.config = config
        self.user_agent = user_agent
        self._sync: Optional[SyncHTTP] = None
        self._async: Optional[AsyncHTTP] = None

    @property
    def sync(self) -> SyncHTTP:
        if self._sync is None:
            self._sync = SyncHTTP(self.config, self.user_agent)
            self._sync.provider_name = self.name
        return self._sync

    @property
    def async_(self) -> AsyncHTTP:
        if self._async is None:
            self._async = AsyncHTTP(self.config, self.user_agent)
            self._async.provider_name = self.name
        return self._async

    def close(self) -> None:
        if self._sync:
            self._sync.close()
            self._sync = None

    async def aclose(self) -> None:
        if self._async:
            await self._async.aclose()
            self._async = None

    @abstractmethod
    async def get_account(self, address: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_account_sync(self, address: str) -> Dict[str, Any]:
        ...
