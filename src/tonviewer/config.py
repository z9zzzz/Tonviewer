"""
Configuration for Tonviewer.

Priority:
  1. Explicit constructor arguments
  2. Environment variables
  3. Sensible defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Literal

from .exceptions import ConfigurationError


Network = Literal["mainnet", "testnet"]


@dataclass
class ProviderConfig:
    """Configuration for a single API provider."""
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    enabled: bool = True
    proxy: Optional[str] = None
    api_key_backup: Optional[str] = None
    retry_backoff: float = 1.5
    rate_limit_rps: float = 8.0
    enable_cache: bool = True
    cache_ttl: float = 30.0


@dataclass
class TonviewerConfig:
    """
    Central configuration object.

    Example:
        cfg = TonviewerConfig(
            api_key="YOUR_TONCENTER_KEY",
            network="mainnet",
        )
        client = TonviewerClient(config=cfg)
    """

    # Primary key (TON Center preferred)
    api_key: Optional[str] = None
    api_key_backup: Optional[str] = None

    # Optional TONAPI key (tonapi.io)
    tonapi_key: Optional[str] = None

    network: Network = "mainnet"

    # Timeouts & retries
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.5

    # Rate limiting (requests per second soft limit)
    rate_limit_rps: float = 8.0

    # Caching
    cache_ttl: float = 30.0
    enable_cache: bool = True

    # Provider toggles
    use_toncenter_v2: bool = True
    use_toncenter_v3: bool = True
    use_tonapi: bool = True
    use_streaming: bool = False

    # HTTP
    user_agent: str = "Tonviewer/2.2.5 (+https://github.com/z9zzzz/Tonviewer)"
    proxy: Optional[str] = None

    # Derived provider configs (filled in __post_init__)
    toncenter_v2: ProviderConfig = field(init=False)
    toncenter_v3: ProviderConfig = field(init=False)
    tonapi: ProviderConfig = field(init=False)
    streaming: ProviderConfig = field(init=False)

    def __post_init__(self) -> None:
        # Resolve keys from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("TONCENTER_API_KEY") or os.getenv("TON_API_KEY")
        if self.api_key_backup is None:
            self.api_key_backup = os.getenv("TONCENTER_API_KEY_BACKUP")
        if self.tonapi_key is None:
            self.tonapi_key = os.getenv("TONAPI_KEY") or os.getenv("TONAPI_API_KEY")

        net = self.network.lower()
        if net not in ("mainnet", "testnet"):
            raise ConfigurationError(f"Invalid network: {self.network}")
        if self.use_streaming:
            raise ConfigurationError(
                "Streaming is not implemented by this SDK. TONAPI marks its Streaming API deprecated; use a separately configured Webhooks integration."
            )

        if net == "mainnet":
            v2_base = "https://toncenter.com/api/v2"
            v3_base = "https://toncenter.com/api/v3"
            stream_base = "https://toncenter.com/api/streaming/v2"
            tonapi_base = "https://tonapi.io/v2"
        else:
            v2_base = "https://testnet.toncenter.com/api/v2"
            v3_base = "https://testnet.toncenter.com/api/v3"
            stream_base = "https://testnet.toncenter.com/api/streaming/v2"
            tonapi_base = "https://testnet.tonapi.io/v2"

        self.toncenter_v2 = ProviderConfig(
            base_url=v2_base,
            api_key=self.api_key,
            proxy=self.proxy,
            api_key_backup=self.api_key_backup,
            retry_backoff=self.retry_backoff,
            rate_limit_rps=self.rate_limit_rps,
            enable_cache=self.enable_cache,
            cache_ttl=self.cache_ttl,
            timeout=self.timeout,
            max_retries=self.max_retries,
            enabled=self.use_toncenter_v2,
        )
        self.toncenter_v3 = ProviderConfig(
            base_url=v3_base,
            api_key=self.api_key,
            proxy=self.proxy,
            api_key_backup=self.api_key_backup,
            retry_backoff=self.retry_backoff,
            rate_limit_rps=self.rate_limit_rps,
            enable_cache=self.enable_cache,
            cache_ttl=self.cache_ttl,
            timeout=self.timeout,
            max_retries=self.max_retries,
            enabled=self.use_toncenter_v3,
        )
        self.tonapi = ProviderConfig(
            base_url=tonapi_base,
            api_key=self.tonapi_key,
            proxy=self.proxy,
            retry_backoff=self.retry_backoff,
            rate_limit_rps=self.rate_limit_rps,
            enable_cache=self.enable_cache,
            cache_ttl=self.cache_ttl,
            timeout=self.timeout,
            max_retries=self.max_retries,
            enabled=self.use_tonapi,
        )
        self.streaming = ProviderConfig(
            base_url=stream_base,
            api_key=self.api_key,
            proxy=self.proxy,
            retry_backoff=self.retry_backoff,
            rate_limit_rps=self.rate_limit_rps,
            enable_cache=self.enable_cache,
            cache_ttl=self.cache_ttl,
            timeout=self.timeout,
            max_retries=self.max_retries,
            enabled=self.use_streaming,
        )

    @classmethod
    def from_env(cls, **overrides) -> "TonviewerConfig":
        """Create config primarily from environment variables."""
        return cls(**overrides)
