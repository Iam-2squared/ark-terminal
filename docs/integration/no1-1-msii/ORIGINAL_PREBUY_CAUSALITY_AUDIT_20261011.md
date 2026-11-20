# Original No.1.1 / V5 pre-BUY feature causality audit

Authority: byte-frozen public core_features.py, commit 710656491be06235901b45c50a8b5cbd714ba4eb, Git blob 685a7774ed96556b810aa23957d12fda8f9654ba.

Source facts: original projection time is entry fill_minute, and source references actual entry fill_price. Three model inputs explicitly depend on a confirmed fill: entry/fill_clock, entry/intent_to_fill_active_delay, and selector/raw_entry_vs_first_price_pct. An actual BUY fill is generally not known at the earlier moment when the BUY decision would have to be submitted. Substituting predicted/future fill price or duration would alter the original Frozen model inputs, hence cannot silently attest to unchanged No.1.1 pre-BUY ranking.

The new pure audit returns ORIGINAL_PRE_BUY_RANK_CAUSALITY_NOT_PROVEN before BUY fill, even when caller supplies theoretical timestamps. It can validate post-filled chronology for monitoring only, but never issues a live signal, trade, or additional manual permission. This is an essential research-to-production causality gap separate from Excel RSS order ON/OFF. It requires authentic evidence of an independently available pre-entry rank or a separately selected revised deployable strategy, not a fabricated new condition.

Excel order permission stays OFF. Frozen/main unchanged. productionReady=false. No model retraining, account files, broker orders, or private ledger writes.
