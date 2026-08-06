# Phase31 Parts5-8 Statistical Review

## Scope

This phase adds review-only statistical validation on top of the immutable Champion/Candidate paired run created in Parts1-4.

- Part5: bootstrap candidate advantage and 95% interval
- Part6: regime-by-regime stability checks
- Part7: Candidate Review Dashboard payload
- Part8: mandatory human-review gate

## Safety contract

The implementation is evaluation-only.

- no automatic Candidate promotion
- no Production model update
- no broker write
- no live order
- no order create, transmit, cancel, or modify
- no Excel order write
- no ARK_ORDER B9 change
- no RssStockOrder call

Even when every statistical gate passes, the final status is `READY_FOR_HUMAN_REVIEW`. It never grants execution or promotion authority.
