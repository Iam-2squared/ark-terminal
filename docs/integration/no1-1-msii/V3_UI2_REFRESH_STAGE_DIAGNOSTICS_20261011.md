# No.1.1 UI2 READ ONLY automatic refresh diagnostic — 2026-10-11

**Status: diagnostic-only change; not live deployment certification.**

Actual Windows UI2 SYSTEM screenshot shows Source Schema VALID, RSS Safety LOCKED, Ownership AVAILABLE, but Source STALE at around 283.6 seconds, Refresh Loop ERROR with READ_ONLY_REFRESH_FAILED, Runtime Safety BLOCKED, and all mutations FALSE. Initial V3 capture/Capital/Ownership and UI2 localhost launch passed. Repeated GET 200 merely proves the web endpoint is responding, not the underlying source refresh.

The Python UI2 server previously hid every subprocess failure behind one generic code. The approved read-only PowerShell preview now outputs exactly one fixed diagnostic phase on a failing run: PREFLIGHT, CAPTURE_GATE, CAPITAL_REPORT, SAFETY_LEDGER, MODEL_EXPORT, MODEL_VERIFY or MODEL_COMMIT. The Python RefreshLoop reads only one exact whitelisted marker, never forwarding any raw stdout, stderr, account figures, symbols, paths, exception texts or stack traces to browser/UI. A missing/ambiguous marker remains READ_ONLY_REFRESH_FAILED. A failed refresh remains BLOCKED; no stale fallback, no changes to 30-second Gate, no Safety reset, no order functions.

The root failure category is not yet known until the user runs the PC on this candidate with the desktop UI2 READ ONLY launcher. After successful offline CI and Windows launch, observe the UI SYSTEM view after 60-90 seconds. Report only the marker displayed in Refresh Loop. If CAPTURE_GATE, investigate the nested COM/capture/Capital issue privately. The Safety latch's separate reasons remain private and are not cleared.

Original No.1.1 Freeze, Ownership baseline, Excel workbook, MarketSpeed II, local broker source, main and PR draft state remain untouched. Actual brokerage feed-arrival timestamp and native strategy/order execution are not certified. Excel RSS order permission remains OFF.
