# Synchronous and asynchronous APIs

Tonviewer has two public API styles. They share the package data sources, but not every feature has both a sync and an async method.

## Async services

Use `TonviewerClient` from async code. It owns reusable provider clients and should be opened and closed with `async with`:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        info = await client.wallet.get_info("UQ...")
        jettons = await client.jettons.get_balances("UQ...")
        nfts = await client.nfts.get_owned("UQ...", limit=10)
        gifts = await client.gifts.get_owned_gifts("UQ...", limit=10)
        user = await client.fragment.get_username("durov")
        price = await client.prices.get_ton_usd_async()
        print(info.balance.ton, len(jettons), len(nfts), len(gifts), user.status, price)

asyncio.run(main())
```

The context manager closes the TONAPI, TON Center, Fragment, and price HTTP clients. If the context manager is not appropriate, call `await client.aclose()` in a `finally` block.

Standalone `FragmentClient` is also async and supports `await client.aclose()`. `NFTClient`, `GiftService`, and `JettonService` expose async operations and are normally obtained from `TonviewerClient`.

## Synchronous compatibility API

`Wallet` and `HashTx` are synchronous. They return JSON strings rather than Pydantic models:

```python
import json
from tonviewer import Wallet, HashTx

wallet = Wallet("UQ...")
wallet_info = json.loads(wallet.info())
transactions = json.loads(wallet.transactions(limit=5))
parsed_event = json.loads(HashTx("EVENT_ID_OR_HASH").get())
```

`Wallet` also has `action(...)` and `raw_transactions(...)`. `HashTx.get()` resolves an event/hash synchronously.

`PriceService.get_ton_usd()` is synchronous. To obtain the async version, use `client.prices.get_ton_usd_async()`.

## Method availability

| Capability | Async interface | Sync interface |
|---|---|---|
| Wallet info | `client.wallet.get_info()` | `Wallet.info()` |
| Parsed events | `client.wallet.get_transactions()` | `Wallet.transactions()` / `Wallet.action()` |
| Raw v3 transactions | `client.wallet.get_raw_transactions()` | `Wallet.raw_transactions()` |
| Event/hash lookup | Run sync `HashTx` in a worker thread if called from async code | `HashTx.get()` |
| Jetton balances | `client.jettons.get_balances()` | No sync implementation; raises `JettonError` |
| Owned NFTs/categories | `client.nfts.*` | No sync service method |
| On-chain gifts | `client.gifts.get_owned_gifts()` | No sync service method |
| Fragment username | `client.fragment.get_username()` | No sync method |
| TON price | `client.prices.get_ton_usd_async()` | `PriceService.get_ton_usd()` |

Do not call synchronous network methods directly on an asyncio event loop. If a synchronous compatibility call is necessary from async code, offload it:

```python
import asyncio
from tonviewer import HashTx

async def lookup(event_id: str) -> str:
    return await asyncio.to_thread(HashTx(event_id).get)
```
