# Fixes and behavior notes

This page summarizes behavior verified in the audited source tree and regression tests. It is not a promise that every remote provider schema remains unchanged.

## Transaction correctness

- Native TON amounts retain fractional precision when converted from nanoTON.
- Native sent/received totals use wallet-relative direction, avoid counting self-transfers as incoming or outgoing, and exclude failed transfers.
- Jetton transfer amounts respect the declared decimal count, including a valid zero-decimal token.
- `NftPurchase` rows use seller-to-buyer direction in both the rich event formatter and legacy normalized-event formatter.
- `lt` is accepted as an alias for `before_lt`; the returned `next_before_lt` is added only when events have a usable logical time.
- Duplicate event IDs are discarded within a fetched page. LT boundaries are locally filtered when the provider returns LT.
- NFT category offset/limit are applied after classification, and paged results avoid duplicate NFT addresses.

## Requests and enrichment

- Only safe GET requests are retried automatically. POST requests are not retried by the shared HTTP layer.
- HTTP 429 errors can expose `Retry-After` as seconds or an HTTP date.
- TON Center backup API key use is limited to a single retry on HTTP 401; the key is not passed to TONAPI.
- Proxy, timeout, retry, rate-pacing, and cache settings are propagated to configured provider and price clients.
- HTTP caching is bounded and restricted to rate and single-NFT metadata endpoints; wallet balances, event feeds, and owned-NFT pages are not cached.
- NFT metadata enrichment deduplicates NFT addresses per transaction batch, caps async concurrency at eight, and does not discard a transaction row if optional metadata lookup fails.
- Wallet information preserves an NFT count already present in account statistics instead of replacing it with a partial page size.

## Validation, compatibility, and Fragment

- Address validation uses the TON SDK parser, allowing supported raw and friendly/test-only forms rather than relying solely on a narrow prefix expression.
- Fragment HTTP 403 handling constructs `FragmentBlockedError` with URL/status details. Fragment owner enrichment preserves the account-level NFT count and does not fetch one NFT page merely to infer it.
- The price service reuses configured sync/async clients, preserves which price provider supplied the value, and closes its clients through service/client cleanup.
- Unsupported `use_streaming=True` now raises a configuration error rather than appearing enabled without an implementation. The separate streaming API is deprecated; this package does not implement webhook delivery.

## Known limits

Fragment is parsed from public HTML and may change structure or block requests. Address, price, owner, and status values can be unavailable. Gift classification is metadata-based and covers collectible gifts represented as on-chain NFTs, not ordinary off-chain Telegram gifts. The `Scam` field is a warning indicator, not a security verdict. See each [feature guide](README.md#feature-guides) for relevant caveats.
