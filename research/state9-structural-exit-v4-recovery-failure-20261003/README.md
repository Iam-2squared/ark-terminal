# State9 Structural EXIT v4 — Recovery Failure evidence

Final selection: **V4_NOT_BETTER_KEEP_V3**. The fixed 2–<5% combined median condition failed. V3 remains the unchanged fallback and human EXIT Freeze candidate. This finite final EXIT improvement Work is complete. No adoption Freeze, rescue candidate, Re-entry, Capital or promotion follows.

Read [REPORT-ja.md](REPORT-ja.md) first. Its first table contains the required 2–<3 / 3–<4 / 4–<5 / combined2–<5 / >=5 protection comparison. It includes all20 mandatory answers. [SELECTION.json](SELECTION.json) records every unrounded fixed condition; [AUDIT_GATE_MAP.json](AUDIT_GATE_MAP.json) maps the24 required independent gates.

## Evidence

- PRIMARY_2_TO_5: 426 target watches, common filled417; >=5 common253 separately.
- EXCLUSIVE_ENTRY_HIGH_ALL, WINNER_GE5_PROTECTION, WINNER_GE5_EXIT_D.
- EXIT_D_PAIRED_DIAGNOSIS, EXIT_D_EXCLUSIVE, EXIT_D_V3_REASON, RECOVERY_FLOOR_MECHANICS, TARGET_CONCENTRATION_DIAGNOSTIC.
- TARGET_V3_EXIT_A: exact79 target baseline main-reversal cases; D preempts16.
- V4_EXIT_REASON and V4_EXIT_REASON_EXCLUSIVE: reason/bucket counts and economics.
- ALL_ENTRY_ECONOMICS, REPLAY_RECEIPT, EVALUATION_RECEIPT, INDEPENDENT_AUDIT.

Each table has JSON and CSV. Values unavailable/unresolved remain null; denominators accompany metrics. Group mean/median differences are distinct from per-entry paired statistics. Missed-upside percentages change in pp; pre-sell giveback is separate from post-sell upside. Opportunity remains the original strictly-later observed High, not an imputed complete session.

## Exact sources and implementation

V3 starting branch actual HEAD c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad. The original V2 private ZIP contains the exact full RC2 State9/Path trace and raw/fill/calendar dependencies reused by V3. The V3 ZIP contains saved V3 outcomes/paired rows and metadata and references the original trace rather than duplicating it. V4 reuses both immutable archives; no engine reconstruction or separate V3 Replay.

The four files frozen_v2_lifecycle.py, local_guard.py, reused_clock.py and reused_fill.py are exact whole-byte copies from V3 FINAL. Only recovery_floor.py adds a floor over the one V4 decision stream. Thresholds, main A/B, local guard C, PRE, arming, quality and execution are unchanged. Contract and nine decision/evaluation/selection files were fixed at S0 before primary Replay. RUN_ONCE receipt records exactly one primary V4 invocation. independent_audit.py is a distinct latch/ledger/fill/economics implementation and imports no primary decision/evaluator logic.

## Saved private output and review

Ark_State9_STRUCTURAL_EXIT_V4_RECOVERY_FAILURE_EVIDENCE_20261003_PRIVATE.zip contains new V4 decision metadata (1,600 files), replay/economics/paired/EXIT-D rows, receipts and RUN_ONCE. SHA256 ef58f731c76c2e9966997b86e1903faceb298ade472adfdf9849654f3cd950f4. No original trace or original V3 outcomes are duplicated. Public code/report/tables are in this directory and are not duplicated in that ZIP.

Immutable dependencies:

| Archive | SHA256 |
| --- | --- |
| Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip | 31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89 |
| Ark_State9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_20261003_PRIVATE.zip | 16cb53e6c986963f5a103e56c9f3fafad142548d7d9fd3286bb9e8c92e5a04b3 |

For read-only reproduction in an isolated workspace with this repository checkout as WORKSPACE/ark-terminal: restore_saved_sources.py accepts --workspace plus --v2-zip, --v3-zip and optionally --v4-zip. It verifies archive/component hashes and materializes existing bytes only. Restore saved V4 results for audit; do not rerun primary V4 Replay in this Work. Public Frozen authority in the inherited state9-structural-exit-v2-20261003 directory must be copied unchanged to WORKSPACE/inputs_v3/v2_public (IDENTITY_RECEIPT.json and FROZEN_SOURCE). Current code/report lives under this research folder; original full traces are restored to inputs_v3/v2_data and original V3 results to private_structural_v3. Then independent_audit.py may review the saved results without market data, fitting, rebuilding State9/Path or running V3.

Historical actual_known_at remains UNKNOWN; causal PASS uses the inherited assumed bar_end availability. Source completeness remains55/1600 (>=5:7/253). All ten safety flags are false, LONG-only/cash-equity-only. Policy variants1, primary Replay1; all model/teacher/search/provider/reconstruction/V3 or old EXIT Replay/Hard1/fixed stop/trailing/Re-entry/Capital/Portfolio/orders/main merge exposure0.

Three checkpoints only: V4_S0_START_AND_CONTRACT, V4_S1_REPLAY_AND_EVALUATION, V4_FINAL_AUDIT_AND_SELECTION. Commit result SHAs are verified by actual branch GET after commit; a checkpoint stores its actual basis HEAD, not a future self SHA. STOP.
