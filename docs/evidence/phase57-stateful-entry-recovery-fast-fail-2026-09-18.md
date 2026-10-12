# STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL

Date: 2026-09-18 JST

Source Entry Location Study: `a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb`  
Pre-Development Contract: `710034639f269aeaacf5f0e2800b510bdc61c822`  
Measured evaluator head: `476b11336fcb7d372aaa7fd2d380080fc1a84448`

Historical Development / outcome-exposed only. This report is Entry-only. Selector, Entry runtime, EXIT, Capital Allocation, Portfolio and 1m research remain unchanged.

## Hypothesis tested

After the already-observed FIRST_CLOSED_DIP, wait for exactly one more completed 5m bar. Define one causal recovery confirmation:

`second_close > first_close AND second_close > second_open`

If true, emit a second Entry opportunity at the next regular 5m OPEN reference. If false, expire the secondary opportunity. No model, score, fitted threshold, symbol rule, recursive wait, future HIGH/LOW decision input, or result-driven variant search.

Comparator on the same recovery-confirmed anchors: the existing +5m DIP reference opportunity.

## Population

- Full first symbol-session anchors: 2,743
- Primary complete selection+60m panel: 878
- FIRST_CLOSED_DIP: 328
- Recovery-confirmed by the fixed rule: 144
- Fully paired Entry-only evaluation: 144
- Paired unique symbols: 119
- States: 1,865 outside primary / 550 first-bar continuation / 184 secondary expired / 144 recovery confirmed

Evidence sufficiency passed. The hypothesis was killed for performance, not for insufficient sample.

## Main paired result: +5 dip opportunity vs recovery-confirmed +10 opportunity

| Metric | DIP_OPEN5 baseline | RECOVERY_CONFIRM10 | Result |
|---|---:|---:|---|
| Mean D30 | 1.2733% | 1.9760% | **55.19% worse** |
| D30 ES95 | 5.5794% | 7.4443% | worse |
| D30 >=5% | 5/144 (3.47%) | 8/144 (5.56%) | worse |
| Common60 Remaining Upside mean | 2.9608% | 1.9396% | **65.51% preserved only** |
| +3 preservation | 25/45 | **55.56%** | fail |
| +5 preservation | 15/16 | 93.75% | pass isolated gate |
| Mean buy improvement vs DIP_OPEN5 | — | **-0.9136%** | buys higher |
| Median buy improvement vs DIP_OPEN5 | — | -0.7041% | buys higher |

The recovery rule does not solve the 106/299 continuing-downside concern. On the selected 144 anchors it waits until price has already rebounded, pays materially more, then still has worse subsequent adverse movement than the +5 dip reference.

## Chronological stability

The 76 primary Development sessions were kept on the original fixed 19-session x 4 calendar blocks; paired rows were not compressed into a new calendar.

| Block | Paired N | DIP_OPEN5 mean D30 | Recovery mean D30 | Non-worse? |
|---|---:|---:|---:|---|
| 1 | 35 | 1.1917% | 1.9455% | No |
| 2 | 39 | 1.0177% | 1.7268% | No |
| 3 | 38 | 1.3612% | 1.7664% | No |
| 4 | 32 | 1.5700% | 2.5621% | No |

Chronological non-worse: **0/4**.

## Frozen gate disposition

- +3 preservation >=90%: **FAIL**
- +5 preservation >=90% with denominator >=10: PASS
- mean D30 improvement >=10%: **FAIL**
- D30 ES95 non-worse: **FAIL**
- common60 Remaining Upside >=90% of DIP_OPEN5: **FAIL**
- >=5% deep-adverse rate non-worse: **FAIL**
- D30 non-worse in >=3/4 chronological blocks: **FAIL (0/4)**

Final verdict: **STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL**.

No gate relaxation and no threshold tweak.

## What this kills

Kill this exact idea:

> FIRST_CLOSED_DIP -> wait one full additional 5m bar -> require a green/higher close -> enter at the next 5m OPEN.

Do not rescue it by changing the green-bar threshold, requiring a different arbitrary candle pattern, or adding t15/t20 confirmation loops on the same exposed result.

## What remains useful

The earlier Location Study evidence remains intact:

- Uniform waiting is bad because it destroys early opportunity.
- FIRST_CLOSED_DIP is a real causal state known at +5m, and the +5 reference location is on average materially cheaper than Immediate for that cohort.
- `dip observed -> automatic buy` is not proven because many cheaper +5 entries continue down.
- This FAST-FAIL now adds a new lesson: **waiting one more complete 5m bar for a simple bullish recovery confirmation is too late and does not reduce subsequent downside on the confirmed subgroup.**

This does not prove that all stateful Entry is impossible. It does not prove that 1m is necessary. It narrows the architecture: a useful post-dip signal, if one exists, must not pay the full extra-5m confirmation penalty represented by this rule, or must add genuinely different causal information rather than another arbitrary candle threshold.

## Verification / safety

Predict Tests workflow run `35242895108`: SUCCESS. Offline regression reported predict 2,763/2,763 PASS, discovery 26/26, foundation 39/39, Python 30/30, RSS 89/89; blocked unexpected network attempts 0. Original Development preservation check PASS.

- model fits/predictions: 0
- Fresh/OOS: 0
- provider requests: 0
- 1m research runs: 0
- EXIT evaluations: 0
- Capital evaluations: 0
- Portfolio evaluations: 0
- candidate auto-promotion: false
- main merge: false
- all nine trading/write/promotion flags: false

STOP this exact recovery-confirmation hypothesis. No automatic variant creation.
