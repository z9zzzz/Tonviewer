import pytest
import respx
import httpx
from tonsdk.utils import Address

from tonviewer.exceptions import FragmentBlockedError, RateLimitError
from tonviewer.core.http import AsyncHTTP, SyncHTTP, _map_http_error
from tonviewer.config import TonviewerConfig
from tonviewer.fragment.client import FragmentClient
from tonviewer.fragment.models import FragmentResult, UsernameStatus
from tonviewer.prices.service import PriceService
from tonviewer.jettons.service import JettonService
from tonviewer.nfts.service import NFTClient
from tonviewer.utils.address import detect_address_type, is_valid_address
from tonviewer.wallet.transactions import build_transactions_payload, parse_event_actions


WALLET = Address(f"0:{'11' * 32}").to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=False)
OTHER = Address(f"0:{'22' * 32}").to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=False)
THIRD = Address(f"0:{'33' * 32}").to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=False)


def _transfer(sender, recipient, amount="1", status="ok"):
    return {
        "event_id": "event-id",
        "timestamp": 1_700_000_000,
        "actions": [{
            "type": "TonTransfer",
            "status": status,
            "TonTransfer": {
                "sender": {"address": sender},
                "recipient": {"address": recipient},
                "amount": amount,
            },
        }],
    }


def test_ton_transfer_direction_and_unknown_counterparties():
    assert parse_event_actions(_transfer(OTHER, WALLET), wallet_address=WALLET)[0]["Action"] == "Received TON"
    assert parse_event_actions(_transfer(WALLET, OTHER), wallet_address=WALLET)[0]["Action"] == "Sent TON"
    self_row = parse_event_actions(_transfer(WALLET, WALLET), wallet_address=WALLET)[0]
    assert self_row["Action"] == "Self-transfer TON"
    assert self_row["_incoming"] is None
    unrelated = parse_event_actions(_transfer(OTHER, THIRD), wallet_address=WALLET)[0]
    assert unrelated["Action"] == "TON transfer (direction unknown)"
    assert unrelated["_incoming"] is None


def test_failed_transfers_excluded_and_tiny_amount_precision_retained():
    payload = build_transactions_payload(
        [_transfer(WALLET, OTHER, "1000000001"), _transfer(WALLET, OTHER, "5000000000", "failed")],
        wallet_address=WALLET,
    )
    assert payload["total_spend_ton"] == 1.000000001
    assert payload["transactions"][0]["Price"].startswith("-1.000000001 TON")
    assert len(payload["transactions"]) == 2


@pytest.mark.parametrize("decimals,raw,human", [(0, "123", 123), (1, "123", 12.3), (6, "1230000", 1.23), (9, "1230000000", 1.23), (None, "1230000000", 1.23)])
def test_jetton_decimals_are_respected(decimals, raw, human):
    class Provider:
        async def get_jettons(self, address):
            jetton = {"address": OTHER, "symbol": "TEST"}
            if decimals is not None:
                jetton["decimals"] = decimals
            return {"balances": [{"balance": raw, "jetton": jetton}]}

    async def run():
        result = await JettonService(Provider()).get_balances(WALLET)
        assert result[0].decimals == (9 if decimals is None else decimals)
        assert result[0].balance_human == human

    import asyncio
    asyncio.run(run())


def test_ton_address_parser_accepts_test_only_and_raw_addresses():
    raw = "-1:" + "ab" * 32
    user_friendly = Address(raw).to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=True)
    test_only = Address(raw).to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=True, is_test_only=True)
    assert is_valid_address(raw)
    assert detect_address_type(raw) == "raw"
    assert is_valid_address(user_friendly)
    assert is_valid_address(test_only)
    assert detect_address_type(test_only) == "user_friendly"
    assert not is_valid_address(test_only[:-1] + ("A" if test_only[-1] != "A" else "B"))


