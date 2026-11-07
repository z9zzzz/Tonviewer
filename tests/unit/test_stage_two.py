import asyncio
from collections import defaultdict

import httpx
import pytest
import respx
from tonsdk.utils import Address

from tonviewer.config import ProviderConfig, TonviewerConfig
from tonviewer.core.http import AsyncHTTP, SyncHTTP
from tonviewer.wallet.service import WalletService


WALLET = Address("0:" + "45" * 32).to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=False)
NFT_A = "0:" + "aa" * 32
NFT_B = "0:" + "bb" * 32


def test_sync_get_cache_is_ttl_and_mutation_safe_and_skips_balances():
    config = ProviderConfig("https://api.example", rate_limit_rps=0, cache_ttl=30)
    client = SyncHTTP(config)
    calls = []

    class Response:
        status_code = 200
        text = "{\"name\":\"x\"}"
        headers = {}
        def json(self):
            calls.append("network")
            return {"name": "x"}

    client._session.request = lambda *args, **kwargs: Response()
    try:
        first = client.get("nfts/" + NFT_A)
        first["name"] = "changed"
        assert client.get("nfts/" + NFT_A) == {"name": "x"}
        client.get("accounts/" + WALLET)
        client.get("accounts/" + WALLET)
        assert len(calls) == 3
        assert len(client._cache) == 1
    finally:
        client.close()


def test_sync_retry_after_and_backup_key_fallback():
    cfg = ProviderConfig(
        "https://api.example", api_key="primary", api_key_backup="backup",
        rate_limit_rps=0, max_retries=1, retry_backoff=0,
    )
    client = SyncHTTP(cfg)
    calls = []

    class Response:
        def __init__(self, status, payload=None, headers=None):
            self.status_code = status
            self.text = "{}"
            self.headers = headers or {}
            self.payload = payload or {"ok": True, "result": {"value": 1}}
        def json(self):
            return self.payload

    def request(method, url, **kwargs):
        calls.append((kwargs.get("headers") or {}).copy())
        if len(calls) == 1:
            return Response(401)
        if len(calls) == 2:
            return Response(429, headers={"Retry-After": "0"})
        return Response(200)

    client._session.request = request
    try:
        assert client.get("rates") == {"value": 1}
        assert len(calls) == 3
        assert calls[1]["X-API-Key"] == "backup"
    finally:
        client.close()


@pytest.mark.asyncio
async def test_async_get_cache_and_safe_retry():
    cfg = ProviderConfig("https://api.example", rate_limit_rps=0, max_retries=1, retry_backoff=0)
    client = AsyncHTTP(cfg)
    try:
        with respx.mock(assert_all_called=False) as router:
            route = router.get("https://api.example/nfts/" + NFT_A).mock(
                side_effect=[httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json={"name": "n"})]
            )
            assert await client.get("nfts/" + NFT_A) == {"name": "n"}
            assert await client.get("nfts/" + NFT_A) == {"name": "n"}
            assert route.call_count == 2
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_async_nft_enrichment_deduplicates_and_bounds_in_flight():
    cfg = TonviewerConfig(use_toncenter_v2=False, use_toncenter_v3=False, rate_limit_rps=0)

    class Provider:
        def __init__(self):
            self.calls = defaultdict(int)
            self.active = 0
            self.maximum = 0
        async def get_nft_item(self, address):
            self.calls[address] += 1
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            await asyncio.sleep(0.001)
            self.active -= 1
            if address == NFT_B:
                raise RuntimeError("optional metadata outage")
            return {"metadata": {"name": "A-name"}}

    provider = Provider()
    service = WalletService(cfg, tonapi=provider)
    events = [{"actions": [
        {"type": "NftItemTransfer", "NftItemTransfer": {"nft": {"address": NFT_A}}},
        {"type": "NftPurchase", "NftPurchase": {"nft": {"address": NFT_A}}},
        {"type": "NftItemTransfer", "NftItemTransfer": {"nft": {"address": NFT_B}}},
        *[{"type": "NftItemTransfer", "NftItemTransfer": {"nft": {"address": f"item-{i}"}}} for i in range(24)],
    ]}]
    await service._enrich_nft_names(events)
    assert provider.calls[NFT_A] == 1
    assert provider.calls[NFT_B] == 1
    assert len(provider.calls) == 26
    assert events[0]["actions"][0]["NftItemTransfer"]["nft_name"] == "A-name"
    assert "nft_name" not in events[0]["actions"][2]["NftItemTransfer"]
    assert 1 < provider.maximum <= 8


def test_backup_key_is_not_sent_to_tonapi_config():
    cfg = TonviewerConfig(api_key="main", api_key_backup="backup", rate_limit_rps=0)
    assert cfg.toncenter_v2.api_key_backup == "backup"
    assert cfg.toncenter_v3.api_key_backup == "backup"
    assert cfg.tonapi.api_key_backup is None

