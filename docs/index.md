<p align="center">
<img class="tv-home-logo" src="https://github.com/user-attachments/assets/0724b226-fdeb-4c2c-ad48-de3ac0bb2159" alt="Tonviewer logo" width="280">
</p>

# Tonviewer

<div class="tv-tagline">A Python SDK and command-line toolkit for TON blockchain data.</div> <p class="tv-badges">
<a href="https://pypi.org/project/Tonviewer/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/Tonviewer?style=flat-square&color=0876b4"></a>
  <a href="https://pypi.org/project/Tonviewer/"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/Tonviewer?style=flat-square"></a>
  <a href="https://github.com/z9zzzz/Tonviewer/blob/master/LICENSE"><img alt="MIT license" src="https://img.shields.io/github/license/z9zzzz/Tonviewer?style=flat-square"></a>
  <a href="https://github.com/z9zzzz/Tonviewer/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/z9zzzz/Tonviewer/ci.yml?branch=master&style=flat-square&logo=githubactions"></a>
  <a href="https://tonviewer.readthedocs.io/en/latest/"><img alt="Read the Docs" src="https://img.shields.io/readthedocs/tonviewer?style=flat-square&logo=readthedocs"></a>
  <a href="https://github.com/z9zzzz/Tonviewer"><img alt="GitHub stars" src="https://img.shields.io/github/stars/z9zzzz/Tonviewer?style=flat-square&logo=github"></a>
  <a href="https://pypi.org/project/Tonviewer/"><img alt="Monthly downloads" src="https://img.shields.io/pypi/dm/Tonviewer?label=downloads%2Fmonth&style=flat-square"></a>
  <a href="https://github.com/z9zzzz/Tonviewer/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors/z9zzzz/Tonviewer?style=flat-square"></a>
</p>

Tonviewer makes common TON explorer workflows available from Python. Use `TonviewerClient` for asynchronous services and typed models, or the synchronous `Wallet` and `HashTx` compatibility helpers.

---

## Quickstart

Install Tonviewer from PyPI. Python 3.10 or newer is required.

```bash
python -m pip install --upgrade Tonviewer
```

Fetch wallet information with the async client:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        wallet = await client.wallet.get_info("YOUR_TON_ADDRESS")
        print(wallet.address, wallet.balance.ton, wallet.status.value)

asyncio.run(main())
```

Replace `YOUR_TON_ADDRESS` with a valid TON address. This example makes a live network request. Continue to [Installation](installation.md) or [Examples](examples.md) for setup and more ways to use the library.

## Features

- **Wallets and transactions** — get account details, parse TONAPI events, and retrieve raw TON Center v3 transaction data.

- **Jettons and NFTs** — inspect token balances, owned NFTs, metadata, and categories.

- **Collectible gifts** — find on-chain collectibles represented as NFTs.

- **Fragment and prices** — look up public Fragment username pages and TON/USD rates.

- **Command line** — run wallet, transaction, hash, price, and Fragment lookups from the `Tonviewer` command.

Provider data can be incomplete or delayed. Fragment results depend on public-page parsing, NFT labels use metadata heuristics, and scam indicators are caution flags—not security verdicts. See [Architecture and data sources](architecture.md) for the scope and limitations.

## User guide

### Getting started

- [Installation](installation.md)

- [Quick-start examples](examples.md)

- [Sync and async APIs](sync-async.md)

- [Configuration](configuration.md)

### Feature guides

- [Wallets](wallets.md) · [Transactions](transactions.md) · [NFTs](nfts.md)

- [Gifts](gifts.md) · [Jettons](jettons.md) · [Fragment](fragment.md) · [Prices](prices.md)

- [Command-line interface](cli.md)

### Reference and project

- [API reference](api-reference.md)

- [Errors and troubleshooting](errors.md)

- [Architecture](architecture.md)

- [Development](development.md)

- [Changelog and verified behavior notes](changelog.md)

- [Audit fixes](fixes.md)

- [Full documentation index](README.md)

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

Source code, releases, and issue tracking are on [GitHub](https://github.com/z9zzzz/Tonviewer).