# Causal Entry State / Path Anatomy v1 — precommit

2026-09-21 JST. Base GitHub HEAD 8c6ae11ab9345630e917978f3c886e9c9baef41f.
This file is committed before any new Path/State outcome measurement. No threshold
search, model selection, Entry training, Dictionary, EXIT, capital change or promotion.
The existing Census protocol's exact 2,155 IDs, 144 Development date allowlist,
six signal definitions, quote/fill/retry semantics and nine false safety flags apply.
Existing evidence is immutable. Historical reconstruction is not independently
knownAt-certified PIT, and next-open +5bp fills are research proxies, not orders.

## Sources and missing semantics

Reuse pinned Census minute observations and Entry v2 compact raw paths, causal
quote flags, fill/outcome table. Restore existing encrypted Development archives
through the existing configured CI credential; no provider requests. Extract only
144 authorized intraday Development dates. Read daily pages for exact calendar
predecessors, never earlier substitute dates, never Common Holdout. Restore hash
and daily page response hashes are verified. No Dictionary values enter features.
Full observed previous-day 1m does not guarantee complete minutes.
Daily unavailable dates, security rows, invalid OHLC, nonpositive prices, missing
volume/value and corporate actions are explicit; no interpolation/forward fill.
Source-only coverage may be audited before outcomes, never tuned for performance.

## Recent Daily

At each decision date d, gather exactly D-5..D-1 from the exchange calendar in
ascending order. All dates < d. Corporate-action marked or invalid OHLC rows are
unavailable. Record per-lag status and source hashes. On each available bar:
body=(C-O)/O*100; upper=(H-max(O,C))/O*100; lower=(min(O,C)-L)/O*100;
close location=(C-L)/(H-L), null at zero range; range=(H-L)/O*100;
volume and trading value observed, not inferred from intraday.
For n=1,2,3,5, returnOCn=(C[D-1]/O[D-n]-1)*100 (explicitly n-session
open-to-close, NOT n-lag close-to-close). Optional D-6 allows conventional
returnCCn=(C[D-1]/C[D-1-n]-1)*100; absent predecessor => null.
Across complete five bars: each OHLC normalized to D-1 close, HH/HL/LH/LL
transition fractions over four pairs; consecutive close up/down transitions
(0..4); mean five ranges; ATR-like mean of four true ranges using previous close,
normalized by D-1 close; recent2/earlier3 range, volume, value ratios; last/first
volume/value ratios; D-1 close position in five-day H/L envelope. Previous-session
gap=O[D-1]/C[D-2]-1; today's gap only when observed 09:00 closed bar is available.
Current close distances to D-1 H/L/C and five-day H/L use only closed NOW price.
Missing five-day context remains in population and triggers no rejection.

## Continuous causal intraday state

Input API accepts only today's closed regular rows with start<t, previous actual
session rows, and prior daily feature context. Reject future rows at API boundary.
Strict contiguous lookbacks of 5,10,20 bars within current half-session (no lunch
bridge). Reference price is latest exact t-1 bar; missing => unknown state.
Five and ten minute return=(last C/first O-1)*100. On ten bars: efficiency=
abs(last C-first O)/(abs(first C-first O)+sum abs successive close differences)),
zero movement =>0; HH/HL/LH/LL pair fractions; direction-change count excludes
zero close differences; RV=std(log close returns)*100; range utilization=
sum abs close differences/(max H-min L), zero envelope =>null. Drawdown=
(max H-last C)/max H*100; peak age=t-1-earliest peak start. Recovery fraction=
(last C-min L)/(max H-min L), null zero. Close position same formula.
5/preceding5 envelope range, mean body, RV, volume/value contraction ratios;
ratios null for missing or nonpositive denominators. Compression duration is
consecutive known compression flag observations, reset at missing/lunch/session.
VWAP and its3m slope retain Census >=80% observed expected-volume construction.
Time above VWAP: fraction of last10 observed closes above their own causal VWAP,
null if any VWAP unavailable. Previous-day return/range/efficiency and observation
coverage are included; raw previous-day lookahead allowed only for actual d-1.
All six signals retain their original Event/State/Context and shared activity.

