# Phase57 — NEW EXIT execution, evaluator and full scorecard contract R24

Date: 2026-09-25 JST  
Basis HEAD before this append-only checkpoint: `ab5e68a26e628507f765ff5dc05bbffbe574a5df`  
Status: **PRECOMMITTED_NO_CANDIDATE_REPLAY_OR_PERFORMANCE**

## Decision and execution geometry

1. A decision exists at every completed continuous 1-minute endpoint after the
   frozen Entry OPEN. For this 2025 cohort, bar starts are 09:00–11:29 and
   12:30–15:24; endpoints include 11:30 and 15:25.
2. Decision NOW may use only a bar with bar-start+1 <= NOW and knownAt <= NOW.
   The archive's bar-end timestamp remains a historical proxy, not live-latency proof.
3. An ordinary EXIT decision uses the exact next scheduled continuous-bar OPEN.
   Thus a decision at 11:30 refers to the 12:30 OPEN. There is no lunch bar,
   forward search, stale reference, last-close substitution or queued sell intent.
4. If that exact OPEN is absent, status is `MISSING_EXECUTION_REFERENCE`, there is
   no fill, and the policy is newly evaluated at the next checkpoint.
5. The 15:25 decision has no later continuous-bar OPEN. Every still-open position
   is forced to the exact endpoint-stamped 15:30 auction reference at minute 930.
   Overnight holding is prohibited.
6. A missing auction reference yields `UNRESOLVED_TERMINAL_EXIT` and censoring.
   It is not replaced by 15:25 close, a stale quote or a profitable/zero return.

The exact 2,155 allowlisted raw paths, SHA-256
`37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b`,
contain a minute-930 reference for 2,092 Opportunities; all 2,092 are single-price
OHLC auction rows. Sixty-three are missing and must remain unresolved if held to
terminal. This is availability census, not policy performance.

Active holding time counts scheduled continuous minutes and excludes lunch. Wall
time is NOW minus Entry minute and includes lunch. Both are reported. No Entry
30-minute deadline, Fixed12 cap or Candidate A +3/+1 rule is inherited.

## Ownership and price contract

- Entry at a frozen OPEN owns that Entry candle.
- At an EXIT OPEN, the EXIT candle's later High/Low is not owned.
- Owned running High/Low contains only completed owned bars strictly before EXIT.
- Equal running High ties use the latest confirmation time.
- Missing any expected owned bar makes certified peak giveback unavailable; the
  observed extrema may remain labeled observed-only.
- OHLC intrabar order is unknown. No High-before-Low or Low-before-High ownership
  is invented.
- A High after EXIT is missed opportunity/evaluator gap, never profit giveback.

Frozen Entry price already includes the original buy-side 5 bps assumption.
Gross Entry→Exit uses the raw exact exit reference against that effective Entry,
without charging Entry again. Primary net score subtracts 0.05 percentage points
of sell-side cost; 0.10 and 0.20 pp sell-cost stresses are mandatory. These cost
values are newly explicit here and are not inherited from an old EXIT policy.

Missing/no-action taxonomy remains distinct: `NO_ENTRY`, `NO_EXIT_INTENT`,
`MISSING_EXECUTION_REFERENCE`, `STALE_OBSERVATION_NOT_EXECUTION_REFERENCE`,
`NO_TRADE_NOT_PROVEN`, `INCOMPLETE_OWNED_PATH`, and
`UNRESOLVED_TERMINAL_EXIT`.

## Evaluator isolation and fixed geometry

`scripts/phase57_exit_capture_metrics_v1.py` remains evaluator-only and is not
imported by either the R20 observer, R23 feature adapter or R24 execution module.
Its dedicated R21 CI run `36130452793` passed all 24 synthetic arithmetic,
bucket-edge, horizon and ownership tests. Those are contract tests, not trades.

The canonical full-opportunity geometry source is
`measurement/opportunity-records.json.gz`, SHA-256
`4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e`.
The existing ordered scorecard implementation SHA-256 is
`878aeae3f41af43fbbbde1d00d96be61a709a514ce96457a79bf89a2b0fed6b5`.
The definition is the maximum observed ordered Low→strictly-later High from the
frozen Selector start through the same common session horizon, including the
endpoint-stamped auction when present. The evaluator's inclusive knowledge cutoff
is 930. A regular bar High is known at start+1; the endpoint-stamped auction is
explicitly known at 930, so a 15:30 terminal Exit does not misclassify its own
simultaneous auction price as a post-Exit High. It is retrospective and never a
decision input.

