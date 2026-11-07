# Fragment usernames

The async Fragment service reads public Fragment username pages and parses available status and sale information. There is no official Fragment API client in this package; HTML layout changes, access restrictions, or rate limits can affect results.

```python
import asyncio
from tonviewer import FragmentBlockedError, FragmentParseError, TonviewerClient, UserNotFoundError

async def main():
    async with TonviewerClient() as client:
        try:
            result = await client.fragment.get_username("durov")  # leading @ is also accepted
            print(result.username, result.status.value)
            print(result.owner_wallet, result.price, result.price_ton)
            print(result.auction_ends, result.is_collectible)
        except UserNotFoundError:
            print("Username was not found.")
        except FragmentBlockedError:
            print("Fragment denied this request; try later or configure a proxy.")
        except FragmentParseError:
            print("The page could not be parsed; its structure may have changed.")

asyncio.run(main())
```

`FragmentResult` may include `username`, `status`, `owner_wallet`, `owner_display`, `price`, `price_ton`, `min_bid`, `auction_ends`, `bids`, `is_collectible`, `nfts`, `purchased`, and `balance`. Most details are optional. `to_dict()` omits empty fields and provides display keys for some fields.

Statuses include `available`, `taken`, `sold`, `on_auction`, `on_sale`, `not_found`, `unknown`, and `blocked`. Do not assume a missing owner or price means zero or that a parsed listing is still current. Treat the output as a page snapshot, not a marketplace guarantee. This service is async; there is no synchronous Fragment lookup method.
