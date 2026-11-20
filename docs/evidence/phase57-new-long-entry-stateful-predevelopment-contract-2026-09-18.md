# Phase57 NEW LONG Entry — Stateful Opportunity Pre-Development Contract

Date: 2026-09-18 JST

Status: **STATEFUL_ENTRY_PREDEVELOPMENT_CONTRACT_FROZEN**

Source Entry Location Study head: `a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb`.

This is a research contract only. No runtime Entry, Selector, EXIT, Capital Allocation, Portfolio, workflow, provider, Fresh/OOS, or 1m change is authorized by this file.

## 1. Purpose

Build the next NEW LONG Entry as a **timing/location state engine**, not a second symbol selector.

The frozen LONG Selector remains responsible for finding opportunity. Entry is responsible for when a causal entry opportunity exists. Capital Allocation remains responsible for notional/position size. EXIT remains out of scope for this Entry-only study.

The contract deliberately does **not** freeze Claude's proposed `50% at t0 + 50% at t5`. No tranche fraction has Entry Location evidence. Position fraction is not an Entry parameter in this phase.

## 2. Evidence that motivates this contract

Primary paired panel: 878 first symbol-session anchors / 430 symbols / 76 Development sessions. Full first-anchor ledger remains 2,743.

- IMMEDIATE mean D30 2.1258%; 337/878 (38.38%) reach >=2% adverse move within 30m.
- Uniform WAIT5: mean buy 0.0287% worse, D30 improvement only 3.81%, +3/+5 immediate-winner capture 71.91%/69.92%.
- Uniform WAIT10: mean buy 0.0357% worse, +3/+5 capture 62.92%/63.41%, common60 remaining-upside loss 0.4100pp.
- FIRST_CLOSED_DIP: 328 anchors / 236 symbols / 74 sessions. WAIT5 buys 1.1184% cheaper on average, D30 2.8980% -> 1.8911%, +3 capture 56/59, +5 capture 21/21.
- But among 299 FIRST_CLOSED_DIP cases bought cheaper at +5, 106 still suffer >=2% additional D30. Therefore `dip observed -> buy` is not accepted as a finished Entry rule.
- NO_FIRST_CLOSED_DIP: 550 anchors. WAIT5 buys 0.7128% higher, D30 1.6654% -> 2.1366%, common60 remaining upside loses 0.8361pp.

FIRST_CLOSED_DIP / NO_FIRST_CLOSED_DIP are known only after the first completed 5m bar. They may not be used as if known at t0.

## 3. Architecture boundary

The state engine emits **entry opportunities**, not quantities.

### Entry owns
- causal observation state;
- opportunity timestamp;
- reference entry location/time;
- expiration reason;
- audit trail.

### Capital Allocation owns
- whether available capital permits a purchase;
- quantity/notional;
- portfolio slots/concentration/risk budget.

### EXIT owns
- stop/hold/profit-taking/exit timing after an actual entry.

No Entry gate may use EXIT PnL, Portfolio PnL, MaxDD, capital heat, future HIGH/LOW, or realized outcome labels.

## 4. Minimal state machine

States:

1. `INITIAL_OPPORTUNITY`
   - emitted causally at Selector decision time t0;
   - preserves the early opportunity without claiming that future dip/no-dip is known.

2. `FIRST_BAR_OBSERVED_CONTINUATION`
   - first completed 5m CLOSE >= pinned Decision Price;
   - secondary delayed opportunity expires;
   - no retrospective claim that t0 was known to be the no-dip cohort.

3. `DIP_OBSERVED`
   - first completed 5m CLOSE < pinned Decision Price;
   - do **not** automatically emit a second entry opportunity;
   - this state exists because 106/299 cheaper +5 entries subsequently fell another >=2%.

4. `RECOVERY_CONFIRMED`
   - eligible only after `DIP_OBSERVED`;
   - emits one `SECOND_ENTRY_OPPORTUNITY` using the fixed causal confirmation below.

5. `SECONDARY_EXPIRED`
   - secondary opportunity does not occur within the single allowed confirmation step or cannot be observed without missing/boundary ambiguity.

No recursive t15/t20/t25 confirmation loop. No re-entry after expiration in this experiment.

## 5. One fixed recovery-confirmation hypothesis

This is the **only new timing hypothesis** authorized for the first FAST-FAIL.

After a valid FIRST_CLOSED_DIP at the first completed 5m bar, observe exactly one additional completed 5m bar.

`RECOVERY_CONFIRMED = (second_close > first_close) AND (second_close > second_open)`

If true, emit `SECOND_ENTRY_OPPORTUNITY` at the next scheduled regular 5m OPEN (the boundary immediately after that second completed bar), subject to existing missing/session-boundary semantics.

If false, emit `SECONDARY_EXPIRED`.

Rationale: this is a minimal local recovery observation, not a bottom prediction. It uses only completed-bar information and contains no fitted numeric threshold. It does not require reclaiming Decision Price, future HIGH/LOW, a model score, symbol identity, or outcome labels.

This hypothesis is **not** claimed to be good before measurement. It is deliberately one-shot so a weak confirmation mechanism can be killed quickly.

## 6. Comparators

On the same causally eligible FIRST_CLOSED_DIP anchors, report:

