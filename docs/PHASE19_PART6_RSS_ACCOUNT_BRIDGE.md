# Phase19 Part6 — MARKETSPEED II RSS Account Bridge

## Goal

MARKETSPEED II RSSの公式口座系関数を使い、Ark Terminal Homeへ実保有銘柄と現物買付可能額を読み取り専用で表示する。

## Official functions

Phase19 Part6 uses only read-only list functions:

- `RssPositionList` — 国内株式の現物保有銘柄一覧
- `RssCapacityList` — 現物買付可能額と信用口座余力

The Bridge does not call order functions such as:

- `RssStockOrder`
- `RssMarginOpenOrder`
- `RssModifyOrder`
- `RssCancelOrder`

## Implemented data path

```text
MARKETSPEED II
  -> Excel RSS workbook
  -> ArkPositions: RssPositionList output
  -> ArkAccount: RssCapacityList output
  -> tools/rss_account_bridge.py
  -> tools/rss_bridge.py FastAPI
  -> http://127.0.0.1:8000/broker/*
  -> real-account-home.js
  -> Home 実口座カード
```

## Native Excel output

MARKETSPEED II RSS list functions use this layout:

```text
row 1: RSS function
row 2: returned-field headers
row 3+: returned data
```

The reader detects the official Japanese headers rather than relying on fixed manually copied columns.

### ArkPositions

Register `RssPositionList` at `A1`.

- leave symbol blank to return all holdings
- select all account categories
- expected fields include holding quantity, average acquisition price, market price, market value, and unrealized P&L

### ArkAccount

Register `RssCapacityList` at `A1`.

The Bridge reads `現物買付可能額`.

## Metric truthfulness

The official RSS functions used here do not directly return total assets or cash balance.

Therefore Home displays:

- buying power: official `RssCapacityList` value
- market value: sum of official `RssPositionList` market values
- unrealized P&L: sum of official `RssPositionList` unrealized P&L
- total assets: unavailable (`--`)
- cash balance: unavailable and not substituted with buying power

This prevents a misleading `0` or a false equation between cash and buying power.

## Backward compatibility

The former normalized `ArkAccount` / `ArkPositions` cell layout remains readable for compatibility, but new setups should use native MARKETSPEED II RSS output.

Legacy text labels without valid numeric account values fail closed and no longer produce `connected: true`.

## Local endpoints

- `GET /broker/connection`
- `GET /broker/account`
- `GET /broker/positions`
- `GET /broker/snapshot`

These endpoints do not implement POST, PUT, PATCH, or DELETE.

## Home behavior

1. Home tries `http://127.0.0.1:8000/broker/connection` first.
2. If the local Bridge responds, Home uses that source.
3. If the local Bridge is unavailable, Home falls back to `/api/broker-readonly/connection`.
4. Values remain `--` when the official RSS source does not provide them.
5. No order controls are rendered.

## Privacy

The browser receives only the normalized display snapshot.

Not returned:

- brokerage login ID
- password
- API key
- account number
- authentication cookie
- raw Excel workbook
- raw broker payload

`accountId` is always `null` in the Excel account reader.

## Safety

The following remain disabled:

- live order creation
- live order transmission
- live order cancellation
- account mutation
- runtime unlock

Phase19 Part4 broker-write-lock remains the final enforcement boundary.

## Fail-closed rules

- Missing `ArkAccount` sheet -> disconnected
- Missing `RssCapacityList` buying-power output -> disconnected
- Missing Excel or MARKETSPEED II RSS -> disconnected
- Descriptive text without numeric account data -> disconnected
- Invalid or zero position quantity -> row ignored
- Local Bridge unavailable -> remote read-only status fallback
- No verified value -> Home displays `--`, not `0`

## Validation

CI covers:

- native `RssPositionList` parsing
- native `RssCapacityList` parsing
- official header-row detection
- legacy-sheet compatibility
- descriptive-text false-positive prevention
- missing-sheet fail closed
- GET-only broker endpoints
- account ID non-exposure
- unavailable metric preservation
- local-first Home integration
- remote fallback presence
- restricted CORS origins
- existing Prediction tests
- existing Discovery tests
- existing RSS market-data tests

## Phase19 completion boundary

Code completion means the official read-only RSS path and UI are implemented and tested.

Operational completion requires the user's Windows machine to have:

- MARKETSPEED II running
- Excel running
- RSS add-in connected
- active workbook open
- `RssPositionList` registered in `ArkPositions`
- `RssCapacityList` registered in `ArkAccount`
- local FastAPI Bridge running on `127.0.0.1:8000`

Real trading remains out of scope.
