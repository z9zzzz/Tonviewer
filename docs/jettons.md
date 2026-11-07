# Jetton balances

Jettons are TON fungible tokens. Fetch balances asynchronously from the Tonviewer client:

```python
import asyncio
from tonviewer import TonviewerClient

async def main():
    async with TonviewerClient() as client:
        balances = await client.jettons.get_balances("UQ...")
        for token in balances:
            print(token.symbol, token.balance_human, token.decimals, token.address)

asyncio.run(main())
```

The method returns a list of `JettonBalance` models. `balance` preserves the provider's raw integer amount as a string; `balance_human` scales it using the Jetton's `decimals`. A valid decimal count of zero is preserved. Missing decimal metadata falls back to nine decimals.

Other optional output fields include `name`, `image`, `verification`, and `raw` provider data. When the provider returns no balances, the list can be empty.

`get_balances_sync()` is not implemented and raises `JettonError`; use `await client.jettons.get_balances(...)` rather than calling it synchronously.
