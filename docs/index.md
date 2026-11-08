# Tonviewer

Tonviewer is a Python SDK and command-line interface for TON wallet information, parsed account events, indexed transactions, Jetton balances, NFTs, on-chain collectible gifts, Fragment username lookups, and TON prices. It provides asynchronous typed services through `TonviewerClient` and a synchronous compatibility interface through `Wallet` and `HashTx`.

The package requires Python 3.10 or newer. Network access is needed for live provider data; API keys are optional for public endpoints and subject to provider limits.

## Features

- Wallet information and balances, with TONAPI metadata and TON Center v2 fallback.
- Parsed TONAPI account events and separate raw TON Center v3 transaction responses.
- Async NFT, Jetton, on-chain gift, and Fragment services.
- TON/USD price lookup with TONAPI and CoinGecko sources.
- A CLI installed as `Tonviewer` and a synchronous `Wallet`/`HashTx` compatibility API.

See the [architecture and data sources](architecture.md) for provider boundaries and caveats. In particular, Fragment is parsed from public HTML; NFT categories are metadata heuristics; and scam indicators are not security conclusions.

## Installation

Install the published distribution with pip:

```bash
python -m pip install --upgrade Tonviewer
```

For a source checkout and contributor setup, see [Installation](installation.md) and [Development](development.md).

## Quick start

Use the async client as a context manager so its HTTP clients are closed cleanly:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        info = await client.wallet.get_info("UQ...")
        print(info.address, info.balance.ton, info.status.value)
        page = await client.wallet.get_transactions("UQ...", limit=5)
        print(page["transactions"])

asyncio.run(main())
```

The synchronous compatibility API returns JSON strings:

```python
import json
from tonviewer import Wallet, HashTx

wallet = Wallet("UQ...")
info = json.loads(wallet.info())
print(info.get("Balance"))
event = json.loads(HashTx("EVENT_ID_OR_TRANSACTION_HASH").get())
```

These are network-backed examples; use a real TON address and provider access where needed. More verified examples are in [Examples](examples.md).

## Documentation

### Getting started

- [Installation](installation.md)
- [Examples](examples.md)
- [Synchronous and asynchronous APIs](sync-async.md)
- [Configuration](configuration.md)

### Feature guides

- [Wallets](wallets.md)
- [Transactions and events](transactions.md)
- [NFTs](nfts.md)
- [On-chain collectible gifts](gifts.md)
- [Jettons](jettons.md)
- [Fragment usernames](fragment.md)
- [TON prices](prices.md)
- [Command-line interface](cli.md)

### Reference and project information

- [API reference and output models](api-reference.md)
- [Errors and troubleshooting](errors.md)
- [Architecture and data sources](architecture.md)
- [Development and documentation](development.md)
- [Fixes and behavior notes](changelog.md)
- [Audit fixes](fixes.md)

```{toctree}
:hidden:
:maxdepth: 2

README
installation
examples
sync-async
configuration
wallets
transactions
nfts
gifts
jettons
fragment
prices
cli
api-reference
errors
architecture
development
changelog
fixes
```

Project source and issue tracking are on [GitHub](https://github.com/z9zzzz/Tonviewer).