@pytest.mark.asyncio
async def test_fragment_403_raises_fragment_blocked_error_with_context():
    client = FragmentClient()
    try:
        with respx.mock(assert_all_called=True) as router:
            router.get("https://fragment.com/username/testuser").mock(return_value=httpx.Response(403))
            with pytest.raises(FragmentBlockedError) as caught:
                await client.get_username("testuser")
            assert caught.value.details == {"url": "https://fragment.com/username/testuser", "status": 403}
    finally:
        await client.aclose()


def test_rate_limit_maps_retry_after_seconds_and_dates():
    error = _map_http_error(429, "", "provider", "https://example.invalid", "7")
    assert isinstance(error, RateLimitError)
    assert error.retry_after == 7.0
    dated = _map_http_error(429, "", "provider", "https://example.invalid", "not a date")
    assert dated.retry_after is None


def test_zero_transaction_limit_returns_no_rows():
    result = build_transactions_payload([_transfer(WALLET, OTHER)], wallet_address=WALLET, limit=0)
    assert result["transactions"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_gift_filter_paginates_until_filtered_limit_is_met():
    raw = []
    for index in range(1000):
        name = "Collectible Gift #1" if index == 0 else f"Regular item {index}"
        raw.append({"address": f"item-{index}", "metadata": {"name": name}})
    raw.append({"address": "gift-final", "metadata": {"name": "Collectible Gift #2"}})

    class Provider:
        def __init__(self):
            self.offsets = []

        async def get_nfts(self, address, *, limit, offset, collection=None):
            self.offsets.append(offset)
            return {"nft_items": raw[offset:offset + limit]}

    provider = Provider()
    gifts = await NFTClient(provider).get_gifts(WALLET, limit=2)
    assert [item.address for item in gifts] == ["item-0", "gift-final"]
    assert provider.offsets == [0, 1000]


def test_configured_proxy_reaches_sync_async_and_fragment_clients():
    proxy = "http://127.0.0.1:8888"
    config = TonviewerConfig(proxy=proxy)
    assert config.tonapi.proxy == proxy
    # The third positional argument remains timeout for existing callers.
    from tonviewer.config import ProviderConfig
    assert ProviderConfig("https://example.invalid", None, 12.0).timeout == 12.0
    from tonviewer.client import TonviewerClient
    client = TonviewerClient(config=config)
    assert client.fragment.proxy == proxy
    sync = SyncHTTP(config.tonapi)
    assert sync._session.proxies["https"] == proxy
    sync.close()
    async_client = AsyncHTTP(config.tonapi)
    assert async_client._client._mounts
    import asyncio
    async def close_all():
        await async_client.aclose()
        await client.aclose()
    asyncio.run(close_all())


def test_price_info_reports_the_actual_fallback_source(monkeypatch):
    calls = []
    def fake_get(self, path, *, params=None, timeout=None):
        url = self.config.base_url + "/" + path.lstrip("/")
        calls.append(url)
        if "tonapi" in url:
            raise RuntimeError("primary unavailable")
        return {"the-open-network": {"usd": 2.5}}

    monkeypatch.setattr("tonviewer.prices.service.SyncHTTP.get", fake_get)
    service = PriceService()
    try:
        info = service.get_price_info()
        assert info.ton_usd == 2.5
        assert info.source == "coingecko"
        assert info.timestamp.tzinfo is not None
    finally:
        service.close()
    assert calls == ["https://tonapi.io/v2/rates", "https://api.coingecko.com/api/v3/simple/price"]


@pytest.mark.asyncio
async def test_fragment_owner_enrichment_does_not_replace_account_nft_count():
    class Provider:
        def __init__(self):
            self.nft_calls = 0
        async def get_account(self, address):
            return {"balance": 1230000000, "stats": {"nfts_count": 2501}}
        async def get_rates(self):
            return {"rates": {"TON": {"prices": {"USD": 2}}}}
        async def get_nfts(self, *args, **kwargs):
            self.nft_calls += 1
            return {"nft_items": [{}]}

    provider = Provider()
    client = FragmentClient(tonapi=provider)
    result = FragmentResult(username="example", status=UsernameStatus.SOLD, owner_wallet=WALLET)
    await client._enrich_owner(result)
    assert result.nfts == 2501
    assert provider.nft_calls == 0
    await client.aclose()
