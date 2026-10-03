# Legacy mechanics reuse matrix

JST: 2026-10-04T01:02:25.085104+09:00

**75% is a candidate-compatibility count:12 of16 listed components. Current engine migration completed0%; direct adoption of old numerical parameters0%.** Conditional candidates still need the current adapter/as-of/cost and null-valuation admission gates. This is not a code-line reuse estimate.

| Component | Reuse | Reason |
|---|---|---|
| causal event queue | YES_CANDIDATE | Price→EXIT→cash release→Entry; reference fills/known-at still need explicit admission. |
| deterministic candidate ordering | YES_CANDIDATE | timestamp then causal rank/score then symbol/identity; no future rank |
| 100-share lot quantization | YES_CANDIDATE | Current cash LONG-only round lots; existing Decimal quantity primitive |
| cash vs MTM equity separation | YES_CANDIDATE | Unrealized gains never become spendable cash; unknown marks remain null |
| cash-only LONG debit / credit | YES_CANDIDATE | Reuse actual cash mechanisms; current embedded5bps each side replaces old fee assumptions |
| same symbol no double-open | YES_CANDIDATE | Existing invariant |
| concurrent position cap | YES_CANDIDATE | Current MAX3/4/5 capacity distinct from budget divisor |
| causal score weighting | YES_CANDIDATE | Mechanism only; no old scorer inputs are fabricated |
| dynamic target utilization / reserve | YES_CANDIDATE | Mechanism only; numerical deployment curve not transferred |
| candidate equity cap mechanism | YES_CANDIDATE | Mechanism only; old45/35/25/15% not transferred |
| confirmed EXIT capital recycling | YES_CANDIDATE | Only confirmed source fill releases cash; unknown exit remains locked |
| append-only audit and outcome allowlist | YES_CANDIDATE | 18 inherited tests passed; current joint audit not claimed |
| old confidence/probability/Selector features | NO_DIRECT_REUSE | Missing or different current meaning; LEGACY_FEATURE_UNAVAILABLE |
| old score/rank/utilization numerical values | NO_DIRECT_REUSE | Former Entry/Selector calibration and side regime |
| SHORT / collateral accounting | NO_CURRENT_REUSE | Current LONG-only, cash-equity-only |
| legacy Adaptive reported realized PnL metric | NO_DIRECT_REUSE | One-trade supplemental audit proves entry cost double-subtracted from reported realized PnL; cash endpoint is separate |
