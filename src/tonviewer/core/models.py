"""
Shared Pydantic models used across the library.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AccountState(str, Enum):
    ACTIVE = "active"
    UNINITIALIZED = "uninitialized"
    FROZEN = "frozen"
    NONEXISTENT = "nonexistent"
    EMPTY = "empty"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class AddressInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    raw: Optional[str] = None
    user_friendly: Optional[str] = None
    bounceable: Optional[str] = None
    non_bounceable: Optional[str] = None
    workchain: Optional[int] = None
    is_valid: bool = True


class PriceInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ton_usd: Optional[float] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None


class ProviderMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str
    endpoint: Optional[str] = None
    latency_ms: Optional[float] = None
    cached: bool = False
    raw: Optional[Dict[str, Any]] = None


class APIErrorDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status_code: Optional[int] = None
    message: Optional[str] = None
    provider: Optional[str] = None
    retryable: bool = False
