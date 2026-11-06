# Phase57 NEW LONG Entry — Two-Opportunity Candidate Contract

Date: 2026-09-18 JST

Status: **NEW_LONG_ENTRY_TWO_OPPORTUNITY_CANDIDATE_FROZEN**

Source Entry Location Study: `a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb`  
Recovery-confirmation contract: `710034639f269aeaacf5f0e2800b510bdc61c822`  
Recovery FAST-FAIL KILL evidence: `757229e7b0996cb925273172814453ce29b13c04`

Historical Development / outcome-exposed only. This freezes a research candidate architecture, not production approval. Frozen Selector remains unchanged. EXIT, Capital Allocation, Portfolio, 1m, Fresh/OOS, providers and main remain out of scope.

## 1. Why the architecture is simplified now

The Entry Location Study established two facts that must coexist:

1. uniform waiting is harmful because early opportunities are lost;
2. after an actually observed FIRST_CLOSED_DIP, the +5 reference location is materially better on average than the immediate location for that cohort.

The one-shot attempt to wait another full 5m bar for bullish recovery confirmation was then killed: on 144 paired recovery-confirmed anchors, mean D30 worsened 1.2733% -> 1.9760%, common60 Remaining Upside fell 2.9608% -> 1.9396%, +3 preservation was 55.56%, and the challenger bought 0.9136% higher on average. D30 was worse in all 4 chronological blocks.

Therefore this candidate does **not** add another t10/t15 confirmation layer. It also does not pretend the +5 dip reference is a proven bottom: 106 of the 299 cheaper +5 dip entries still fell another >=2% within D30.

The architecture instead exposes two causal **entry opportunities** and leaves notional choice to Capital Allocation.

## 2. Responsibility boundary

### Entry owns
- causal state observation;
- opportunity type;
- opportunity timestamp/reference location;
- expiration/unknown reason;
- deterministic audit trail.

### Capital Allocation owns
- whether either available opportunity receives capital;
- notional/quantity;
- portfolio slot/concentration/risk budget;
- any future decision about distributing capital between multiple opportunities.

### EXIT owns
- management after an actual fill.

Entry does not freeze 50/50, 25/75, or any other tranche fraction. An emitted opportunity is **not** an automatic buy.

## 3. Frozen candidate state machine

### State A — `INITIAL_ENTRY_OPPORTUNITY`

When the Frozen LONG Selector emits a candidate, expose one initial Entry opportunity using the existing causal IMMEDIATE reference semantics. This preserves early opportunity. No future dip/no-dip state is assumed.

### State B — observe exactly the first completed 5m bar

Compare that completed CLOSE with the pinned Selector Decision Price.

- If `first_close >= decision_price`: state = `FIRST_BAR_CONTINUATION`; no secondary opportunity is emitted; secondary state terminates.
- If `first_close < decision_price`: state = `FIRST_CLOSED_DIP`; emit one `DIP_REPRICE_OPPORTUNITY` at the next regular 5m OPEN reference, subject to existing boundary/missing semantics.
- If the first completed bar/reference cannot be observed causally: state = `SECONDARY_UNKNOWN`; do not impute or fabricate a secondary opportunity.

### State C — terminate Entry timing for this anchor

After `FIRST_BAR_CONTINUATION`, `DIP_REPRICE_OPPORTUNITY`, or `SECONDARY_UNKNOWN`, the Entry state engine creates no t10/t15/t20 retry or recovery-confirmation loop.

The downstream system may later decide whether an available opportunity receives capital, but Entry itself does not create additional timing variants.

## 4. Causality

`FIRST_CLOSED_DIP` is not known at t0. The architecture always exposes the initial opportunity without conditioning on future state. The dip-reprice opportunity exists only after the first completed 5m CLOSE has actually been observed below Decision Price.

Decision inputs are limited to:
- Frozen Selector candidate identity and pinned Decision Price;
- causal timestamps/session boundary metadata already present in the saved path semantics;
- the first completed 5m bar CLOSE for the secondary-state transition.

Future HIGH/LOW, D30, future winner labels, EXIT results, Portfolio results, symbol-specific outcomes and later bars are evaluator-only and may not drive the state transition.

## 5. Evidence supporting the two opportunity locations

Primary paired Entry Location panel: 878 anchors / 430 symbols / 76 Development sessions.

### Initial opportunity

Uniform waiting is not a replacement for the initial opportunity:
- WAIT5 mean buy price is 0.0287% worse overall;
- WAIT5 +3/+5 immediate-winner capture is 71.91% / 69.92%;
- WAIT10 +3/+5 capture is 62.92% / 63.41%.

