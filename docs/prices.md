# TON price

The price service returns a TON/USD value as a Python `float`. The primary source is TONAPI rates, with CoinGecko used as a fallback when the primary lookup fails.

## Async client

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        usd = await client.prices.get_ton_usd_async()
        print(f"1 TON ≈ ${usd:.4f}")

asyncio.run(main())
```

## Synchronous service

```python
from tonviewer.prices.service import PriceService

prices = PriceService()
try:
    print(prices.get_ton_usd())
    info = prices.get_price_info()
    print(info.ton_usd, info.source, info.timestamp)
finally:
    prices.close()
```

`get_price_info()` returns a `PriceInfo` model with `ton_usd`, `source`, and `timestamp`. The plain `get_ton_usd()` methods return a float. If neither source can provide a valid response, the call raises `NetworkError`. This quote is indicative data, not a trading price or financial recommendation.

Within a service instance, a fetched value may be reused for the configured cache TTL. Create a new service or disable caching if your use case needs different refresh behavior. `TonviewerClient` closes its price clients when its async context exits.
