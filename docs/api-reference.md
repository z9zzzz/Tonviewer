# API models and output map

The async service API returns Pydantic models for most domain objects and a dictionary for parsed transaction pages. The compatibility classes `Wallet` and `HashTx` return JSON strings.

## Wallet models

`WalletInfo` fields include `address`, `address_info`, `balance`, `status`, `is_wallet`, `last_activity`, `name`, `icon`, `nfts_count`, `interfaces`, `contract_type`, `explorer_url`, `provider`, and `raw`. Optional fields may be `None` if absent from the provider.

`WalletBalance` includes `nanotons` (integer), `ton` (float), optional `usd`, and optional `price` metadata. When serialized through Pydantic, enum values and datetimes are serialized according to Pydantic's JSON rules.

## Transaction pages

`client.wallet.get_transactions()` returns a dictionary:

- `transactions`: cleaned action rows.
- `total`: row count after filtering and limit.
- `skipped`: matching rows omitted by the limit.
- `dollar_rate`: optional conversion rate.
- `total_spend_ton`, `total_received_ton`: native TON totals for returned successful rows.
- `total_spend_usd`, `total_received_usd`: optional USD totals.
- `next_before_lt`: optional pagination cursor, included only when event LT values are available.

A transaction row's common keys are `Action`, `Time`, `From`, `To`, `Price`, `State`, `Comment`, `Hash`, `Scam`, and `#`. `NFT` may be added when the action includes NFT metadata. Not every row contains every optional key.

## NFT models

`NFTItem` fields include `address`, `name`, `description`, `image`, `collection_address`, `collection_name`, `owner`, `attributes`, `is_telegram_gift`, `category`, `floor_price_ton`, and `raw`. `NFTAttribute` contains `trait_type` and `value`. `floor_price_ton` is not populated by default.

`NFTOwnedResult`, returned by `get_categorized()`, groups items in `all`, `usernames`, `gifts`, and `others`; it also exposes `count`, `search()`, `filter_by()`, `has()`, `by_category()`, and `value_summary()`.

## Gift and Jetton models

`GiftInfo` contains `name`, `collection`, `address`, `owner`, `image`, `is_collectible`, `is_listed`, `is_on_chain`, `attributes`, `source`, and `raw`. Current gift listing returns on-chain collectible NFT-derived records; it does not query a Telegram user's off-chain gift inventory.

`JettonBalance` contains `address`, `symbol`, `name`, raw `balance` as a string, `balance_human`, `decimals`, `image`, `verification`, and `raw`.

## Fragment and price models

`FragmentResult` includes `username`, `status`, `owner_wallet`, `owner_display`, `price`, `price_ton`, `min_bid`, `auction_ends`, `bids`, `is_collectible`, `nfts`, `purchased`, `balance`, `source`, and timestamps/error metadata. `to_dict()` omits empty fields and maps some keys to display names such as `NFTs`, `Purchased`, and `Balance`.

`PriceInfo` contains `ton_usd`, `source`, and `timestamp`. `PriceService.get_ton_usd()` and `get_ton_usd_async()` return a `float`, not a `PriceInfo` object. Use `get_price_info()` for the typed metadata response.

## Exception types

All package exceptions inherit from `TonviewerError`. Common subclasses include `AddressError`, `WalletError`, `TransactionError`, `NFTError`, `JettonError`, `FragmentError`, `APIError`, `AuthenticationError`, `RateLimitError`, `TimeoutError`, `NetworkError`, `ProviderUnavailableError`, and `InvalidResponseError`. See [errors and troubleshooting](errors.md).

## Exported API objects

The following public objects are re-exported from the top-level `tonviewer` package. Their docstrings and signatures are generated from the source:

.. automodule:: tonviewer
   :members: TonviewerClient, Wallet, HashTx, WalletInfo, WalletBalance, FragmentResult, NFTItem, JettonBalance, GiftInfo, PriceInfo
