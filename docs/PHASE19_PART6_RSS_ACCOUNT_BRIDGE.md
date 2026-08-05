# Phase19 Part6 — MARKETSPEED II RSS Account Bridge

## Goal

既存のMARKETSPEED II RSS・Excel・Python Bridgeを拡張し、Ark Terminal Homeの実口座カードへ残高と保有銘柄を読み取り専用で表示する。

## Implemented data path

```text
MARKETSPEED II
  -> Excel RSS workbook
  -> ArkAccount / ArkPositions sheets
  -> tools/rss_account_bridge.py
  -> tools/rss_bridge.py FastAPI
  -> http://127.0.0.1:8000/broker/*
  -> real-account-home.js
  -> Home 実口座カード
```

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
4. Values remain `--` when no verified account snapshot exists.
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
- Empty account values -> disconnected
- Missing Excel or MARKETSPEED II RSS -> disconnected
- Invalid position quantity -> row ignored or normalized without inventing holdings
- Local Bridge unavailable -> remote read-only status fallback
- No verified value -> Home displays `--`, not `0`

## Excel contract

See `tools/README_RSS.md` for the exact `ArkAccount` and `ArkPositions` cell layout.

The Bridge reads values already present in Excel. It does not invent RSS formulas and does not store credentials.

## Validation

CI covers:

- account normalization
- position normalization
- missing-sheet fail closed
- GET-only broker endpoints
- account ID non-exposure
- local-first Home integration
- remote fallback presence
- restricted CORS origins
- existing Prediction tests
- existing Discovery tests
- existing RSS market-data tests

## Phase19 completion boundary

Code completion means the read-only path and UI are implemented and tested.

Operational completion still requires the user's Windows machine to have:

- MARKETSPEED II running
- Excel running
- RSS add-in connected
- active workbook open
- `ArkAccount` populated
- `ArkPositions` populated
- local FastAPI Bridge running on `127.0.0.1:8000`

Real trading remains out of scope.
