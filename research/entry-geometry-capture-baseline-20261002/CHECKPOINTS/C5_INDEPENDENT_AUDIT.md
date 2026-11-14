# 💾 C5_INDEPENDENT_AUDIT

## checkpoint

C5

## saved_at_jst

2026-10-02T23:48:49.222400+09:00

## basis_head

895b7553fe24bb1e241ed217b78ba0c2439379ef

## previous_checkpoint_result_head

895b7553fe24bb1e241ed217b78ba0c2439379ef

## current_status

ENTRY_GEOMETRY_BASELINE_AUDIT_PASS

## completed_this_checkpoint

```json
[
  "Recomputed original saved evidence through Decimal ratios, streaming extrema, interval-clock durations and manual quantiles",
  "Verified 4,310 row identities, ordering, buckets, unknown denominators and canonical Capture against original scorecards",
  "Verified saved MFE/MAE against raw extrema and kept same-bar/strict-later semantics distinct"
]
```

## key_evidence

```json
{
  "opportunities": 2155,
  "arm_rows": 4310,
  "sessions": 58,
  "symbols": 950,
  "total_checks": 307655,
  "mismatch": 0,
  "absolute_tolerance_pct": 1e-08,
  "maximum_observed_absolute_error": 2.6297186650481308e-11,
  "lunch_crossing_checks": 1255,
  "fit": 0,
  "replay": 0,
  "provider": 0,
  "protected_open": 0
}
```

## blockers

```json
[]
```

## current_direction

Saved-evidence descriptive Entry Geometry; V6 closed STATE_R2_SIGNAL_NOT_REPLICATED; Hybrid next-spec only after integrity PASS

## next_step

C6 interpretation and PROPOSED_NOT_AUTHORIZED next-spec

## frozen_boundaries

```json
[
  "Selector / State9 RC2 / Path / targets unchanged",
  "No new Entry decisions / fit / Replay / provider",
  "No new partition exposure",
  "No main merge / force push / orders",
  "Fixed requested bucket edges",
  "R2 probabilities/ranks not promoted"
]
```

## exposure_and_budget

```json
{
  "new_entry_model_fits": 0,
  "state_model_fits": 0,
  "exit_model_fits": 0,
  "threshold_searches": 0,
  "new_policy_replays": 0,
  "provider_requests": 0,
  "Protected_open": 0,
  "Holdout_open": 0,
  "Validation_new_open": 0,
  "OOS_open": 0,
  "Prospective_open": 0,
  "orders": 0,
  "paper_trades": 0,
  "live_trades": 0,
  "main_merges": 0,
  "bootstrap": 0
}
```

## safety

```json
{
  "executionAllowed": false,
  "brokerWriteAllowed": false,
  "excelOrderWriteAllowed": false,
  "rssOrderFunctionAllowed": false,
  "liveTradingAllowed": false,
  "paperTradingAllowed": false,
  "automaticPromotionAllowed": false,
  "productionUpdateAllowed": false,
  "transmitted": false
}
```

## result_head

GitHub commit itself is authoritative; no future SHA predicted
