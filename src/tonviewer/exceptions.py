"""
Tonviewer exception hierarchy.

All library errors inherit from TonviewerError.
"""

from __future__ import annotations
from typing import Any, Optional


class TonviewerError(Exception):
    """Base class for all Tonviewer errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: Optional[str] = None,
        operation: Optional[str] = None,
        retryable: bool = False,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.provider = provider
        self.operation = operation
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.retryable:
            parts.append("retryable=True")
        return " | ".join(parts)


class ConfigurationError(TonviewerError):
    """Invalid configuration or missing required settings."""


class ValidationError(TonviewerError):
    """Input validation failed."""


class AddressError(ValidationError):
    """Invalid or unsupported TON address."""


class WalletError(TonviewerError):
    """Wallet-related operation failed."""


class TransactionError(TonviewerError):
    """Transaction fetch or parsing failed."""


class NFTError(TonviewerError):
    """NFT operation failed."""


class JettonError(TonviewerError):
    """Jetton operation failed."""


class FragmentError(TonviewerError):
    """Base for all Fragment-related errors."""


class APIError(TonviewerError):
    """Generic API / HTTP layer error."""


class AuthenticationError(APIError):
    """401 / 403 — invalid or missing API key."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class RateLimitError(APIError):
    """429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("retryable", True)
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class TimeoutError(APIError):
    """Request timed out."""

    def __init__(self, message: str = "Request timed out", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class NetworkError(APIError):
    """Network connectivity problem."""

    def __init__(self, message: str = "Network error", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderUnavailableError(APIError):
    """Provider is down or returned 5xx."""

    def __init__(self, message: str = "Provider unavailable", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class InvalidResponseError(APIError):
    """Response could not be parsed or has unexpected structure."""


class ParsingError(APIError):
    """Failed to parse provider response into expected model."""


class PaginationError(APIError):
    """Pagination failed or incomplete results."""


# ── Fragment specific ──────────────────────────────────────────────────────

class UserNotFoundError(FragmentError):
    """Username does not exist on Fragment / Telegram."""

    def __init__(self, username: str, **kwargs: Any) -> None:
        super().__init__(f"Username not found: @{username}", **kwargs)
        self.username = username


class WalletNotFoundError(FragmentError):
    """Username exists but no associated wallet could be resolved."""


class FragmentBlockedError(FragmentError):
    """Cloudflare / WAF hard block (403)."""

    def __init__(self, message: str = "Blocked by Cloudflare / Fragment WAF", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class FragmentFetchError(FragmentError):
    """Network / HTTP failure after retries."""


class FragmentParseError(FragmentError):
    """HTML structure changed or could not be parsed."""


class FragmentRateLimitError(FragmentError):
    """Fragment rate limited the client."""

    def __init__(self, message: str = "Fragment rate limit", **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class FragmentUnavailableError(FragmentError):
    """Fragment service temporarily unavailable."""
