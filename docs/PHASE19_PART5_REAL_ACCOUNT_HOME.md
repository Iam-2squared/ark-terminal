# Phase19 Part5 — Real Account Home

## Goal

Add a clearly separated real brokerage account area to Home without enabling any real order operation.

## Repository Audit Result

Before this part, Home displayed only the Paper Trading account.

The read-only broker API routes existed, but the production handlers still returned placeholder states:

```text
connection.connected=false
connection.authenticated=false
connection.provider=unconfigured
account=null
positions=[]
```

Therefore, no real account balance or real position data was visible in the application.

## Home Display

Home now mounts a dedicated `実口座` card below the existing Home account area.

The card displays:

- connection state
- provider label
- last synchronization time
- position count
- total equity
- cash balance
- market value
- unrealized profit/loss

Values are shown only after connection, authentication, and an account snapshot are all available.

Missing data is displayed as `--`. It is never converted into a fake zero balance.

## Privacy Boundary

The Home view model does not expose:

- account ID
- account number
- credentials
- tokens
- raw broker payloads

## Permanent Safety Boundary

The Home integration:

- sends GET requests only
- sets `X-Ark-Read-Only: true`
- contains no submit-order function
- contains no cancel-order function
- contains no approval token
- provides no buy or sell button
- keeps live execution disabled

The Phase19 Part4 broker write lock remains active beneath this UI.

## Current Limitation

The UI location is complete, but actual real account values will remain `未接続` and `--` until a verified server-side read-only brokerage provider replaces the current placeholder API responses.

No claim is made that real account data is already synchronized.
