# Entry Timing Signal Census v1 — precommit

This is a descriptive, already-exposed Development census, not model training,
an OOS test, executable profit, or an Entry freeze. Exactly 2,155 immutable IDs
from the Entry v2 evaluation are retained. Read only their archived paths and
their previous available session; no Dictionary fields enter decision payloads.
All nine trading/write/promotion flags are false. No provider requests.

## Clock, observations and availability

The archive uses bar-start minute timestamps. A regular bar at m becomes known
at m+1, so decision t receives only m<t. An event confirmed by the bar starting
10:04 has availability timestamp 10:05, never backdated to its pivot low.
Auction/endpoint rows at 11:30, 15:00 (old calendar) or 15:30 are excluded from
decision features; future evaluator archive remains unchanged. Decision census
runs at every closed continuous-minute endpoint after selection through continuous
session end, including 11:30/15:00/15:25 when a new closed bar exists. Missing
scheduled slots are retained as insufficient observations. No afternoon state
inherits an unclosed/missing afternoon quote from the morning. Local windows and
swings reset at lunch. Whole-day observed VWAP carries across lunch.

The comparison's executable decision grid is exactly the inherited v2 grid:
regular minutes 09:00–11:29 and 12:30–14:59 before 2024-11-05, thereafter
12:30–15:24; excludes 09:00 and 12:30, maximum delay 30 active minutes.
No overnight continuation. Active time excludes lunch. Terminal close/auction
is not an invented fill. Zero-grid opportunities retain SESSION_BOUNDARY.

Unless specified otherwise, a price window is available only if every expected
1m OHLC bar exists in the current half-session. No forward fill, zero-volume
imputation, interpolated quote or bridging across gaps. Signal booleans are
true/false/null (insufficient); three-valued OR is true if any true, null if no
true and any unknown, otherwise false. Every family exposes Event, State and
Context separately. Zero-range wick ratios are null; zero denominators are null.

VWAP is sum(actual Va)/sum(actual Vo) over observed regular bars since 09:00.
It is explicitly an OBSERVED VWAP, not certified official/full-session VWAP.
Require at least 80% observed expected closed regular slots and positive volume;
save exact coverage and observed rows. Never treat a missing minute as no-trade.
VWAP slope = 100*(VWAP(t)/VWAP(t-3)-1), requiring both endpoints available.
Previous-day observed high/low require previousSession to be the actual previous
trading date, not merely the previous archived date. Record prior coverage;
use observed level with >=80% expected continuous slots, never certify full-day
extreme when source is incomplete. Opening Range is the first 15 regular bars
09:00–09:14, only usable at/after 09:15 and only if all 15 are present. There is
no afternoon opening-range reset. Local resistance = max H of preceding 10
closed bars excluding the signal bar; local support = min L of that same window.

## Six fixed hypotheses (no sweep)

All percentage thresholds below are percentage points, not fractions.

1. **CONTINUATION**: State true when C>observed VWAP, 3m VWAP slope>0,
   return C(t-1)/C(t-4)-1 >=0.10%, distance below max H of last 5 bars <=0.50%,
   and last 3 bars have strictly increasing highs AND strictly increasing lows.
   Event = State becomes true relative to immediately preceding complete closed
   bar; previous State unknown makes Event unknown. State alone triggers B/E,
   including at Selector time. Context records recent return, drawdown and
   observed move versus Selector, without future path labels.
2. **BREAKOUT**: Event = previous close <= fixed level < current close for
   any preceding-10 high, previous-day observed high, completed Opening Range
   high. Both crossing closes must be consecutive within the half-session.
   State = current close above any available level; it is not a fresh Event.
   Local resistance level excludes the current bar for both crossing operands.
3. **COMPRESSION_EXPANSION**: use 11 consecutive bars. Earlier five bars
   t-11..t-7: close/open rise >=0.20%. Consolidation five t-6..t-2:
   high-low envelope <=0.65 times earlier envelope; last consolidation close
   is <=0.75% below earlier high. Current bar t-1: close exceeds consolidation
   high, positive body, range >=1.50 times mean consolidation bar range.
   Event requires setup + expansion; State is the pre-expansion setup.
4. **HIGHER_LOW**: within the last 20 consecutive half-session bars, a pivot low
   at i is strictly below lows i-1 and i+1 and confirmed only at close of i+1.
   Last two confirmed pivots satisfy newer low>older low; max high in window
   before older low to that low falls >=0.20%; latest close>high of newer pivot
   bar. State true once all hold. Event true only on the new confirmed pivot
   bar or the first consecutive close crossing above that pivot bar high.
   No pivot timestamp can serve as the signal timestamp.
5. **LOWER_WICK**: previous bar t-2 has (min(O,C)-L)/(H-L)>=0.50 and
   (C-L)/(H-L)>=0.65; preceding three bars close(t-3)/open(t-5)-1<=-0.20%.
   Current closed bar t-1 confirms C>wick bar H and L>=wick bar L.
   Event true only at this confirmation. State separately reports whether the
   current closed bar is an unconfirmed wick under the same decline definition.
6. **RECLAIM**: Event is crossing from <= to > observed VWAP (each close uses
   its contemporaneous VWAP) OR previous-day observed low OR completed OR low.
   Level crossings use consecutive closed bars. State = above observed VWAP
   (null if unavailable), never mistaken for reclaim. Context distinguishes
   previous below-VWAP, recent decline and shallow pullback.

