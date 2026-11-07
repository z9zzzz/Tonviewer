# Wallet information

The async wallet service validates and normalizes a TON address, then returns a `WalletInfo` model. It prefers TONAPI for rich fields and may fall back to TON Center v2 for account data.

## Async usage

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        info = await client.wallet.get_info("UQ...")
        print(info.address)
        print(info.balance.ton)       # TON amount
        print(info.balance.nanotons)  # integer nanoTON amount
        print(info.balance.usd)       # None if no price was available
        print(info.status.value)
        print(info.is_wallet)
        print(info.last_activity)
        print(info.name, info.icon)
        print(info.nfts_count)
        print(info.explorer_url)

asyncio.run(main())
```

The return type is `tonviewer.WalletInfo`. Its balance is a `WalletBalance` model. Optional metadata can be absent if the provider does not include it. USD conversion depends on a price source and is not guaranteed.

## Synchronous legacy output

`Wallet.info()` returns an indented JSON string and omits some empty fields:

```python
from tonviewer import Wallet

print(Wallet("UQ...").info())
```

Representative shape (live values vary):

```json
{
  "Balance": "1.250 TON ≈ 8.125 $",
  "Status": "active",
  "Is_wallet": true,
  "Last_activity": "2026-11-06 02:37:47 PM",
  "Name": "example.t.me",
  "Icon": "https://example.invalid/icon.png",
  "NFTs": 12,
  "Address": "UQ..."
}
```

Decode compatibility output when your program needs a dictionary:

```python
import json
from tonviewer import Wallet

payload = json.loads(Wallet("UQ...").info())
print(payload.get("Balance"))
```

## Address helpers

`is_valid_address()` is a syntactic parser check; it does not establish that an address currently exists on-chain. `normalize_address()` converts a parseable friendly or raw address to a user-friendly representation and raises `AddressError` for invalid input. Additional helpers include `to_raw()`, `parse_address()`, and `detect_address_type()` under `tonviewer.utils.address`.
