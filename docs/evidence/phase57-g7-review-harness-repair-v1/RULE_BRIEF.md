# G7 repaired display — fixed rule brief

This is a **post-review regression pack**, not a new blinded G7 run and not an independent reviewer result. It contains the original 36 ACTUAL cases, without the original eight injected controls. Do not rescore it as fresh evidence.

## Time first

All chart x-values, OHLC table labels, pivot times and missing markers use **interval END time**. Under the pinned G adapter, raw minute stamps are interval START times; `barEnd = rawStart + 1`.

For a checkpoint at 09:30, a 09:29-start/09:30-end bar may be used. The 09:30-start/09:31-end bar must not be used. A trustworthy knownAt later than the checkpoint also prevents admission. No independent historical knownAt has been established for these source archives: **HISTORICAL_CLOSED_RECONSTRUCTION**, not prospective availability parity.

Missing scheduled minutes do not move the checkpoint or cause forward filling. Price lines are disconnected across missing bars and recesses. Empty windows have no price observations, not a synthetic zero price.

## Axes do not all measure the same horizon

| Field | Fixed meaning | NOT its meaning |
|---|---|---|
| Direction | Sign of `last closed C - first O` in the latest five scheduled, consecutive closed 1m bars | Whole-session trend; sign since last pivot; a Scale-threshold signal |
| Structure | Active mechanical UP/DOWN/RANGE structure at t, including valid earlier-segment structure retained over a scheduled break | A requirement for four NEW local pivots at every checkpoint |
| Phase | Current mechanical leg/episode relationship to active structure | A prediction that a recovery will succeed |
| pivotSignature | Exact HIGH and LOW relations of the last four confirmed alternating local pivots | A new Structure class |
| Scale | Median complete five-minute True Ranges from the actual previous session | Today's volatility or the last plotted price change |

Direction requires latest5 COMPLETE but **does not require Scale**. An unavailable Scale alongside `Direction=DEFINED(UP)` is legal. A falling day may have a rising latest5 window. An exactly unchanged latest5 window may contain large moves internally.

Direction is exact: positive = UP; negative = DOWN; zero = UNCHANGED. There is no 1S requirement, tick tolerance or hysteresis for Direction.

## Scale and pivots

Scale uses at least six complete, scheduled, nonoverlapping five-minute blocks from the actual previous session, includes zero ranges in the median, and has no fallback. Block TR resets to H-L after missing blocks/recess. A zero median is SCALE_ZERO and has no usable Scale value. A Scale insufficiency is not itself an error in displaying valid same-day Direction.

Close-pivots require a >=1S reversal. Exact threshold qualifies; equal extreme retains the earliest timestamp. `effectiveAt` and `confirmedAt` are distinct. NOW may use only confirmedAt<=t pivots. Recess/missing gaps reset the local pivot sequence.

## Active UP/DOWN structure and witnesses

An alternating four-pivot sequence must include two HIGHs and two LOWs. Strictly higher HIGHs AND higher LOWs establish UP; both lower establish DOWN. These pairwise comparisons are strict raw-price comparisons, not an additional 1S relation threshold.

UP is invalidated by a close strictly below its protected LOW; DOWN by a close strictly above its protected HIGH. Equal touch is not invalidation. Missing scheduled bars break inheritance. A scheduled recess may preserve an earlier structure subject to the reopened close check.

The repaired card shows the structure's own `bornAt`, `confirmedAt`, protected level and origin pivot IDs, not just the last few local pivots. Local pivot count can be below four while a previously established active structure remains valid. The min/max close since structure birth is supporting context; the full causal sidecar contains the exact event sequence.

## Range has its own positive definition

A candidate uses 30 contiguous observed 1m bars divided into six five-minute blocks:

- envelope width >0 and <=2S;
- path efficiency <=1/3; the inherited zero-travel/null efficiency exception is retained;
- at least two distinct blocks touch within 0.25S of the upper bound;
- at least two distinct blocks touch within 0.25S of the lower bound.

It **does not require four pivots**. Candidate detection occurs every five bars from the continuous segment's beginning. Bounds are fixed at birth and are not redrawn around later prices. A close outside invalidates the range. An active trend can coexist with a local range; range does not erase trend.

The card's range witness contains the birth window, bound values, width, efficiency, touch-block indices and all 30 witness bar-end stamps. Do not infer the rule from a broad visual impression of the entire day.

## Status and absence

The card includes a **review-only projection** of the candidate status semantics; it is not the complete State v2 implementation/schema.

- DEFINED: evaluated. NONE or an empty phase set is a valid negative result.
- INSUFFICIENT: computation ran, but no active structure/range and fewer than four confirmed local pivots. This is not FORMING_UP/DOWN.
- NOT_EVALUATED: a required input failed. Reasons are per-axis; all observation flags are also shown independently.

Scale failure is not a Direction failure. Latest5 incompleteness is a Direction failure, but the original Structure engine can evaluate with a current bar and Scale using its gap/reset rules. Do not transfer one axis's prerequisites to every other axis.

`NONE + H_UP/L_DOWN` can explicitly describe a widening pivot geometry without inventing a broadening Structure label. The existence of a shape outside UP/DOWN/RANGE is not by itself a missing-vocabulary defect.

## Judge the representation, not whether the input is rich

Correctly displayed missing data is an input limitation, not a contradiction. A false COMPLETE label, an omitted required failure reason, a numeric Scale under an unavailable Scale status, a post-t close/pivot, or a contradiction with the exact fixed rules is a representation defect.

No profit, future outcome, decision recommendation or model accuracy is measured in this pack. Original G7 FAIL remains unchanged. Historical raw-basis / corporate-action / arrival-time limitations remain explicitly recorded.

## Immutable rule source

`mechanical-v1/reference.py` at `9a764e27086bf6bb1133c304b73c0027d1275760`.

SHA-256: `e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d`.

This repair loads those exact bytes and invokes `snapshot`, never `reference_at`. No market threshold is changed.
