# Ark Terminal Phase57 — EXIT Immediate Adverse Diagnostic

Date: 2026-09-11 JST  
Role: DEVELOPMENT_DIAGNOSTIC_ONLY / NON_PROSPECTIVE  
Source: PR #581 head `0eb9857bf61e8a6f31cda662cecc13a094e84fa3`, measurement run `34541503697`  
Measurement report SHA-256: `7533d488861be420f6edbfc5e2a62d9ca98de9719b56cacc1c67f5d4b319b803`  
Trades SHA-256: `02c78a819c5bcf74f8f1f2f02ee0750eb1358af8447c666d5168e82c3b5884a1`  
Diagnostic JSON SHA-256: `3fd6975e8ee9da531da2c14e29854de7283c5cafca50b736d326d868056a099e`

## Purpose

Use only the already-exposed 20-session diagnostic evidence to answer two questions before creating a new EXIT:

1. What separates an immediate-adverse trade that recovers by +6 bars from one that remains a loser?
2. Is the aggregate EXIT v4 > v3 result broad, or concentrated in a few trades?

No new sessions, protected data, validation/OOS, retuning, or promotion are used here.

## Immediate Adverse Cohort

- Paired trades: 35
- Immediate Adverse: 28 / 35 = 80.0%
- Immediate Adverse with complete +6 label: 24
- Recovered by +6 close: 14
- Remained loser by +6 close: 10

### Arm behavior inside all 28 Immediate Adverse trades

| Arm | Avg trade | Median | Win rate | PF | Mean holding bars | Early vs Fixed |
|---|---:|---:|---:|---:|---:|---:|
| Fixed12 | 1.492% | -0.206% | 46.4% | 1.846 | 10.89 | 0.0% |
| Session-End | 3.402% | 1.050% | 53.6% | 2.751 | 29.00 | 0.0% |
| v3 | 3.481% | -0.241% | 46.4% | 3.354 | 18.61 | 25.0% |
| v4 | 3.327% | -0.290% | 46.4% | 3.179 | 21.86 | 17.9% |

The core observation remains: adverse excursion itself is not a failure signal. v3/v4 improve average trade and PF on this cohort largely by allowing recovery time.

## Recovered-vs-Loser split at +6

### Recovered by +6 close — 14 trades

| Arm | Avg trade | Median | Win rate | Mean holding |
|---|---:|---:|---:|---:|
| Fixed12 | 5.681% | 3.282% | 71.4% | 11.50 |
| Session-End | 8.691% | 8.938% | 78.6% | 35.57 |
| v3 | 8.253% | 7.203% | 71.4% | 25.14 |
| v4 | 8.256% | 6.844% | 71.4% | 30.43 |

### Remained loser by +6 close — 10 trades

| Arm | Avg trade | Median | Win rate | Mean holding |
|---|---:|---:|---:|---:|
| Fixed12 | -3.865% | -2.091% | 10.0% | 12.00 |
| Session-End | -3.516% | -3.943% | 20.0% | 25.70 |
| v3 | -2.682% | -1.836% | 10.0% | 11.20 |
| v4 | -3.117% | -1.960% | 10.0% | 12.90 |

For the +6 losers, v3 reduced the average loss more than v4 in this sample: v3 -2.682% vs v4 -3.117%. This is the clearest remaining loser-control weakness for v4.

## First completed post-entry bar: strongest descriptive signal

The first post-entry 5-minute bar is already causal when it closes. Within the 24 complete +6 Immediate-Adverse trades:

| Natural diagnostic split | N | +6 recovered | +6 loser | Recovery rate |
|---|---:|---:|---:|---:|
| First-bar directional close > 0 | 12 | 10 | 2 | 83.3% |
| First-bar directional close <= 0 | 12 | 4 | 8 | 33.3% |
| First-bar MFE >= 1% | 15 | 11 | 4 | 73.3% |
| First-bar MFE < 1% | 9 | 3 | 6 | 33.3% |
| First-bar close > 0 AND MFE >= 1% | 10 | 10 | 0 | 100.0% |

Important: these are exposed-development diagnostics, not frozen rules. In particular, the 10/10 row must not be converted directly into a v5 threshold.

### Descriptive recovered-vs-loser separation

