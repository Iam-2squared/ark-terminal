# STEP 2 — Path / State Vocabulary Decision v1

Date: 2026-09-21 JST

Status: VOCABULARY_V1_DEFINED / STOP FOR HUMAN REVIEW

## Scope

This STEP answers one question only:

> How should Entry describe observed price behavior without conflating observation quality, overlapping behavior, temporal order, and terminal outcome?

It uses only the saved STEP 1 Future Path Deep Audit evidence. It does not evaluate causal recognizability, Signals, BUY NOW/WAIT, Entry prices, learning, Dictionary, Holdout, EXIT, Capital, or Portfolio.

## Evidence basis

STEP 1 reproduced all 2,155 historical classifications exactly. It found:
- 496 observation-gate failures.
- 355 NO_DOMINANT_PATH cases, including substantial observation sparsity and economically nontrivial observed motion.
- 677 sufficiently observed Opportunities with 2+ existing predicates true.
- 539 of those overlapping cases were absorbed into final CHOP by the existing priority rule.
- Final CHOP 828 = 289 CHOP-only + 539 overlap-absorbed.
- Existing predicate occurrence differed materially from final exclusive labels: DIRECT 67 vs 50; RECOVERY 810 vs 202; CONSOLIDATION 106 vs 10; WEAKNESS 114 vs 76.
- Mixed predicate truth does not by itself prove temporal state transition.

Therefore the old 5+1 label remains historical evidence, but is not adopted as the canonical Entry-facing vocabulary.

## Vocabulary v1: four orthogonal layers

### Layer A — Observation Status

Observation quality is not a price state.

Allowed values:
- OBSERVED_SUFFICIENT
- OBSERVED_PARTIAL
- OBSERVATION_INSUFFICIENT

Reason codes are separate and may coexist:
- SHORT_REMAINING_HORIZON
- SPARSE_OBSERVED_MINUTES
- TERMINAL_EVALUATION_UNAVAILABLE
- SESSION_BOUNDARY
- UNRESOLVED_SOURCE_CAUSE

Rules:
- Never map an observation failure to a market-behavior state.
- Never invent, forward-fill, interpolate, or substitute missing 1m bars.
- UNKNOWN is not a catch-all label. If the cause is insufficient observation, use OBSERVATION_INSUFFICIENT plus reason codes.
- Source cause remains unresolved unless evidence distinguishes no-trade, halt, provider loss, or another cause.

### Layer B — Behavior Attributes (multi-label)

These attributes may coexist. They are not mutually exclusive classes.

Initial vocabulary, preserving concepts already evidenced in STEP 1:
- CONTINUATION_UP
- PULLBACK
- RECOVERY
- CONSOLIDATION
- BREAKOUT_UP
- MULTI_SWING / CHOPPINESS
- WEAKNESS_DOWN

Rules:
- Do not force exactly one attribute per Opportunity or timestamp.
- CHOPPINESS is an attribute describing repeated two-way movement, not an overriding final class.
- RECOVERY + CHOPPINESS, CONSOLIDATION + BREAKOUT_UP, WEAKNESS_DOWN + CHOPPINESS, etc. are valid combinations.
- The existing fixed predicates are retained as historical witnesses. STEP 2 does not tune their thresholds or claim that these seven names are already causally recognizable.

### Layer C — Temporal Event / Transition Record

When observed witnesses establish order, preserve the order instead of collapsing it into one label.

Representation:
EVENT_1 -> EVENT_2 -> ... with observed timestamps and ambiguity flags.

Examples of valid descriptive sequences:
- PULLBACK -> RECOVERY
- CONSOLIDATION -> BREAKOUT_UP
- PULLBACK -> RECOVERY -> CONSOLIDATION -> BREAKOUT_UP

Rules:
- A multi-label combination is not automatically a transition.
- Transition is recorded only when observed witness timestamps establish order.
- Same-bar order, missing-gap order, and unobserved intervals remain ORDER_AMBIGUOUS.
- No future-derived transition may be used later as a real-time decision input; STEP 3 must separately test causal recognition from closed data.

### Layer D — Path Descriptors

Continuous descriptors remain separate from semantic state names:
- terminal return
- observed envelope/range
- ordered Low -> Later High range
- efficiency
- reversal count
- direction changes
- realized volatility
- terminal position within envelope
- recovery from observed low
- below-selector fraction
- observation density / contiguous-run metrics

These describe degree and geometry. They must not silently become hard classes without a separately authorized study.

## UNKNOWN policy

Target is not to manufacture UNKNOWN=0.

Instead:
1. Observation uncertainty -> Layer A reason, not UNKNOWN behavior.
2. Multiple simultaneous behaviors -> keep multiple Layer B attributes.
3. Known ordered events -> Layer C sequence.
4. Adequately observed motion that matches no current semantic attribute -> OTHER_OBSERVED_PATTERN, retaining Layer D descriptors.
5. Truly indeterminate order -> ORDER_AMBIGUOUS at the transition level.

This removes the old practice of mixing missing observation, overlapping predicates, and no-predicate cases inside one AMBIGUOUS/INSUFFICIENT bucket while preserving honest uncertainty.

## Relationship to old 5+1

The old labels remain immutable historical evidence:
- DIRECT_CONTINUATION
- PULLBACK_RECOVERY
- CONSOLIDATION_BREAKOUT
- MULTI_SWING_CHOP
- PERSISTENT_WEAKNESS
- AMBIGUOUS_INSUFFICIENT

They are not deleted or rewritten.

For future Entry research, the canonical conceptual representation becomes:

Observation Status
+ zero-or-more Behavior Attributes
+ observed ordered Events/Transitions when order is established
+ continuous Path Descriptors

No exclusive priority rule may erase an already-observed behavior attribute.

## Completion decision

STEP 2 question is answered at the specification level:
- Observation quality and behavior are separated.
- Behavior is multi-label.
- Temporal order is represented only when observed.
- CHOP becomes an attribute rather than an overriding path class.
- UNKNOWN is replaced by explicit uncertainty semantics; it is not forcibly eliminated.
- Old 5+1 evidence remains preserved for lineage and comparison.

This is a vocabulary decision only. It is not evidence that the vocabulary can be recognized causally in real time.

## Hard STOP

Do not start STEP 3 automatically.

STEP 3, if separately authorized by the human, will test Causal State Recognition using only:
- D-5..D-1 Recent Daily candidates,
- Previous Day fully observed 1m,
- Today Open -> NOW closed 1m,

with Dictionary excluded.

STEP 3 must measure whether Layer B/C concepts can be recognized from information available at NOW. Future anatomy is evaluator-only.

## Frozen / Safety

Frozen Selector unchanged. No retrain/rerank/refilter. No Opportunity rejection.
No Signal evaluation. No Entry Timing evaluation. No model fitting. No Dictionary. No Holdout. No EXIT.
LONG-only / cash-equity-only.
executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
