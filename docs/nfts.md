# NFTs

`client.nfts` provides async NFT ownership and metadata methods backed by TONAPI. Returned `NFTItem` models include the contract address, name, image, collection, owner, attributes, and a best-effort category.

## Fetch owned NFTs

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        items = await client.nfts.get_owned("UQ...", limit=20, offset=0)
        for item in items:
            print(item.address, item.name, item.collection_name, item.category)

asyncio.run(main())
```

With `limit=None` (the default), `get_owned()` retrieves all pages. For bounded requests, provide a limit and optional offset. The result is a list of `NFTItem` models; `floor_price_ton` is optional and is not fetched by default.

## Category helpers

The classifier maps items to `username`, `gift`, or `other`, using collection and metadata text. It is a heuristic and should not be treated as authoritative collection verification.

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        usernames = await client.nfts.get_usernames("UQ...", limit=10)
        gifts = await client.nfts.get_gifts("UQ...", limit=10)
        other_items = await client.nfts.get_others("UQ...", limit=10)
        portfolio = await client.nfts.get_categorized("UQ...", limit=100)
        print(portfolio.count, portfolio.has("chill flame"))
        print([n.name for n in portfolio.search("lamp")])
        print(portfolio.value_summary())

asyncio.run(main())
```

Category helper `offset` and `limit` are applied after matching the requested category. `NFTOwnedResult.value_summary()` only adds `floor_price_ton` values already present; because floors are not fetched by default, many or all values can be zero.

## Single item and raw helper

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        item = await client.nfts.get_item("EQ...")
        print(item.name, item.attributes)
        raw_view = await client.nfts.get_owned_raw("UQ...", limit=5)
        print(raw_view["count"], raw_view["items"])

asyncio.run(main())
```

`get_item()` returns a parsed `NFTItem`. `get_owned_raw()` returns a dictionary with `count` and model-dumped `items`, omitting each model's `raw` field. For Telegram gifts that appear as on-chain NFT collectibles, see [Gifts](gifts.md).
