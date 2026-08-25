# Phase57 P25 HOLD/EXIT Recovery R1-R2

This diagnostic freezes the failed five-session P25 Full Dynamic result and compares it against the same Fixed-Horizon trades plus the non-risk fallback semantics used by P24.7.

The diagnostic deliberately does **not** claim an exact replay of the P23.50 Dynamic Risk gate, because the persisted P25 session evidence does not itself prove the multi-session historical context required by the old P24.7 risk query for every current P25 symbol. It therefore fails closed rather than silently reconstructing history from a live provider.

The legacy-selective diagnostic permits only `STATE_AWARE_PROFIT_PROTECTION`; unconfirmed ATR hard-stop/chart-breakdown exits fall back to the original frozen horizon, matching the non-risk fallback logic documented in P24.7.

No Entry, model, universe, threshold, Dynamic-N, fair-cutoff, fresh holdout, or trading/write safety setting is changed. The five-session result is diagnostic-only and cannot be used for same-sample parameter tuning or winner selection.
