"""
Tonviewer — Professional TON Blockchain Python SDK

Public API:
    from tonviewer import (
        TonviewerClient, Wallet, HashTx,
        FragmentClient, NFTClient,
        WalletInfo, FragmentResult, ...
    )
"""

from __future__ import annotations

__version__ = "2.2.5"
__author__ = "AhMed / PyCodz"


from .client import TonviewerClient
from .compat import Wallet, HashTx
from .fragment.client import FragmentClient
from .fragment.models import FragmentResult, UsernameStatus
from .nfts.service import NFTClient, NFTItem, NFTAttribute, NFTOwnedResult
from .jettons.service import JettonService, JettonBalance
from .gifts.service import GiftService, GiftInfo

from .exceptions import (
    TonviewerError,
    ConfigurationError,
    ValidationError,
    AddressError,
    WalletError,
    TransactionError,
    NFTError,
    JettonError,
    FragmentError,
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    NetworkError,
    ProviderUnavailableError,
    InvalidResponseError,
    ParsingError,
    UserNotFoundError,
    WalletNotFoundError,
    FragmentBlockedError,
    FragmentFetchError,
    FragmentParseError,
)

from .wallet.models import WalletInfo, WalletBalance, AccountState
from .core.models import AddressInfo, PriceInfo

__all__ = [
    "__version__",
    "TonviewerClient",
    "Wallet",
    "HashTx",
    "NFTClient",
    "FragmentClient",
    "JettonService",
    "GiftService",
    "WalletInfo",
    "WalletBalance",
    "AccountState",
    "AddressInfo",
    "PriceInfo",
    "FragmentResult",
    "UsernameStatus",
    "NFTItem",
    "NFTAttribute",
    "NFTOwnedResult",
    "JettonBalance",
    "GiftInfo",
    "TonviewerError",
    "ConfigurationError",
    "ValidationError",
    "AddressError",
    "WalletError",
    "TransactionError",
    "NFTError",
    "JettonError",
    "FragmentError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "TimeoutError",
    "NetworkError",
    "ProviderUnavailableError",
    "InvalidResponseError",
    "ParsingError",
    "UserNotFoundError",
    "WalletNotFoundError",
    "FragmentBlockedError",
    "FragmentFetchError",
    "FragmentParseError",
]