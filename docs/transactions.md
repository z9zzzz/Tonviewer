# Transactions and events

Tonviewer offers two different views. Parsed TONAPI account events are convenient for readable action summaries. Raw TON Center v3 transactions preserve the provider response for audit-oriented work; they are not the same data shape.

## Parsed events

Async:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        page = await client.wallet.get_transactions(
            "UQ...", limit=20, action="received ton"
        )
        for row in page["transactions"]:
            print(row["Action"], row["From"], row["To"], row["Price"], row["State"])

asyncio.run(main())
```

Sync compatibility:

```python
import json
from tonviewer import Wallet

wallet = Wallet("UQ...")
page = json.loads(wallet.transactions(limit=20, action="jetton"))
print(page["total"], page["transactions"])
```

A row can contain `Action`, `Time`, `From`, `To`, `Price`, `State`, `Comment`, `Hash`, `Scam`, `#`, and `NFT` where relevant. Fields with no value can be omitted by the compatibility JSON formatter. Amounts in native TON transfers are converted from nanoTON using decimal-safe arithmetic. Failed native transfer rows remain visible, but failed transfers are excluded from the native TON totals.

A representative page shape is:

```json
{
  "transactions": [
    {
      "Action": "Received TON",
      "Time": "30 Oct 03:37:05 PM",
      "From": "UQ...",
      "To": "UQ...",
      "Price": "+1.25 TON",
      "State": "Success",
      "Comment": "",
      "Hash": "EVENT_ID",
      "Scam": false,
      "#": 1
    }
  ],
  "total": 1,
  "skipped": 0,
  "dollar_rate": 6.5,
  "total_spend_ton": 0.0,
  "total_spend_usd": 0.0,
  "total_received_ton": 1.25,
  "total_received_usd": 8.125
}
```

`action` accepts filters such as `sent ton`, `received ton`, `ton`, `jetton`, `nft`, and `scam`. `number` selects a 1-based row from the filtered result. `limit=0` yields an empty transaction list.

## Cursor pagination

Pass `before_lt` or its alias `lt`. If both are supplied, they must have the same value. The output includes `next_before_lt` only when TONAPI events contain parseable `lt` values:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        page = await client.wallet.get_transactions("UQ...", limit=20)
        next_lt = page.get("next_before_lt")
        if next_lt is not None:
            next_page = await client.wallet.get_transactions("UQ...", limit=20, lt=next_lt)
            print(next_page["transactions"])

asyncio.run(main())
```

When the provider returns LT values, the client removes duplicate event IDs in the page and excludes boundary-or-newer LT values locally. Events without a usable LT cannot be locally boundary-checked. Cursor data depends on the provider response; treat missing cursor values as “no cursor provided,” not as a numeric zero.

## Raw TON Center v3 data

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        raw = await client.wallet.get_raw_transactions(
            "UQ...", limit=100, offset=0, sort="desc"
        )
        print(raw)

asyncio.run(main())
```

The sync compatibility counterpart is `Wallet.raw_transactions(limit, offset, sort)`. Both require the TON Center v3 provider. Use raw transactions when you need the indexed provider response rather than Tonviewer’s action-row formatter.

## Hash/event lookup

`HashTx(event_id_or_hash).get()` is synchronous and returns a JSON string with a normalized event/action breakdown. In an async application, call it via `asyncio.to_thread()` or keep the lookup outside the event loop. See [Sync and async APIs](sync-async.md).