- `IMMEDIATE` reference opportunity at t0;
- `DIP_OPEN5` diagnostic reference at +5m (known Location Study comparator; not an adopted rule);
- `RECOVERY_CONFIRM10` challenger from Section 5.

The study must retain the full 2,743-anchor ledger and clearly separate the complete paired population. Do not generalize paired-only results to missing/boundary anchors.

## 7. Entry-only metrics

EXIT / PF / win rate / Portfolio / MaxDD are prohibited as primary gates.

Primary measurements:

- opportunity coverage and UNKNOWN/EXPIRED counts;
- reference buy-price change;
- post-entry D5/D10/D15/D30;
- D30 p90/p95/ES95/worst and >=2/>=5/>=10 adverse counts;
- own+30 and common selection+60 Remaining Upside;
- +3/+5 opportunity preservation with explicit denominator semantics;
- paired 2D Remaining-Upside x Downside table;
- chronological 4-block and deterministic symbol-group stability;
- FIRST_CLOSED_DIP population size and recovery-confirmed population size;
- time-to-second-opportunity.

Do not compress the decision into a single upside/downside ratio.

## 8. Pre-frozen FAST-FAIL gates

The challenger is a **secondary opportunity mechanism**, so evaluate it against `DIP_OPEN5` on the same recovery-confirmable anchors, while also showing IMMEDIATE.

Minimum evidence sufficiency:
- >=30 recovery-confirmed paired anchors;
- >=20 unique symbols;
- >=20 baseline +3 opportunities where measurable;
- >=10 baseline +5 opportunities where measurable; otherwise +5 is diagnostic only.

Performance screen:
- +3 preservation >=90% of the paired DIP_OPEN5 baseline opportunity set;
- +5 preservation >=90% when denominator >=10, otherwise diagnostic only;
- mean D30 improvement >=10% versus paired DIP_OPEN5;
- D30 ES95 non-worse versus paired DIP_OPEN5;
- common60 Remaining Upside >=90% of paired DIP_OPEN5 mean;
- deep-adverse >=5% count/rate non-worse;
- D30 mean non-worse in >=3/4 chronological blocks where each block has sufficient paired observations.

No gate relaxation after results. Passing means `CONTINUE_NOT_VALIDATED`, never production approval.

## 9. Immediate opportunity treatment

The INITIAL_OPPORTUNITY at t0 remains part of the architecture because uniform waiting destroys opportunity. This contract does **not** decide how much capital, if any, is assigned at t0. It therefore does not manufacture a blended 50/50 performance number.

The first FAST-FAIL asks only whether a **second, causally better-located opportunity after an observed dip** can be defined with useful Entry-only properties.

If the second opportunity fails, the t0 opportunity remains a baseline architecture element; no conclusion about final allocation size follows.

## 10. Kill conditions

Kill this exact `RECOVERY_CONFIRM10` hypothesis immediately if any of the following holds:

- evidence sufficiency fails;
- +3 preservation <90%;
- +5 preservation <90% with denominator >=10;
- mean D30 improvement <10%;
- ES95 worsens;
- common60 Remaining Upside <90% of paired DIP_OPEN5;
- deep-adverse >=5% rate worsens materially relative to the paired baseline;
- chronological stability fails the pre-frozen rule;
- the rule requires missing-data fill, future information, threshold retuning, symbol-specific exceptions, or recursive waiting to look acceptable.

If killed, preserve the useful causal state-machine infrastructure and the failure evidence; do not tune the rule.

## 11. Continue conditions

Only if the screen passes:

- keep `INITIAL_OPPORTUNITY` + `DIP_OBSERVED` + `RECOVERY_CONFIRMED` as an Entry Architecture candidate;
- then perform a separate architecture review before deciding whether/how Capital Allocation assigns notional across multiple opportunities;
- still do not open Fresh/OOS;
- still do not reopen 1m automatically.

## 12. 1m reopen condition

1m remains PAUSED. Reopen only if 5m FAST-FAIL shows a specific resolution bottleneck, for example:

- useful dip cases are frequently censored because a complete 5m close arrives after most Remaining Upside is gone; or
- recovery-confirmed and continuing-dip paths remain inseparable at 5m while a pre-existing authorized finer-grained dataset can test that exact distinction.

Do not reopen 1m merely because this one confirmation rule fails.

## 13. Explicit prohibitions

- Selector modification/retraining/threshold changes;
- old E[L] gate revival;
- t0 use of future FIRST_CLOSED_DIP/NO_FIRST_CLOSED_DIP;
- future LOW/HIGH as decision inputs;
- symbol blacklist or symbol-specific threshold;
- outcome-driven subgroup selection;
- model fit/prediction in this first FAST-FAIL;
- WAIT5/WAIT10 threshold variants;
- multiple recovery thresholds or candle-pattern zoo;
- position fraction tuning;
- EXIT/Capital/Portfolio tuning;
- Fresh/OOS/provider requests;
- 1m execution;
- main merge or trading/write enablement.

## 14. Required final verdict

The next study must end with exactly one of:

- `STATEFUL_ENTRY_RECOVERY_FAST_FAIL_CONTINUE_NOT_VALIDATED`
- `STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL`
- `STATEFUL_ENTRY_RECOVERY_FAST_FAIL_INCONCLUSIVE`
- `STATEFUL_ENTRY_RECOVERY_FAST_FAIL_BLOCKED`

Then STOP. No automatic v2/v3 variant creation.
