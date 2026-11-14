# Phase57 - R20 full observation census independent audit R22

Date: 2026-09-25 JST  
Latest HEAD at audit: `ab5e68a26e628507f765ff5dc05bbffbe574a5df`  
Artifact execution HEAD: `db423414ef6529829e883c915954fb51a95a8668`  
Status: **R20_FULL_OBSERVATION_CENSUS_INDEPENDENT_AUDIT_PASS_NOT_EXIT_PERFORMANCE_PASS**

## Scope and immutable receipt

GitHub Actions run `36128852207` (`Phase57 EXIT Observation Checkpoints R20`)
completed successfully. Artifact `10862675162`,
`phase57-exit-checkpoints-r20-36128852207`, is 195,826,846 bytes. Its locally
recomputed ZIP SHA-256 is
`6019809ca4ac9793c5a34ec1c894580c52ffea5074b6ee0ee8e593d10ef12b40`,
identical to the GitHub artifact digest. The artifact expires after the recorded
30-day retention period; this append-only receipt preserves the immutable hashes
and counts, not the 195 MB payload.

The run-a manifest SHA-256 is
`98036d1133b0d93aa4c6e47d598ffd4a60d1f7021474f569c3a2ba24021e2b3b`.
Independent verification recomputed every hash in both manifests: all 61
manifested files in run A and run B are byte-identical. The 58 checkpoint streams,
coverage, Entry envelopes and the 476-column registry inventory all match.

## Population and identity audit

Both frozen Entry arms retain exactly 2,155 unique Opportunity IDs and exactly
the same set as the pinned signal-census protocol. The sorted ID-set SHA-256 for
both arms is
`ff2d0ea4f8ee03337e10910e908d41e48321c7d335c834ab1f9aa4de60255a60`.
There are 58 Opportunity-bearing sessions, 2025-05-30 through 2025-08-25.

| Entry arm | Population | Fill | No Entry | Checkpoints | Fresh current close | Missing current close | Complete owned prefix |
|---|---:|---:|---:|---:|---:|---:|---:|
| IMMEDIATE | 2,155 | 1,963 | 192 | 345,893 | 220,364 (63.71%) | 125,529 (36.29%) | 65,266 (18.87%) |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | 2,155 | 1,885 | 270 | 310,354 | 198,591 (63.99%) | 111,763 (36.01%) | 55,672 (17.94%) |
| Total observations | - | - | - | 656,247 | 418,955 | 237,292 | 120,938 |

Scheduled checkpoints are counted from each preserved Entry time, not from
available candles. Missing bars therefore remain in the denominator. A stale
last observation is not a fresh current price, a no-trade certificate, zero
volume, a fabricated fill or a complete owned path.

## Entry-time State-v3 distribution

| State | IMMEDIATE | ALL_MATERIAL R1 |
|---|---:|---:|
| DROP | 1,261 | 1,004 |
| PULLBACK | 287 | 199 |
| REBOUND | 179 | 366 |
| RISE | 150 | 226 |
| RANGE | 50 | 75 |
| SHARP_DROP | 25 | 6 |
| SHARP_RISE | 6 | 5 |
| DROP_STOP | 5 | 4 |

IMMEDIATE Entry-time State quality is 703 OK / 1,260 DEGRADED; ALL_MATERIAL
R1 is 612 OK / 1,273 DEGRADED. Across sequential checkpoints, State quality is
25.58% OK for IMMEDIATE and 25.06% OK for R1. State labels therefore remain
usable only together with quality, coverage and missingness; the audit does not
turn a DEGRADED state into a reliable state.

The distribution directly confirms the controlling thesis: many frozen Entries
begin in DROP/PULLBACK/REBOUND. A NEW EXIT may not equate a falling price or DROP
label with automatic thesis failure.

## Six Timing Signals and UNKNOWN

All six signal counters reconcile exactly to each arm's checkpoint count.
UNKNOWN rates are large and must remain tri-state:

| Signal | IMMEDIATE UNKNOWN | R1 UNKNOWN |
|---|---:|---:|
| BREAKOUT | 300,093 (86.76%) | 269,698 (86.90%) |
| COMPRESSION_EXPANSION | 245,481 (70.97%) | 222,064 (71.55%) |
| CONTINUATION | 234,652 (67.84%) | 209,944 (67.65%) |
| HIGHER_LOW | 265,089 (76.64%) | 239,871 (77.29%) |
| LOWER_WICK | 234,037 (67.66%) | 211,197 (68.05%) |
| RECLAIM | 202,535 (58.55%) | 179,530 (57.85%) |

UNKNOWN is not FALSE, and TRUE-to-UNKNOWN is not disappearance or failure.
Candidate research may not select only complete or profitable signal histories.

## Causality and isolation audit

All 34 mandatory synthetic and actual canonical-producer tests passed. They
include direct State/Signal producer parity, future-suffix mutation invariance,
knownAt/bar-end rejection, lunch reset, Entry-minute ownership, missingness,
tri-state preservation and repeated-run byte identity. The flattened decision
field inventory contains no future State/pivot, final PnL, oracle ordered High,
post-Entry best High, expected future missingness or EXIT outcome key.

The historical availability semantics remain
`HISTORICAL_BAR_END_PROXY_NOT_PROVIDER_PUBLICATION_TIME`. This establishes a
causal historical prefix, not live publication latency or executable readiness.

## Pattern-v2 inventory boundary

The exact canonical registry has 476 unique columns and SHA-256
`efcbcaf4c4024679dc5f6e7881dcccc7c0186361b6bd469b7d3a5e6a5421e8eb`.
R20 intentionally admitted zero columns: 443 intraday-prefix columns, three
Frozen Selector-context columns and 30 prior-daily-dependent columns were still
pending EXIT-NOW admission. R22 does not silently promote them. Their final
column-level classification belongs to the next append-only checkpoint.

## Exposure, Safety and interpretation

- Provider requests: 0.
- New Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective opens: 0.
- NEW EXIT model fits: 0.
- NEW EXIT candidate policy evaluations: 0.
- Fixed12 / Candidate A invocations: 0.
- Safety9: all false.
- Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`: unchanged.

This is a full observation-substrate PASS only. It is not an EXIT policy,
performance result, candidate winner, Capital result, Fresh/OOS claim or
production authorization.

Machine-readable receipt:
`R20_FULL_CENSUS_AUDIT_R22.json`.