Scores in [0,1] are arithmetic means of four Boolean components, NOT calibrated
probabilities. Unknown component remains null; score requires all four:
- TREND: ret5>=0.10%; efficiency>=0.50; close>VWAP; HH and HL fractions>=0.5.
- PULLBACK: drawdown>=0.30%; ret5<0; peak age>=3; close>previous observed day open.
- COMPRESSION: range5/prior5<=0.65; body ratio<=0.8; volume ratio<=0.8;
  value ratio<=0.8.
- CHOP: efficiency<=0.25; direction changes>=4; ten-bar range>=0.5%;
  close position between0.2 and0.8 inclusive.
- WEAKNESS: ret5<=-0.10%; close<VWAP; VWAP slope<0; LH and LL fractions>=0.5.
Daily integrated scores: if all five daily bars are available, TREND adds 0.10
when returnOC5>0 and daily HH/HL fractions>=0.5; WEAKNESS adds0.10 when returnOC5<0
and LH/LL>=0.5; PULLBACK adds0.10 when returnOC5>0 and ret5<0; COMPRESSION adds0.10
when daily range ratio<=0.8; CHOP adds0.10 when abs(returnOC5)<1. Clip at1.
Missing daily => unchanged intraday score with explicit DAILY_UNAVAILABLE marker.
Dominant state requires unique maximum>=0.50; ties=>MIXED; all unknown=>UNKNOWN;
otherwise UNRESOLVED. No mandatory assignment, no rejection. RECOVERY is separate
context: drawdown>=0.3 and ret5>0 and recovery fraction>=0.5. Save both daily-free
and integrated scores/states every scheduled closed minute through session end.

## Future Path 5+1 — evaluator ONLY

Use observed future regular/auction rows after selector, excluding already closed
endpoint auction at exact selector time per existing Census correction. Require
existing full-session evaluator availability, >=20 future rows, >=30 remaining
active minutes. Missing path=>MISSING_PATH_DATA; otherwise insufficient=>
INSUFFICIENT_OBSERVATION. These are not negative outcomes.
Measures: selector-based extrema/terminal return; ordered best low→STRICTLY later
high oracle; close-path efficiency; directional reversals at >=0.5% close-price
excursions (initial direction after0.5%, reverse after0.5% from running extreme).
Swing resets across missing minute and lunch; do not assume intrabar H/L order.
Predicates:
1 DIRECT: first observed +1% high occurs before first -0.5% low; same bar =>
order unknown, predicate false; terminal return>=0; close efficiency>=0.20.
2 RECOVERY: a low<=selector*0.995 strictly precedes a high>=that low*1.02,
and terminal close>=low*1.01 (any such chronological pair).
3 CONSOLIDATION: complete10-bar envelope<=0.6% of first open, followed within
next10 contiguous same-half-session bars by close>=envelopeHigh*1.003 and
that bar range>=1.5*mean consolidation bar range; terminal>=breakout close.
4 CHOP: >=4 confirmed directional reversals and close efficiency<=0.30.
5 WEAKNESS: terminal<=selector*0.99, at least60% observed closes<selector,
and maximum ordered recovery from any low to later high<2%.
Single predicate => that class. Multiple predicates: CHOP dominates if>=6
reversals and efficiency<=0.15; otherwise TRUE_MIXED_PATH (do not choose winner
by returns). No predicates=>NO_DOMINANT_PATH. Save all predicate values,
same-bar ambiguity flag, observations/coverage, and Path6 reasons. No count target.

## Identification diagnostics