All families share causal price/context values. Context is descriptive, not a
second filter: recent returns 1/3/5/10m, pullback from preceding observed high,
VWAP position/slope, coverage, preceding decline, and source-level availability.
We do not use symbol/rank/score to re-rank or re-filter.

## Volume / Trading Value

For each window 1/3/5/10m save actual sum Vo and Va, current/preceding equal-window
ratio (acceleration), and current/previous-session identical clock-slot ratio.
Both ratio windows require every expected slot and positive denominator;
otherwise null with coverage counts. Relative-to-previous-day is a one-day
same-time proxy, not a multi-day climatology. Previous-day unavailability remains
explicit. Save consolidation five/earlier five activity ratio and expansion
bar/mean consolidation bar activity ratio for compression; wick confirmation
bar/wick bar activity ratio for wick; these remain context and never gate BUY.
Predeclared descriptive strata for 3m volume/value acceleration and relative
volume/value: <0.8, [0.8,1.2), >=1.2, UNKNOWN. No extra indicator sweep.

## Six paired arms / no signal rejection

A Immediate+same retry. B first Continuation State. C first Breakout or
Compression Event. D first Higher-low, Wick-confirmation or Reclaim Event.
E first of B/C/D. F deadline-only Fallback. A-F retain all IDs.

For B-F the fallback target is 10 active minutes, clipped to last available
scheduled comparison decision if session ends sooner. First decision at/after
target initiates BUY attempt regardless of signal/quality. Once triggered, BUY
intent latches; later missing/weak signals cannot cancel it. Freshness/execution
unavailability is recorded separately. Continue retry every comparison minute
through common Selector+30-active-minute deadline, clipped at session boundary.
Reference must satisfy the unchanged v2 freshness (<=5 wall minutes, same
half-session); actual fill requires the next bar's observed Open at decision t,
with the unchanged +5bps entry convention. This is a historical fill proxy, not
a guarantee of liquidity, tradability or executable volume. Unknown absence
is MISSING_SOURCE_UNCLASSIFIED, not an invented halt or no-trade diagnosis.
F can retain a pending attempt even if its reference is unavailable. No signals
and all-unavailable signals both reach fallback, with separate observation status.

## Evaluation (labels never in detector/replay decisions)

Save per-minute causal rows, first per-family occurrence in both full census and
comparison window, observed=false/null counts, opportunity-level records and all
arm attempts including missing data. Success/failure partitions use each frozen
Selector session-end +1/+2/+3/+4/+5 label. Unknown future remains a separate
partition; no-signal-but-partial coverage is not certified signal absence.

For all six arms: decision delay, price, paired price improvement 100*(1-P/P_A),
waiting observed max H versus Immediate price and close rise at decision,
30/60 active-minute MFE/MAE/MaxDD (confirmed chronological AND adverse OHLC-order
bound), session-end MFE/MAE, remaining +1..+5 hits, capture using fixed original
Selector winner denominators, attempts, fills, retries, failures, all-pair status,
per-session and Selector time-of-day stability. Reuse immutable saved v2 outcome
labels at identical grid times; separately retain their coverage flags. Their
COMPLETE30/60 means legacy observed 5-minute-slot coverage, NOT every 1m present.
Additionally save strict all-1m horizon coverage. Unknown metrics remain null.
All-2,155 denominators and complete-pair conditional denominators must both be
visible. No zero-imputation of unfilled return or price; capture bounds retain
unknowns. Entry price gain alone is not profit and later +30m changes exit time.

Full-session ordered oracle: maximize 100*(H_j/L_i-1), j>i, on source observations
at/after Selector. Same-bar L/H ordering is never assumed. Keep oracle diagnostic
separate from causal recognition and from actual paired Entry changes. Range
Retention =100*(H_j/P_entry-1)/(H_j/L_i-1) using SAME oracle later high. Mark
no fill, insufficient full-session evaluation, denominator<=0, high at/before
Entry (including same bar), Entry before oracle low, and low at/before Entry
separately. Entry-before-low is evaluable but reported separately, never removed.
Do not clamp negative or >100 retention. Also save alternative best observed
high strictly later than Entry, clearly labeled DIFFERENT_HIGH diagnostic.

Predeclare DIRECT_CONTINUATION outcome anatomy = strict later +3% high before
any observed low <=Selector*(1-0.5%); if both first occur in same bar mark ambiguous;
if no +3 hit classify NO_3_HIT, if coverage missing UNKNOWN. Inherited
LOW_THEN_HIGH/HIGH_THEN_LOW remains evaluator-only. No future path to detector.

Save co-occurrence at same decision and any time in comparison window; Jaccard
and first-time agreement; session-cluster bootstrap (2,000, seed570921) for
session-equal paired price means, descriptive only. No candidate selected,
no extra thresholds added based on findings. Changes for coding defects must
be logged as corrections, retaining the original protocol and prior evidence.

Completion: focused causal tests, regression, two byte-identical regenerations,
raw evidence / plots / report. STOP with hypotheses and limitations; no training,
Dictionary, EXIT, Common Holdout, production update, freeze or order sending.
