# Telegram collectible gifts

`client.gifts.get_owned_gifts()` finds wallet-owned items classified as gifts by the NFT service. These are on-chain NFT collectibles. It does not list ordinary Telegram gifts that have not been minted as NFTs.

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        gifts = await client.gifts.get_owned_gifts("UQ...", limit=25)
        for gift in gifts:
            print(gift.name, gift.collection, gift.address, gift.is_on_chain)

asyncio.run(main())
```

The return value is a list of `GiftInfo` models. Example of the shape (optional fields can be absent):

```json
{
  "name": "Collectible Gift #123",
  "collection": "Example Gifts",
  "address": "EQ...",
  "owner": "UQ...",
  "image": "https://example.invalid/gift.webp",
  "is_collectible": true,
  "is_listed": false,
  "is_on_chain": true,
  "attributes": [{"trait_type": "Background", "value": "Blue"}],
  "source": "tonapi"
}
```

`limit=None` is the default and asks the NFT category service for all matching gifts. The category is based on NFT name and collection metadata, so verify important classifications against the underlying item. No marketplace listing or floor-price query is performed by this gift method.
