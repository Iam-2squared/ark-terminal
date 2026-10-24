# Ark No.1.2: deployable *research candidate*, not Frozen No.1.1
Date: 2026-10-11. Independent branch based on integration/no1-1-msii-cash-locked-v1 at 4110059f.

## Scope
The parent No.1.1 freeze is preserved unchanged. The original Capital V5 H2/H3/H5 ML/R0 ranking includes confirmed BUY-fill price and duration as historical features and cannot be automatically used to choose a BUY before that fill. This alternative uses a strictly PRE-BUY First Entry score/threshold ratio for deterministic **research ordering only**; there is no claim it reproduces, improves, or replaces the Frozen R0 rank or its historic 20-day returns.

Input: an observation frame with timezone-bearing source/observed/known timestamps, a First Entry candidate and separately observed State9 Primary/market reference, plus the existing signed private Ownership baseline. Each candidate must reference its complete observation trio; excluded PULLBACK or SHARP_DROP never enters selection, unknown State remains unavailable, personal symbols are protected, 100-share lot is retained and new BUY intent after 15:20 is excluded. No future fill timing/price may appear as a purported pre-buy feature. The input batch is SYNTHETIC_OFFLINE_ONLY pending a genuine native event producer. The ratio must not be described as Frozen Capital ML, expected returns or a certified BUY signal.

This code does not simulate broker prices or submit orders. Next isolated stage adds fill-vs-intent order timing, unique IDs, cash and MAX3 in a synthetic account state machine; the actual RSS order connection and source arrival times remain unverified. Test performance on independent, precommitted forward periods before considering replacement promotion.

No user-side additional manual permission. Final intended human trade permission remains Excel RSS order ON/OFF after full real native and broker certification. productionReady=false, no real orders, no main/Frozen change.