@pytest.mark.asyncio
async def test_event_cursor_alias_and_conflict_validation():
    from tonviewer.providers.tonapi import TonAPIProvider
    provider = TonAPIProvider(ProviderConfig("https://api.example/v2", rate_limit_rps=0, max_retries=0))
    try:
        with respx.mock(assert_all_called=True) as router:
            route = router.get("https://api.example/v2/accounts/" + WALLET + "/events").mock(
                return_value=httpx.Response(200, json={"events": []})
            )
            await provider.get_account_events(WALLET, lt=12345)
            assert route.calls.last.request.url.params["before_lt"] == "12345"
        with pytest.raises(ValueError):
            await provider.get_account_events(WALLET, lt=1, before_lt=2)
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_wallet_cursor_deduplicates_events_and_returns_next_lt():
    from tonviewer.wallet.service import WalletService
    event = {"event_id": "same", "lt": "900", "timestamp": 1_700_000_000, "actions": []}
    class Provider:
        def __init__(self):
            self.cursor = None
            self.calls = 0
        async def get_account_events(self, address, *, limit, before_lt):
            self.cursor = before_lt
            if before_lt == 1000:
                boundary = {"event_id": "boundary", "lt": "1000", "timestamp": 1_700_000_000, "actions": []}
                return {"events": [event, dict(event), boundary]}
            inclusive = {"event_id": "same", "lt": str(before_lt), "timestamp": 1_700_000_000, "actions": []}
            older = {"event_id": "older", "lt": "800", "timestamp": 1_700_000_000, "actions": []}
            return {"events": [inclusive, older]}
        async def get_nft_item(self, address):
            self.calls += 1
            return {}
    cfg = TonviewerConfig(use_toncenter_v2=False, use_toncenter_v3=False, rate_limit_rps=0)
    provider = Provider()
    service = WalletService(cfg, tonapi=provider)
    result = await service.get_transactions(WALLET, lt=1000)
    assert provider.cursor == 1000
    assert result["total"] == 1
    assert result["next_before_lt"] == 900
    page_two = await service.get_transactions(WALLET, before_lt=result["next_before_lt"])
    assert provider.cursor == 900
    assert page_two["total"] == 1
    assert page_two["next_before_lt"] == 800


def test_nft_purchase_direction_is_seller_to_buyer_in_rich_and_v1_parsers():
    import json
    from tonviewer.compat import _normalized_event
    from tonviewer.wallet.transactions import parse_event_actions
    seller = {"address": "seller-address"}
    buyer = {"address": "buyer-address"}
    event = {"timestamp": 1_700_000_000, "actions": [{
        "type": "NftPurchase", "status": "ok",
        "NftPurchase": {"seller": seller, "buyer": buyer, "nft": {"address": "nft-address"}},
    }]}
    rich = parse_event_actions(event, wallet_address=WALLET)[0]
    v1 = _normalized_event(event)["actions"][0]
    assert rich["From"] == "seller-address" and rich["To"] == "buyer-address"
    assert v1["From"] == "seller-address" and v1["To"] == "buyer-address"


def test_rate_pacing_uses_configured_requests_per_second(monkeypatch):
    import tonviewer.core.http as transport
    client = SyncHTTP(ProviderConfig("https://api.example", rate_limit_rps=0.5))
    sleeps = []
    monkeypatch.setattr(transport.time, "sleep", lambda delay: sleeps.append(delay))
    try:
        client._wait_for_slot()
        client._wait_for_slot()
        assert len(sleeps) == 1
        assert sleeps[0] == pytest.approx(2.0, abs=0.01)
    finally:
        client.close()


def test_streaming_option_is_explicitly_rejected():
    from tonviewer.exceptions import ConfigurationError
    with pytest.raises(ConfigurationError, match="not implemented"):
        TonviewerConfig(use_streaming=True)


def test_wallet_transaction_provider_error_is_not_rewrapped():
    from tonviewer.exceptions import RateLimitError
    from tonviewer.wallet.service import WalletService
    error = RateLimitError("slow down", retry_after=0)
    class Provider:
        def get_account_events_sync(self, *args, **kwargs):
            raise error
    cfg = TonviewerConfig(use_toncenter_v2=False, use_toncenter_v3=False, rate_limit_rps=0)
    service = WalletService(cfg, tonapi=Provider())
    with pytest.raises(RateLimitError) as caught:
        service.get_transactions_sync(WALLET)
    assert caught.value is error


def test_price_service_uses_config_cache_and_proxy(monkeypatch):
    import tonviewer.prices.service as prices
    cfg = TonviewerConfig(proxy="http://127.0.0.1:8888", cache_ttl=12, rate_limit_rps=0)
    calls = []
    def fake_get(self, path, *, params=None, timeout=None):
        calls.append((self.config.base_url, self.config.proxy, timeout))
        return {"rates": {"TON": {"prices": {"USD": 3.25}}}}
    monkeypatch.setattr(prices.SyncHTTP, "get", fake_get)
    service = prices.PriceService(cfg)
    try:
        assert service.get_ton_usd() == 3.25
        assert service.get_ton_usd() == 3.25
        assert len(calls) == 1
        assert calls[0][1] == "http://127.0.0.1:8888"
        assert calls[0][2] == 10
    finally:
        service.close()


@pytest.mark.asyncio
async def test_async_backup_key_retry_and_rate_pacing(monkeypatch):
    import tonviewer.core.http as transport
    cfg = ProviderConfig(
        "https://api.example", api_key="primary", api_key_backup="backup",
        rate_limit_rps=0, max_retries=0,
    )
    client = AsyncHTTP(cfg)
    try:
        with respx.mock(assert_all_called=True) as router:
            route = router.get("https://api.example/rates").mock(
                side_effect=[httpx.Response(401), httpx.Response(200, json={"ok": True, "result": {"value": 2}})]
            )
            assert await client.get("rates") == {"value": 2}
            assert route.calls[0].request.headers["X-API-Key"] == "primary"
            assert route.calls[1].request.headers["X-API-Key"] == "backup"
    finally:
        await client.aclose()

    paced = AsyncHTTP(ProviderConfig("https://api.example", rate_limit_rps=0.5))
    sleeps = []
    original_sleep = transport.asyncio.sleep
    async def fake_sleep(delay):
        sleeps.append(delay)
    monkeypatch.setattr(transport.asyncio, "sleep", fake_sleep)
    try:
        await paced._await_slot()
        await paced._await_slot()
        assert sleeps == [pytest.approx(2.0, abs=0.02)]
    finally:
        monkeypatch.setattr(transport.asyncio, "sleep", original_sleep)
        await paced.aclose()
