# Errors and troubleshooting

All SDK-specific exceptions inherit from `TonviewerError`. Common types include `AddressError`, `WalletError`, `TransactionError`, `NFTError`, `JettonError`, `FragmentError`, and HTTP-layer `APIError` subclasses such as `AuthenticationError`, `RateLimitError`, `TimeoutError`, `NetworkError`, `ProviderUnavailableError`, and `InvalidResponseError`.

Catch the narrowest expected error first:

```python
from tonviewer import AddressError, RateLimitError, TonviewerClient, WalletError

async def main():
    async with TonviewerClient() as client:
        try:
            info = await client.wallet.get_info("not-an-address")
        except AddressError as exc:
            print("Check the TON address:", exc)
        except RateLimitError as exc:
            print("Provider rate limit; retry after:", exc.retry_after)
        except WalletError as exc:
            print("Wallet lookup failed:", exc)
```

Compatibility helpers return JSON strings and may encode an error object in that string rather than raising the same error to the caller. Parse their result with `json.loads()` and check for an `error` key.

## Common issues

**Wrong package imported:** Print `tonviewer.__file__` to confirm the import points at your intended virtual environment or source tree. On Windows, use the venv interpreter explicitly, such as `.\.venv\Scripts\python.exe -m pytest`.

**Async tests say “async def functions are not natively supported”:** Install test extras using the same interpreter that runs pytest: `python -m pip install -e ".[dev]"`. This includes pytest-asyncio.

**Fragment returns blocked/parse errors:** The service reads public HTML and can be blocked or affected by markup changes. Catch `FragmentBlockedError`, `FragmentFetchError`, or `FragmentParseError`; the current Fragment client maps non-success HTTP responses to fetch/blocked exceptions. Do not loop rapidly or treat parsed details as guaranteed current.

**No TON/USD value in wallet info:** Price providers may be unavailable. Wallet balance remains available; optional `balance.usd` can be `None`.

**Missing NFT floor price:** The NFT service does not fetch floors by default. A missing `floor_price_ton` is not a zero market value.

See [Configuration](configuration.md) for provider settings and [Sync and async APIs](sync-async.md) for lifecycle guidance.
