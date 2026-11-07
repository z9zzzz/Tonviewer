# Usage examples

The snippets use `UQ...` and `EQ...` as placeholders. Replace them with valid addresses appropriate for the selected network.

## Async wallet, transactions, NFTs, and prices

```python
import asyncio
from tonviewer import TonviewerClient

ADDRESS = "UQ..."

async def main():
    async with TonviewerClient() as client:
        wallet = await client.wallet.get_info(ADDRESS)
        print({
            "address": wallet.address,
            "balance_ton": wallet.balance.ton,
            "balance_usd": wallet.balance.usd,
            "status": wallet.status.value,
            "nfts_count": wallet.nfts_count,
        })

        tx_page = await client.wallet.get_transactions(ADDRESS, limit=5)
        print(tx_page["total"], tx_page["total_spend_ton"])
        for tx in tx_page["transactions"]:
            print(tx.get("Action"), tx.get("From"), tx.get("To"), tx.get("Price"))

        nfts = await client.nfts.get_owned(ADDRESS, limit=10)
        gifts = await client.gifts.get_owned_gifts(ADDRESS, limit=10)
        jettons = await client.jettons.get_balances(ADDRESS)
        print(len(nfts), len(gifts), len(jettons))
        print(await client.prices.get_ton_usd_async())

asyncio.run(main())
```

Example printed wallet summary (illustrative, not a live value):

```text
{'address': 'UQ...', 'balance_ton': 1.25, 'balance_usd': 8.125,
 'status': 'active', 'nfts_count': 12}
```

## Sync compatibility API

```python
import json
from tonviewer import HashTx, Wallet

wallet = Wallet("UQ...")
info = json.loads(wallet.info())
rows = json.loads(wallet.transactions(limit=10, action="sent ton"))
print(info.get("Balance"))
print(rows.get("total"), rows.get("total_spend_ton"))
print(json.loads(HashTx("EVENT_ID_OR_HASH").get()))
```

## Inspect an NFT portfolio

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        portfolio = await client.nfts.get_categorized("UQ...", limit=100)
        print("all:", portfolio.count)
        print("usernames:", len(portfolio.usernames))
        print("gifts:", len(portfolio.gifts))
        print("others:", len(portfolio.others))
        print("matching:", [item.name for item in portfolio.search("star")])

asyncio.run(main())
```

## Error-aware Fragment lookup

```python
import asyncio
from tonviewer import FragmentBlockedError, FragmentParseError, TonviewerClient, UserNotFoundError

async def username_snapshot(name: str):
    async with TonviewerClient() as client:
        try:
            result = await client.fragment.get_username(name)
            return result.to_dict()
        except UserNotFoundError:
            return {"username": name, "status": "not_found"}
        except FragmentBlockedError:
            return {"username": name, "error": "blocked; try later"}
        except FragmentParseError:
            return {"username": name, "error": "page format was not recognized"}

async def main():
    print(await username_snapshot("durov"))

asyncio.run(main())
```

For complete parameter and output details, use the corresponding [feature guide](README.md#feature-guides).