AUC below is only rank separation on these 24 exposed trades; it is **not** model performance or a significance claim.

| Feature | Recovered median | Loser median | Descriptive AUC (higher -> recovered) |
|---|---:|---:|---:|
| `t1CloseDirPct` | 1.5152 | -0.5615 | 0.750 |
| `t1MfePct` | 2.0223 | 0.6544 | 0.700 |
| `entry_hybridReciprocalRank` | 0.1429 | 0.0889 | 0.696 |
| `hybridScore` | 0.6088 | 0.5852 | 0.664 |
| `entry_directionalVwapDistancePct` | -5.6645 | -3.7597 | 0.350 |
| `entry_relativeVolume5` | 1.7802 | 1.3291 | 0.650 |
| `modelProb` | 0.6304 | 0.6257 | 0.650 |
| `entry_directionalMomentum3Pct` | -6.6657 | -5.4478 | 0.371 |
| `entry_directionalPullback6Pct` | -7.6941 | -6.1017 | 0.393 |
| `t1MaePct` | -0.9824 | -1.3398 | 0.600 |

The strongest observed separation is first-bar directional close, followed by first-bar MFE. Entry score/rank have weaker but visible separation. VWAP and volume do **not** yet justify the fixed-weight Health Score proposed in external review; the observed separation is not strong enough in this sample.

## v4 vs v3 concentration audit

Only 5 / 35 trades have different realized v3 and v4 returns. v4 is better in 2 and worse in 3.

| Date | Symbol | Dir | v4-v3 | v3 net | v4 net | v3 bars | v4 bars | v3 reason | v4 reason |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 2026-09-01 | 4598.T | LONG | +10.687% | +6.820% | +17.507% | 4 | 48 | V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION | SESSION_END |
| 2026-09-03 | 4052.T | LONG | +3.856% | +7.276% | +11.133% | 6 | 41 | V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION | SESSION_END |
| 2026-08-24 | 593A.T | SHORT | -1.356% | -0.304% | -1.660% | 3 | 12 | V3_LOSER_RESCUE_SHORT_HORIZON_EDGE_REJECTED | V4_CONFIRMED_DOWNSIDE_TRAJECTORY |
| 2026-08-21 | 4833.T | LONG | -2.985% | +8.905% | +5.920% | 18 | 26 | V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION | SESSION_END |
| 2026-08-21 | 6085.T | SHORT | -3.817% | +9.874% | +6.057% | 14 | 53 | V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION | SESSION_END |

Net aggregate v4-v3 difference across these five trades is +6.385 percentage points. The two positive deltas are both LONG trades where v3 fired `V3_WINNER_PROTECTION_CONFIRMED_EDGE_REJECTION` and v4 held to session end. The three negative deltas show that v4's extra patience is not uniformly beneficial.

Therefore **v4 > v3 is concentrated, not broad** in this diagnostic set.

## Interpretation

1. Immediate Adverse itself should not trigger EXIT. 80% of the sample experiences it.
2. The first *completed* post-entry bar is a much more promising causal discriminator than the mere presence of an adverse excursion.
3. v3/v4 perform well on recovered trades because they allow time. For the subgroup still losing at +6, v3 currently controls average loss better than v4.
4. The proposed new EXIT should focus on `healthy pullback vs structural failure`, but should not hard-code a Health Score from these 35 trades.
5. Current evidence supports carrying forward a **small candidate feature set**, not a fitted rule:
   - first-bar directional close return
   - first-bar MFE / MAE
   - frozen Hybrid rank / score
   - frozen MSH probability
   - entry directional VWAP distance (hypothesis only)
   - relative volume (hypothesis only)
6. VWAP reclaim, volume deterioration, and structural-break logic remain plausible, but this exposed sample does not yet prove they are useful.

## Next research contract

Keep v3/v4 frozen as baselines.

Before building v5:
- freeze the candidate causal feature definitions above,
- use current 20-session evidence only for hypothesis generation,
- test recovered-vs-failure discrimination on new development/validation data,
- do not tune weights or thresholds on these 35 trades,
- only after out-of-sample separation is observed, prototype Continuation-Value / Structural-Failure EXIT.

No main change, merge, auto-promotion, broker write, paper/live trading, or production update is authorized.
