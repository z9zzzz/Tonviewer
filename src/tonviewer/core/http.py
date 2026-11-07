"""
Shared HTTP clients with connection pooling, bounded GET caching, rate pacing,
retry handling and provider error mapping.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import random
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional

import httpx
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import ProviderConfig
from ..exceptions import (
    APIError,
    AuthenticationError,
    InvalidResponseError,
    NetworkError,
    ProviderUnavailableError,
    RateLimitError,
    TimeoutError as TVTimeoutError,
)

logger = logging.getLogger("tonviewer.http")
_CACHE_MAX_ENTRIES = 256


def _map_http_error(
    status: int,
    body: str,
    provider: str,
    url: str,
    retry_after: Optional[str] = None,
) -> Exception:
    if status in (401, 403):
        return AuthenticationError(
            f"Authentication failed ({status})",
            provider=provider,
            details={"status": status, "url": url, "body": body[:300]},
        )
    if status == 429:
        retry_delay = None
        if retry_after:
            try:
                retry_delay = max(0.0, float(retry_after))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    retry_delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    retry_delay = None
        return RateLimitError(
            "Rate limit exceeded",
            retry_after=min(retry_delay, 60.0) if retry_delay is not None else None,
            provider=provider,
            details={"status": 429, "url": url},
        )
    if 500 <= status < 600:
        return ProviderUnavailableError(
            f"Provider returned {status}",
            provider=provider,
            details={"status": status, "url": url, "body": body[:300]},
        )
    return APIError(
        f"HTTP {status}",
        provider=provider,
        details={"status": status, "url": url, "body": body[:300]},
    )


class _HTTPPolicy:
    """Small per-client policy shared by sync and async transports."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._cache_lock = threading.RLock()
        self._rate_lock = threading.Lock()
        self._next_request_at = 0.0

    def _cache_key(self, path: str, params: Optional[Dict[str, Any]]) -> Optional[str]:
        if not self.config.enable_cache or self.config.cache_ttl <= 0:
            return None
        # Do not cache account balances, ownership pages, or transaction history.
        stable_endpoint = path.strip("/") == "rates" or (
            path.startswith("nfts/") and "/" not in path.strip("/")[5:]
        )
        if not stable_endpoint:
            return None
        encoded = json.dumps(params or {}, sort_keys=True, separators=(",", ":"), default=str)
        return f"{path}?{encoded}"

    def _cache_get(self, key: Optional[str]) -> Any:
        if key is None:
            return None
        now = time.monotonic()
        with self._cache_lock:
            item = self._cache.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return copy.deepcopy(value)

    def _cache_set(self, key: Optional[str], value: Any) -> None:
        if key is None:
            return
        with self._cache_lock:
            self._cache[key] = (time.monotonic() + self.config.cache_ttl, copy.deepcopy(value))
            self._cache.move_to_end(key)
            while len(self._cache) > _CACHE_MAX_ENTRIES:
                self._cache.popitem(last=False)

    def _wait_for_slot(self) -> None:
        rps = self.config.rate_limit_rps
        if rps <= 0:
            return
        interval = 1.0 / rps
        with self._rate_lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + interval
        if delay:
            time.sleep(delay)

    async def _await_slot(self) -> None:
        rps = self.config.rate_limit_rps
        if rps <= 0:
            return
        interval = 1.0 / rps
        with self._rate_lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + interval
        if delay:
            await asyncio.sleep(delay)

    def _retry_delay(self, attempt: int, error: Exception) -> float:
        if isinstance(error, RateLimitError) and error.retry_after is not None:
            return min(max(0.0, float(error.retry_after)), 60.0)
        base = max(0.0, self.config.retry_backoff)
        return min(base * (2 ** attempt) + random.uniform(0.0, min(0.25, base / 4)), 30.0)

    def _retryable(self, error: Exception) -> bool:
        return isinstance(error, (RateLimitError, TVTimeoutError, NetworkError, ProviderUnavailableError))