### Dip-reprice opportunity

FIRST_CLOSED_DIP cohort: 328 anchors / 236 symbols / 74 sessions.

Compared with the same cohort's immediate reference, +5 reprice has:
- mean buy improvement: +1.1184%;
- median buy improvement: +0.8002%;
- mean D30: 2.8980% -> 1.8911% (34.74% lower);
- common60 Remaining Upside: 1.6876% -> 2.4291%;
- +3 immediate-winner preservation: 56/59 = 94.92%;
- +5 immediate-winner preservation: 21/21 = 100%.

These are Development descriptive facts, not independent validation and not a claim that every dip-reprice opportunity should be funded.

## 6. Known limitation retained explicitly

Among 299 FIRST_CLOSED_DIP cases where the +5 reference was cheaper than immediate, 106 subsequently experienced another >=2% D30 and 21 experienced >=5% D30.

Therefore:
- `DIP_REPRICE_OPPORTUNITY` means **a causally improved location opportunity**, not `BOTTOM_CONFIRMED`;
- Entry does not claim the dip has ended;
- no automatic full-size purchase is implied;
- no hidden recovery threshold is added after the failed t10 confirmation experiment.

This limitation must remain visible to downstream Capital/EXIT research.

## 7. What is killed and must not be silently revived

- uniform WAIT5 / WAIT10 as the full Entry architecture;
- DIP_CLOSE_FALLBACK10;
- OBSERVE5_DELAY_DIP10;
- the fixed `second_close > first_close AND second_close > second_open` recovery-confirmation rule;
- arbitrary t10/t15/t20 confirmation loops on the same exposed evidence;
- Claude's unmeasured fixed 50/50 split;
- Entry-side symbol blacklists or outcome-fitted thresholds;
- old E[L] re-selection gate.

## 8. Candidate output schema

Each Selector anchor may produce:

1. one `INITIAL_ENTRY_OPPORTUNITY` event;
2. zero or one `DIP_REPRICE_OPPORTUNITY` event;
3. a terminal secondary state: `FIRST_BAR_CONTINUATION`, `DIP_REPRICE_EMITTED`, `SECONDARY_UNKNOWN`, or boundary expiration.

Each opportunity event must include at minimum:
- anchor/event id;
- symbol/session;
- Selector decision timestamp and pinned Decision Price;
- opportunity type;
- causal opportunity timestamp;
- reference price status/value if observable;
- source state;
- missing/boundary status;
- no quantity field owned by Entry.

## 9. Implementation gate

The next step may implement this state machine in an isolated research module and replay it on the already-exposed Development data.

Implementation is allowed only if it preserves:
- identical 2,743 first-anchor identity;
- initial opportunity emission independent of future dip state;
- exactly one first-bar state transition;
- at most one secondary dip-reprice opportunity;
- no model fit/prediction;
- no result-driven threshold;
- no quantity optimization;
- no EXIT/Capital/Portfolio evaluation;
- no Fresh/OOS/provider/1m access;
- no Selector/runtime production mutation;
- no main merge.

## 10. Completion criteria for the research kernel

Before calling the Entry timing kernel implementation-complete, require:

- deterministic state replay and regenerated artifacts;
- synthetic causality tests proving future bars cannot alter t0 output;
- missing/boundary tests;
- 2,743 full-anchor ledger retained;
- primary 878 population reproduced without population drift;
- FIRST_CLOSED_DIP count 328 reproduced on the primary panel;
- no-dip count 550 reproduced on the primary panel;
- opportunity events auditable without future outcome fields in decision payloads;
- existing Frozen Selector/Development hashes unchanged;
- CI green.

Performance numbers from the already-exposed Development set may be reproduced for parity, but they are not new validation.

## 11. Next research question after kernel parity

Do **not** invent a third timing rule automatically. Once the two-opportunity kernel is deterministic, the next decision is an architecture-boundary question:

> Can Capital Allocation use `INITIAL_ENTRY_OPPORTUNITY` and `DIP_REPRICE_OPPORTUNITY` without Entry itself fixing a tranche ratio, while preserving the Selector opportunity and respecting cash constraints?

That is a separate contract. Entry timing/location itself should not be reopened unless kernel parity fails or genuinely new evidence is authorized.

## 12. Safety / stop

All trading/write/promotion flags remain false. No live/paper execution. No automatic promotion. PR #587 remains Draft/unmerged.

This contract freezes the current NEW LONG Entry **timing/location candidate** as a two-opportunity state engine for implementation/parity work. It does not freeze portfolio sizing, EXIT, or production behavior.