Keep these identities separate:

| Geometry | Meaning | Ownership |
|---|---|---|
| ordered Low→strictly-later High | canonical whole Opportunity and bucket | evaluator-only |
| Entry→same ordered High | upside from actual Entry to that same High | evaluator-only |
| Entry→post-Entry best High | best High strictly after Entry in same horizon | evaluator-only, separate High |
| Entry→actual Exit | resolved realized reference move | policy output after replay |
| Upmove Capture | Entry→Exit divided by positive Entry→High | evaluator-only ratio, unclipped |
| High→Exit gap | evaluator High minus Exit; may be after Exit | missed opportunity, not giveback |
| Owned Peak→Exit giveback | complete owned peak known by Exit minus Exit | owned profit retention |

Negative and >100% capture stay visible. Nonpositive denominators return null
with a reason. Missing geometry does not erase an otherwise valid Entry→Exit
return. No Entry and unresolved Exit never become zero-return trades.

## Six opportunity-size buckets reproduced

Using the exact source, definition and hash above—not an assumed carry-forward—
the canonical anatomy is:

| Ordered Low→strictly-later High | N |
|---|---:|
| <1% | 158 |
| 1–2% | 391 |
| 2–3% | 361 |
| 3–4% | 289 |
| 4–5% | 188 |
| >=5% | 666 |
| Not evaluable | 102 |

The 102 not evaluable are 63 full-session observation insufficient, 25
nonpositive ordered ranges and 14 insufficient ordered rows. Therefore the
historical IMMEDIATE `>=5%` N=666 is now reproduced under the same canonical
definition/source/horizon/hash. This reproduces anatomy only; no NEW EXIT result
has been computed. `fullSessionEvaluable` is the legacy canonical coverage flag,
not a new claim that every 1-minute slot is strictly complete.

## Full scorecard fixed before candidate performance

Every bucket, the not-evaluable stratum, each Entry arm separately, and the valid
common-case paired view must report:

| Group | Required output |
|---|---|
| Accounting | N, metric-specific evaluable N, missing N, censored N |
| Opportunity | Low→High mean/median; Entry→same-High mean/median; Entry→post-Entry-best-High mean/median |
| Realization | Entry→Exit gross/net mean/median; whole-opportunity and both upside-capture definitions |
| Gap/retention | both evaluator High→Exit gaps; certified Owned Peak→Exit giveback |
| Return/risk | net mean/median, PF, win rate, average win, average loss, p05, p10, worst |
| Time | active and wall holding time mean/median |
| Timing errors | early-exit opportunity cost and late-exit owned giveback |

Each metric carries its own eligible denominator. A common complete-case
denominator cannot be reused across metrics. PF is sum of positive net return
divided by absolute sum of negative net return, with zero denominator reported
null. Win means net return >0 among resolved Entry/Exit rows.

The paired view requires the same Opportunity ID, same geometry definition and
horizon, both Entry arms filled/resolved, and availability of the specific metric.
It reports pair N and within-pair `R1 - IMMEDIATE` deltas; unpaired rows cannot be
labeled paired.

## Three capabilities remain separate

- **Winner Continuation:** `>=5%` capture, early-exit opportunity cost and holding time.
- **Profit Retention:** certified owned-peak giveback and positive-trade retention.
- **Loss Containment:** p05, p10, worst and average loss.

Mean net return/PF remain required but cannot collapse these axes, and win rate
alone cannot select. A policy that clips large Opportunities to improve loss or
ignores catastrophic losses to preserve winners cannot automatically pass.

## Freeze, exposure and safety

Both Entry arms and Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`
remain unchanged. The 2,155 are outcome-exposed Development. No protected
partition or provider data was opened. Fixed12/Candidate A were not evaluated or
referenced as a comparator. Model fits and candidate performance inspections are
zero. Safety9 are all false; no execution, transmission, paper/live trading,
promotion or production update is authorized.
