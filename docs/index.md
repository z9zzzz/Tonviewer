```{image} _static/ton-mark.svg
:alt: TON network mark
:align: center
:width: 76px
:class: tonviewer-mark
```

# Tonviewer

<div class="tv-tagline">A Python SDK and CLI for exploring TON wallets and on-chain data.</div>

<p align="center">
  <a href="https://pypi.org/project/Tonviewer/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/Tonviewer?style=for-the-badge&logo=pypi&logoColor=white&color=0876b4"></a>
  <a href="https://pypi.org/project/Tonviewer/"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/Tonviewer?style=for-the-badge&logo=python&logoColor=white"></a>
  <a href="https://github.com/z9zzzz/Tonviewer/blob/master/LICENSE"><img alt="MIT license" src="https://img.shields.io/github/license/z9zzzz/Tonviewer?style=for-the-badge&color=1687c9"></a>
  <a href="https://github.com/z9zzzz/Tonviewer/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/z9zzzz/Tonviewer/ci.yml?branch=master&style=for-the-badge&logo=githubactions&logoColor=white"></a>
  <a href="https://tonviewer.readthedocs.io/en/latest/"><img alt="Read the Docs" src="https://img.shields.io/readthedocs/tonviewer?style=for-the-badge&logo=readthedocs&logoColor=white"></a>
</p>

Tonviewer brings the common TON explorer workflows into one Python package. Use the async `TonviewerClient` for typed service APIs, or the synchronous `Wallet` and `HashTx` helpers when you need the compatibility interface.

## Get started

**Python 3.10 or newer** is required. Install the published package:

```bash
python -m pip install --upgrade Tonviewer
```

Make your first wallet lookup with the asynchronous client:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        wallet = await client.wallet.get_info("YOUR_TON_ADDRESS")
        print(wallet.address, wallet.balance.ton, wallet.status.value)

asyncio.run(main())
```

Replace `YOUR_TON_ADDRESS` with a valid address. This example makes a live network request. For more examples, API key configuration, and the synchronous interface, continue to [Examples](examples.md) and [Configuration](configuration.md).

## What you can do

- **Wallets and transactions** — inspect account details, parse TONAPI events, or retrieve raw TON Center v3 transaction data.
- **Tokens and collectibles** — retrieve Jetton balances, owned NFTs, and on-chain collectible gifts.
- **Fragment and prices** — look up public Fragment username pages and TON/USD pricing.
- **Command line** — run wallet, transaction, price, hash, and Fragment lookups with the `Tonviewer` command.

Review the [architecture and data-source notes](architecture.md) before relying on provider data. Fragment results depend on public-page parsing, NFT labels use metadata heuristics, and scam indicators are caution flags rather than security verdicts.

## Documentation

### Learn the API

- [Installation](installation.md) · [Quick-start examples](examples.md) · [Sync and async APIs](sync-async.md)
- [Configuration](configuration.md) · [API models and output](api-reference.md) · [Errors and troubleshooting](errors.md)

### Feature guides

- [Wallet information](wallets.md) · [Transactions and pagination](transactions.md)
- [NFTs](nfts.md) · [Collectible gifts](gifts.md) · [Jettons](jettons.md)
- [Fragment usernames](fragment.md) · [TON prices](prices.md) · [CLI](cli.md)

### Project and contributing

- [Architecture](architecture.md) · [Development](development.md)
- [Verified fixes and behavior notes](changelog.md) · [Audit-fix details](fixes.md)
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

Source, issue tracking, and releases are available on [GitHub](https://github.com/z9zzzz/Tonviewer).
