# Phase28.5 Excel Preview Runner

This phase adds a local Windows-only proof runner for the existing MARKETSPEED II RSS / Excel / Python bridge.

## Commands

```powershell
py tools/run_phase28_excel_preview.py --symbol 7203.T --quantity 100 --limit-price 1
```

The FastAPI bridge also exposes:

```text
POST /dry-run/order-preview?symbol=7203.T&quantity=100&limit_price=1
```

## Safety invariants

- The target worksheet is `ARK_ORDER`.
- Cell `B9` is the order trigger and is always written as `FALSE`.
- No `RssStockOrder`, modify or cancel operation is invoked.
- `brokerWriteAllowed` remains `false`.
- `liveTradingAllowed` remains `false`.
- The feature only writes a local Excel preview after the Phase27 approval, risk and kill-switch gates pass.
- Missing `ARK_ORDER` sheet causes a safe failure.

## Proof checklist

1. Run the local Python tests.
2. Open MARKETSPEED II and the Excel RSS workbook.
3. Confirm the workbook contains an `ARK_ORDER` sheet.
4. Run the preview command.
5. Confirm cells B2-B8 contain the preview values.
6. Confirm B9 is `FALSE`.
7. Confirm the output reports `brokerWrites: 0` and `liveOrders: 0`.
