# Tonviewer documentation

Tonviewer is a Python SDK and CLI for reading public TON blockchain data. This guide describes the current package API in `src/tonviewer`; where a method exists only in one style, the page says so explicitly.

## Start here

- [Installation and development setup](installation.md) — PyPI/source installs and test dependencies.
- [Quick start and examples](examples.md) — working async and sync entry points with representative output.
- [Sync and async APIs](sync-async.md) — which service methods block, which are awaitable, and how to close clients.
- [Configuration](configuration.md) — networks, API keys, timeouts, retries, caching, rate pacing, and proxies.
- [API models and output map](api-reference.md) — main fields returned by the typed API and JSON compatibility layer.

## Feature guides

- [Wallet information](wallets.md)
- [Parsed and raw transactions](transactions.md)
- [Jetton balances](jettons.md)
- [NFT ownership and categories](nfts.md)
- [On-chain collectible gifts](gifts.md)
- [Fragment usernames](fragment.md)
- [TON price](prices.md)
- [Command-line interface](cli.md)

## Operations and contribution

- [Errors and troubleshooting](errors.md)
- [Architecture and data sources](architecture.md)
- [Verified fixes and behavior changes](changelog.md) and [audit-fix details](fixes.md)
- [Development and tests](development.md)

The repository [README](https://github.com/z9zzzz/Tonviewer/blob/master/README.md) is the short project overview. Install the package from PyPI using `python -m pip install --upgrade Tonviewer`. The source metadata requires Python 3.10 or newer.

## API choice at a glance

`TonviewerClient` is the asynchronous entry point and provides `.wallet`, `.nfts`, `.gifts`, `.jettons`, `.fragment`, and `.prices`. Use it as an async context manager:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        info = await client.wallet.get_info("UQ...")
        print(info.balance.ton, info.status.value)

asyncio.run(main())
```

`Wallet` and `HashTx` are synchronous compatibility helpers. They return JSON-formatted strings; use `json.loads()` when a Python dictionary is needed. `PriceService` provides a synchronous price method. The NFT, gift, Jetton, and Fragment service methods documented here are asynchronous.

## How to read the examples

Replace `UQ...` and `EQ...` with a real, valid mainnet or testnet address. Placeholder addresses in code samples are not usable credentials. Example output is illustrative: live balances, names, metadata, and rates depend on the provider response and current chain state. A `None` value generally means the provider did not supply that optional field.
