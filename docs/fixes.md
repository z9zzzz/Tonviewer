# Audit fixes

This page complements [Fixes and behavior notes](changelog.md) with the main regression areas verified in the audited source tree.

## Transaction accounting and direction

Native TON values are converted from nanoTON with decimal precision retained. Spend and receive totals are wallet-relative, self-transfers are not misclassified, and failed TON transfers are not counted in successful totals. Jetton scaling respects zero decimals as well as normal decimal counts. NFT purchase participants follow seller-to-buyer direction in both the rich parser and legacy normalized event output.

## Pagination and repeated work

NFT category filters apply `offset` and `limit` after classification. Owned NFT pages are parsed incrementally, and repeated item addresses are skipped in the all-pages path. Transaction enrichment deduplicates NFT addresses in a batch and caps async metadata lookups at eight concurrent tasks. Optional lookup failures leave the transaction action visible.

Transaction pagination accepts either `before_lt` or the compatible `lt` alias. It rejects conflicting values, removes repeated event IDs on each page, filters events on or after a supplied LT when the event includes LT, and returns `next_before_lt` only if a usable event LT is available.

## Networking and source identity

GET retry policy uses retryable error types and server `Retry-After` where available. Unsafe POST operations are not automatically replayed. TON Center's backup key is attempted only after an authentication response from a TON Center client. Sync and async clients share the bounded cache/rate/retry policy; cacheable paths exclude volatile account/event feeds. Price lookups reuse configured clients and report which source served `PriceInfo`.

## Validation and optional data

TON addresses are validated through the TON SDK parser rather than only a fixed friendly-address pattern. Fragment HTTP 403 maps to the typed blocked error with URL/status context. Owner NFT counts from account stats are preserved rather than overwritten by the length of a fetched page.

These fixes do not make live provider responses immutable or guarantee that Fragment's HTML selectors remain valid. For those constraints see [Architecture](architecture.md) and [Fragment](fragment.md).
