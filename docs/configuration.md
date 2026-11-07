# Configuration

`TonviewerClient()` uses `TonviewerConfig` defaults. Pass explicit constructor values for common options, or construct a config for provider-level controls.

## API keys

The configuration reads these variables when the corresponding constructor argument is omitted:

| Environment variable | Provider/use |
|---|---|
| `TONCENTER_API_KEY` or legacy `TON_API_KEY` | Primary TON Center key |
| `TONCENTER_API_KEY_BACKUP` | One backup key attempt after HTTP 401 from TON Center |
| `TONAPI_KEY` or `TONAPI_API_KEY` | TONAPI key |
| `TON_NETWORK` | Not automatically read by the current config; set `network=` explicitly |

Example for PowerShell:

```powershell
$env:TONCENTER_API_KEY = "..."
$env:TONAPI_KEY = "..."
```

Example for Linux/macOS:

```bash
export TONCENTER_API_KEY="..."
export TONAPI_KEY="..."
```

Never commit real keys to a repository or put them in logs. The backup key is configured for TON Center providers; it is not copied into TONAPI configuration.

## Main options

```python
from tonviewer import TonviewerClient
from tonviewer.config import TonviewerConfig

config = TonviewerConfig(
    api_key="TONCENTER_KEY",          # optional
    api_key_backup="TONCENTER_BACKUP", # optional
    tonapi_key="TONAPI_KEY",           # optional
    network="mainnet",                 # or "testnet"
    timeout=30.0,
    max_retries=3,
    retry_backoff=1.5,
    rate_limit_rps=8.0,
    enable_cache=True,
    cache_ttl=30.0,
    use_tonapi=True,
    use_toncenter_v2=True,
    use_toncenter_v3=True,
    proxy=None,
)

client = TonviewerClient(config=config)
```

Network selection changes TON Center v2/v3 and TONAPI base URLs. `proxy` is an HTTPX-compatible proxy URL and is passed to provider and Fragment clients. `timeout` is seconds. `rate_limit_rps` is a soft request pace per HTTP client instance, not a shared process-wide quota.

## Retry and cache behavior

Automatic status retries are restricted to GET requests. POST calls are not repeated automatically. Retryable errors use the configured retry count and backoff, and HTTP 429 responses can use the provider's `Retry-After` header. A backup key is attempted after a 401 response; it is not a general failover provider.

The bounded HTTP cache is limited to stable rate responses and individual NFT metadata. It does not cache wallet balances, owned-NFT pages, or account events. `cache_ttl=0` or `enable_cache=False` turns caching off. PriceService also retains its fetched price for the configured TTL on that service instance.

## Provider toggles

`use_tonapi`, `use_toncenter_v2`, and `use_toncenter_v3` enable or disable the corresponding clients. Wallet information prefers TONAPI and can fall back to TON Center v2. Raw transactions specifically require TON Center v3. Parsed account-event transactions require TONAPI.

`use_streaming=True` is not supported and raises `ConfigurationError`; it must not be used as if it started a stream. For live application notifications, configure a separate supported webhook integration.