class SyncHTTP(_HTTPPolicy):
    """Synchronous HTTP client with bounded retries and reusable pooling."""

    def __init__(self, config: ProviderConfig, user_agent: str = "Tonviewer/2.2.5"):
        super().__init__(config)
        self.provider_name = "unknown"
        self._session = requests.Session()
        if config.proxy:
            self._session.proxies.update({"http": config.proxy, "https": config.proxy})
        adapter = HTTPAdapter(
            max_retries=Retry(total=0),
            pool_connections=10,
            pool_maxsize=20,
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        if config.api_key:
            self._session.headers["X-API-Key"] = config.api_key
            self._session.headers["Authorization"] = f"Bearer {config.api_key}"

    def close(self) -> None:
        self._session.close()

    def _request(self, method: str, url: str, *, params=None, json_body=None, timeout=None):
        retry_limit = self.config.max_retries if method == "GET" else 0
        retry_count = 0
        used_backup = False
        while True:
            self._wait_for_slot()
            headers = None
            if used_backup and self.config.api_key_backup:
                headers = {"X-API-Key": self.config.api_key_backup, "Authorization": f"Bearer {self.config.api_key_backup}"}
            try:
                response = self._session.request(
                    method, url, params=params, json=json_body,
                    timeout=timeout or self.config.timeout, headers=headers,
                )
            except requests.Timeout as exc:
                error = TVTimeoutError(f"Timeout calling {url}", provider=self.provider_name)
                if retry_count < retry_limit:
                    time.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error from exc
            except requests.RequestException as exc:
                error = NetworkError(f"Network error: {exc}", provider=self.provider_name)
                if retry_count < retry_limit:
                    time.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error from exc
            if response.status_code == 401 and self.config.api_key_backup and not used_backup:
                used_backup = True
                continue
            if response.status_code >= 400:
                error = _map_http_error(response.status_code, response.text, self.provider_name, url, response.headers.get("Retry-After"))
                if retry_count < retry_limit and self._retryable(error):
                    time.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error
            return response

    @staticmethod
    def _decode(response: requests.Response, url: str, provider: str) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError("Response is not valid JSON", provider=provider, details={"url": url, "body": response.text[:300]}) from exc
        if isinstance(data, dict) and "ok" in data:
            if not data.get("ok"):
                error = data.get("error") or data.get("description") or "Unknown error"
                raise APIError(str(error), provider=provider, details=data)
            return data.get("result", data)
        return data

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        key = self._cache_key(path, params)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        data = self._decode(self._request("GET", url, params=params, timeout=timeout), url, self.provider_name)
        self._cache_set(key, data)
        return data

    def post(self, path: str, *, json: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._decode(self._request("POST", url, json_body=json, timeout=timeout), url, self.provider_name)


class AsyncHTTP(_HTTPPolicy):
    """Asynchronous HTTP client with bounded retries and reusable pooling."""

    def __init__(self, config: ProviderConfig, user_agent: str = "Tonviewer/2.2.5"):
        super().__init__(config)
        self.provider_name = "unknown"
        headers = {"User-Agent": user_agent, "Accept": "application/json"}
        if config.api_key:
            headers["X-API-Key"] = config.api_key
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            headers=headers,
            follow_redirects=True,
            proxy=config.proxy,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, *, params=None, json_body=None, timeout=None):
        retry_limit = self.config.max_retries if method == "GET" else 0
        retry_count = 0
        used_backup = False
        while True:
            await self._await_slot()
            headers = None
            if used_backup and self.config.api_key_backup:
                headers = {"X-API-Key": self.config.api_key_backup, "Authorization": f"Bearer {self.config.api_key_backup}"}
            try:
                response = await self._client.request(
                    method, url, params=params, json=json_body,
                    timeout=timeout or self.config.timeout, headers=headers,
                )
            except httpx.TimeoutException as exc:
                error = TVTimeoutError(f"Timeout calling {url}", provider=self.provider_name)
                if retry_count < retry_limit:
                    await asyncio.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error from exc
            except httpx.RequestError as exc:
                error = NetworkError(f"Network error: {exc}", provider=self.provider_name)
                if retry_count < retry_limit:
                    await asyncio.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error from exc
            if response.status_code == 401 and self.config.api_key_backup and not used_backup:
                used_backup = True
                continue
            if response.status_code >= 400:
                error = _map_http_error(response.status_code, response.text, self.provider_name, url, response.headers.get("Retry-After"))
                if retry_count < retry_limit and self._retryable(error):
                    await asyncio.sleep(self._retry_delay(retry_count, error))
                    retry_count += 1
                    continue
                raise error
            return response

    @staticmethod
    def _decode(response: httpx.Response, url: str, provider: str) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError("Response is not valid JSON", provider=provider, details={"url": url, "body": response.text[:300]}) from exc
        if isinstance(data, dict) and "ok" in data:
            if not data.get("ok"):
                error = data.get("error") or data.get("description") or "Unknown error"
                raise APIError(str(error), provider=provider, details=data)
            return data.get("result", data)
        return data

    async def get(self, path: str, *, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        key = self._cache_key(path, params)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        data = self._decode(await self._request("GET", url, params=params, timeout=timeout), url, self.provider_name)
        self._cache_set(key, data)
        return data

    async def post(self, path: str, *, json: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._decode(await self._request("POST", url, json_body=json, timeout=timeout), url, self.provider_name)


async def async_retry(
    coro_factory,
    *,
    max_retries: int = 3,
    backoff: float = 1.5,
    retryable_exceptions: tuple = (RateLimitError, TVTimeoutError, NetworkError, ProviderUnavailableError),
):
    """Retry a caller-supplied safe async operation with bounded backoff."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = min(max(0.0, backoff) * (2 ** attempt) + random.uniform(0, 0.25), 30.0)
            if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                delay = min(max(delay, float(exc.retry_after)), 60.0)
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
