# R52 decision coverage and finite continuation value design

Status: performance blind; all Development outcomes were already exposed in earlier studies. The original R50-A and Gen3 protocols and formal NO_SELECTION decisions remain unchanged. Basis `f5d3b9ab9a3dcc35d7609da31b9ba40638056158`; frozen R52 JSON SHA256 `64d30cf679939172e6aca0e9dc4212d7e663fea32114862289ca969009c4206e`.

| Question | Gen3 | Frozen R50-A | R52 two-candidate study |
|---|---|---|---|
| Label | Three separately thresholded sampled utilities | Zero-fit deterministic rules | Continuous, executable net continuation value H minus immediate S with same quantity/fee; UNKNOWN when either execution is unproven |
| Action | Three-head continuation/protection/deterioration policy | Armed +3% MFE, certified giveback and persistent deterioration | Single comparison of predicted value difference; every profit state has HOLD/SELL path, no +3% arm or DROP-only sell |
| Missing information | Sampled anchors can lack a label | Uncertified MFE or stale fact causes HOLD before ordinary Harvest | Label UNKNOWN on missing reference; runtime missing required current price or stale bar causes explicit fallback HOLD; optional prefix and Pattern features preserve missing flags |
| Counterfactual continuation | Sampled future utility from three fixed times | No comparison teacher | H: HOLD now, apply frozen R50-A starting next checkpoint, with its state advanced over all hypothetical owned checkpoints; S: exact next scheduled OPEN; no oracle best price |
| Market execution | Existing next OPEN and terminal contract | Existing next OPEN and terminal contract | Same immutable contract; intent never creates cash, missing OPEN re-evaluated and missing terminal locked |
| Integration | Single EXIT performance and old Gate | Formal NO_SELECTION; archived v3-B × R50-A control | All frozen Entry events replayed with exact saved Capital and policy-specific confirmed EXIT, even when single-position diagnostics fail |

Observed baseline decision coverage (IM/R1 combined): 29,458 funded-position checkpoints. IM had 8,654 checkpoints in negative current profit state; 6,765 were UNCERTIFIED_HOLD. IM 3–5% state had 940 checkpoints, of which 806 were UNCERTIFIED_HOLD. A checkpoint's final trade PnL in the per-row archive is repeated for diagnosis and must never be summed over checkpoints. One PnL per settled position is reported in the summary. Full immutable baseline rows are stored in three ordered, hash-pinned parts (`BASELINE_CHECKPOINTS_REASSEMBLE.json`).

Readiness geometry found all 819 IM and 795 R1 frozen Entry IDs with at least one checkpoint in the 24-session window. The source has 656,247 checkpoints across 3,848 frozen Entry/arm identities, including earlier training sessions. There are 274,417 checkpoints in the 24-session evaluation window. NOW-fresh plus exact next OPEN reference is available at 27,646 IM complete-prefix, 50,373 IM incomplete-prefix, 23,333 R1 complete-prefix, and 46,533 R1 incomplete-prefix checkpoints. These are technical availability counts, **not** teacher availability or candidate performance.

The support addendum fixes a minimum of 100 mature training labels per fold/arm before any estimator is fitted. It was appended to remedy a missing technical support number in the original protocol, with no candidate label or integrated performance inspected. Its SHA256 is `89b10fc56145bd0eb2821eb7fbc9fc768268df08c4745841b3a82173fd46effb`.

The control's exact archived Final Equity is `887131.0091250009994995`; the shorter handoff display rounded its low-order decimal digits. Both arms' old replay structures reproduced the archived ledgers byte for byte before R52 fitting. The experimental Development claim remains limited by outcome exposure, as-of bar-end publication proxy, and R1's unresolved auction unless independently resolved by an actual earlier lawful sale.
