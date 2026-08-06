# Phase28 Parts4-6: MARKETSPEED II RSS safe preparation

This phase extends the local Windows MARKETSPEED II RSS / Excel / Python bridge without enabling live order transmission.

## Part4: Excel preparation

- Uses an `ARK_ORDER` worksheet contract.
- Writes preview values only after Phase27 approval, risk and kill-switch checks pass.
- Cell `B9` is the order trigger and is always forced to `FALSE`.
- No `RssStockOrder`, modify or cancel operation is invoked.

## Part5: RSS status readback

Known Japanese RSS states are normalized for Ark Terminal display. The status path is read-only and cannot mutate an order.

## Part6: activation evidence gate

The gate checks Paper and Shadow evidence, incidents, kill-switch tests and account-rule confirmation. Even when all thresholds pass, the state stops at `READY_FOR_HUMAN_REVIEW`.

## Safety invariants

- `automaticActivationAllowed: false`
- `excelOrderTriggerAllowed: false`
- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- final activation remains outside the application and requires a future explicit decision after sufficient evidence and account-rule checks.
