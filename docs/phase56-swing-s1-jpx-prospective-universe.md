# Phase56 Swing S1 — JPX Prospective Universe

Swing S1 starts the migration from the old five-symbol Phase56 measurement setup to a point-in-time JPX-wide Swing research universe.

It reuses the existing P25 cross-sectional opportunity selector, but uses the dedicated `SWING` score rather than the Day score. The completed overnight screener snapshot must be frozen before 08:50 JST and must contain at least 3,000 point-in-time eligible JPX domestic names with rows no older than 12 hours.

The frozen record preserves five memberships for later common-window comparison:

- `SWING_FIXED_5`
- `SWING_OLD_FIXED_30`
- `SWING_DYNAMIC_30`
- `SWING_DYNAMIC_40`
- `SWING_DYNAMIC_50`

Dynamic30/40/50 are nested prefixes of one direction-agnostic pre-outcome Swing rank. The current outer OOS may not choose the universe size or horizon. Future outcome fields, realized returns and winner labels are excluded from the snapshot identity and do not affect ranking.

The Swing rank emphasizes Discovery conviction, Technical conviction, confidence and quality, with volume-ratio and turnover support. A maximum of four names per sector is enforced.

This part intentionally does **not** alter the currently scheduled Day overnight workflow immediately before its first real prospective cycle. The Swing freezer is implemented and testable in isolation first; workflow reuse of the same completed JPX snapshot can be wired after the Day capture path has demonstrated one clean real cycle. This avoids duplicating a ~3,700-symbol scan and avoids risking the first Day evidence lineage.

Routine Swing research does not require MARKETSPEED II, Excel, board, Tick or Microstructure. Those remain separate later verification/optional research surfaces.

No execution, broker/Excel/RSS order write, paper/live trading, current-OOS Dynamic N selection, current-OOS horizon selection, threshold search, post-hoc symbol filtering, automatic promotion, production update or fresh-holdout consumption is enabled.

CI green validates implementation integrity only. Swing performance has not improved merely because this universe freezer exists; the next Swing parts must freeze horizon semantics and run proper prospective/walk-forward OOS evaluation.
