# Phase57 EXIT — 20-Session Path Diagnostic / Immediate Adverse Taxonomy

Status: **DEVELOPMENT_DIAGNOSTIC_ONLY / NON_PROSPECTIVE**

Source: completed 20-session artifact from PR #581, workflow run `34541503697`.
No new historical sessions were opened for this analysis. Frozen Selector / MSH-Entry / EXIT v3 / EXIT v4 are unchanged.

## Executive result

The completed 35 paired trades support the earlier finding that Immediate Adverse is common, but the deeper breakdown changes the interpretation of v3 vs v4:

- Immediate Adverse: **28 / 35 = 80.0%**
- Of the 24 Immediate-Adverse trades with a complete +6-bar close label:
  - recovered by +6 close: **14**
  - still loser at +6 close: **10**
- In the Immediate-Adverse cohort itself, **v3 slightly outperformed v4** on average trade and PF.
- v4's overall advantage over v3 is not a broad improvement across trades:
  - identical outcome: **30 / 35**
  - v4 better: **2 / 35**
  - v4 worse: **3 / 35**
  - positive v4-v3 deltas: **+14.543 percentage points**
  - negative deltas: **-8.158 percentage points**
  - net: **+6.385 percentage points**

Therefore the current evidence does **not** support the statement that v4 is generally better at tolerating Immediate Adverse. Its aggregate advantage is concentrated in a small set of trades.

## Immediate-Adverse subset

| Arm | N | Avg trade | Median | Win rate | PF |
|---|---:|---:|---:|---:|---:|
| Fixed12 | 28 | +1.492% | -0.206% | 46.43% | 1.846 |
| Session-End | 28 | +3.402% | +1.050% | 53.57% | 2.751 |
| v3 | 28 | **+3.481%** | -0.241% | 46.43% | **3.354** |
| v4 | 28 | +3.327% | -0.290% | 46.43% | 3.179 |

This is descriptive only. N=28 is too small for a promotion claim.

## +6 recovered vs +6 loser taxonomy

Among Immediate-Adverse trades with a complete +6 close label:

### Recovered by +6 close — N=14

| Arm | Avg trade | Median | Win rate | PF |
|---|---:|---:|---:|---:|
| Fixed12 | +5.681% | +3.282% | 71.43% | 11.458 |
| Session-End | +8.691% | +8.938% | 78.57% | 16.469 |
| v3 | +8.253% | +7.203% | 71.43% | 37.035 |
| v4 | +8.256% | +6.844% | 71.43% | 37.047 |

v3 and v4 are effectively identical on this subgroup.

### Still loser at +6 close — N=10

| Arm | Avg trade | Median | Win rate | PF |
|---|---:|---:|---:|---:|
| Fixed12 | -3.865% | -2.091% | 10.00% | 0.017 |
| Session-End | -3.516% | -3.943% | 20.00% | 0.202 |
| v3 | **-2.682%** | **-1.836%** | 10.00% | **0.249** |
| v4 | -3.117% | -1.960% | 10.00% | 0.160 |

On the current +6-loser subgroup, v3 is better than v4. This is the opposite of a general claim that v4 has superior adverse handling.

## Descriptive Healthy-Pullback vs Failure separators

The following uses only the 24 Immediate-Adverse trades with complete +6 labels. These are **in-sample descriptive statistics**, not a trained classifier and not frozen thresholds.

| Candidate state | Recovered mean / median | +6 loser mean / median | In-sample AUC |
|---|---|---|---:|
| first-bar directional close | +79.1 / +151.5 bps | -89.5 / -56.2 bps | **0.750** |
| first-bar favorable excursion | 196.3 / 202.2 bps | 107.3 / 65.4 bps | **0.700** |
| Hybrid rank | 7.86 / 7 | 12.40 / 12 | 0.304 (lower is better; separation 0.696) |
| Hybrid score | 0.612 / 0.609 | 0.598 / 0.585 | 0.664 |
| entry RVOL5 | 2.98 / 1.78 | 2.23 / 1.33 | 0.650 |
| first-bar MAE | 139.3 / 98.2 bps | 180.3 / 134.0 bps | 0.400 |
| post-first-bar directional VWAP distance | -3.998 / -4.109% | -4.710 / -4.145% | 0.571 |
| first-bar volume / prior-5 mean volume | 1.423 / 1.275 | 1.477 / 1.277 | **0.521** |

### Interpretation

The strongest descriptive separation is currently in the **first bar's realized directional close and favorable excursion**, followed by Hybrid rank/score.

The current sample does **not** support assigning strong fixed weights to first-bar volume ratio or post-first-bar VWAP distance. In particular, the proposed ad-hoc `VWAP 40% / Volume 25% / Recovery 25% / MFE 10%` Health Score is not justified by this evidence.

No Health Score or threshold is frozen from these 24 trades.

## v4 vs v3 difference concentration

v3 and v4 produced identical net returns on **30/35** trades. Only five trades explain every difference.

### v4 better than v3

| Date | Symbol | Side | v3 | v4 | Delta | v3 bars | v4 bars | Key difference |
|---|---|---|---:|---:|---:|---:|---:|---|
| 2026-09-01 | 4598.T | LONG | +6.820% | +17.507% | **+10.687%** | 4 | 48 | v3 winner-protection exit; v4 held to session end |
| 2026-09-03 | 4052.T | LONG | +7.276% | +11.133% | **+3.856%** | 6 | 41 | v3 winner-protection exit; v4 held to session end |

Both large v4 wins are LONG trades. One had Immediate Adverse and recovered; one did not have Immediate Adverse.

### v4 worse than v3

| Date | Symbol | Side | v3 | v4 | Delta | Key difference |
|---|---|---|---:|---:|---:|---|
| 2026-08-24 | 593A.T | SHORT | -0.304% | -1.660% | -1.356% | v3 loser rescue exited earlier |
| 2026-08-21 | 4833.T | LONG | +8.905% | +5.920% | -2.985% | v3 winner-protection exit beat later v4/session-end |
| 2026-08-21 | 6085.T | SHORT | +9.874% | +6.057% | -3.817% | v3 winner-protection exit beat later v4/session-end |

This suggests the current v4-v3 difference is primarily about **whether v3 winner-protection / loser-rescue exits should be overridden**, not a general improvement in Immediate-Adverse tolerance.

## Revised research conclusion

1. **Keep v3 and v4 frozen as baselines.**
2. Do **not** claim v4 has superior adverse handling from this sample.
3. Do **not** fit a weighted Health Score on these 24 labeled adverse trades.
4. Use the current 35 trades only for feature / failure-taxonomy hypothesis generation.
5. The highest-value next validation question is:
   - can first-bar path information plus pre-entry Hybrid state distinguish healthy adverse from structural failure on a new, untouched Development/Validation block?
6. Separately validate the v3 winner-protection override question, because all v4-v3 aggregate advantage is concentrated in five differing trades.

## Pre-registered next candidate state family

No coefficients or thresholds are frozen. The candidate family for the next untouched block is limited to:

- first-bar directional close return
- first-bar favorable excursion
- first-bar adverse excursion
- Hybrid rank
- Hybrid score
- entry directional VWAP distance
- entry RVOL5

The next block should test these as diagnostics first. New features, weights, and thresholds must not be added after seeing its outcomes.

## Safety / scope

- No new session outcomes opened.
- No Selector / Entry / v3 / v4 changes.
- No main changes.
- No merge / Ready / promotion.
- Research / shadow only.