Checkpoints T+0/5/10/15/30 active minutes; require exact scheduled observation,
never nearest future observation. Report missing checkpoints, all6-class imbalance,
per-class feature distributions, standardized mean differences one-v-rest (pooled
SD; null zero/insufficient), state-v-path confusion and session/time-of-day tables.
One diagnostic nearest-centroid classifier only: first chronological half of the
58 nonempty evaluation sessions fit; second half diagnostic test. Fit medians,
means/SD only on fit; missing median-imputed WITH missing indicators (not invented
observations); all-null features excluded. Equal-prior Euclidean centroids,
lexical tie resolution. No hyperparameters/search. Two paired feature sets:
intraday only vs same+Daily. Use same IDs and labels including Path6; report
accuracy, balanced accuracy, confusion and missing coverage. This is NOT Entry
training, NOT independent OOS, and later checkpoints partly reveal the answer
path; no early predictability claim from late recognition. Identify at each
checkpoint, not cherry-picked earliest correctness per case.

## Fixed timing comparisons

A Immediate + same retry, F no signal/fixed10 active-minute fallback.
B early: BUY if integrated TREND score>=0.75 or original CONTINUATION trigger;
otherwise WAIT and re-evaluate.
C State-appropriate: TREND=>CONTINUATION or BREAKOUT; PULLBACK=>HIGHER_LOW,
LOWER_WICK,RECLAIM; COMPRESSION=>COMPRESSION_EXPANSION,BREAKOUT;
CHOP=>HIGHER_LOW or RECLAIM only if close position<=0.5;
WEAKNESS=>HIGHER_LOW and RECLAIM on SAME closed minute;
MIXED/UNRESOLVED/UNKNOWN=>no signal, fallback still mandatory.
First signal latches BUY intent; no later score can cancel it. All B/C/F fallback
at10 active minutes clipped to final common comparison grid. Retry to30 active
minutes exactly as Census A; unavailable reference and missing execution remain
separate from model rejection (always false). A must reproduce1,963 fills and
existing +3/+5 Capture exactly. No timing candidate selected/promoted.

## Evaluation and anatomy

Reuse every inherited 30/60/end metric plus strict1m coverage, 30/60 MaxDD and
adverse bounds. End MaxDD from observed entry-onward rows with unknown intrabar
order reported as optimistic/adverse bounds. All-window MFE/MAE are descriptive
high/low touches, not realized returns. Preserve all2155/arm, no winner sampling.
Paired price improvement=100*(1-candidate/immediate); equal tolerance1e-10.
Low proximity uses ordered-oracle low: (entry-low)/low*100 and active delay only
if entry minute>low minute, full-session available and Path!=DIRECT. Same-minute
order unknown, entry-before-low, direct-not-applicable, missing/unfilled separate.
Same-oracle-high retention from Census, no clipping; strict high>entry. Alternative
entry→strictly later max high separately. No-positive-denominator and timing edge
reasons retained. +1..5 capture uses FIXED Selector outcome denominators; all
populations and unknowns shown. State stratification by T0 (not selected fill
state) primary; fill-state and future-path anatomy separately evaluator-only.
Failure flags (overlap allowed): cheaper, same, dearer; cheaper but +3 Capture
lost; MAE30 improved but +3 lost; low-distance improved with retention nonworse;
no-signal fallback; unavailable. No causal attribution from association alone.
Save per-session and four time buckets (<10:00,<11:30,<14:00,rest), month,
state transitions (exclude lunch/gaps), signal occurrence/co-occurrence by state,
first causally available timestamp and delay. No bootstrap tuning.

## Verification and STOP

Unit tests: path predicates/reasons/ties; samebar unknown; daily future rejection;
strict missing/lunch; suffix invariance; score transition; fallback never rejects;
low/high edge cases; oracle forbidden at state API. Full study and plots twice,
byte-hash comparison. Run inherited focused tests and offline regression and
Frozen preservation. Preserve code/protocol/raw derived evidence/report/plots and
CI receipt in this NEW directory. Dedicated CI success != entire PR green.
STOP regardless of outcome. No Entry vNext learning/freeze, no Dictionary,
no Holdout/Fresh/OOS/Prospective, no NEW EXIT, no Selector or safety flag change.
