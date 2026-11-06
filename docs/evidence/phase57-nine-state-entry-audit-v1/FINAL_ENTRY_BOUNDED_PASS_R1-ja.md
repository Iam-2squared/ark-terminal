# Phase57 9-State Entry Audit — Bounded Pass Final R1

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## 最終判定

**`DEVELOPMENT_REVIEW_COMPLETE_WITH_UNRESOLVED_STATES / ENTRY_COMPLETION_GATE_NOT_MET`**

9-State Entryの今回許可されたbounded passは完了した。全9 Stateについて分類監査またはzero-observation/code dispositionを固定し、高支持Stateで事前固定できた性能仮説はすべて測定・棄却した。少数StateはINSUFFICIENT、RANGE/SHARP_DROPは診断後もfuture Lowを使わずに正当化できる単一候補がなくHOLDとした。

採用できる新Entry候補は0。したがってaccepted ONE_MINUTE baselineを変更しない。

Entry completion gateは満たしていないため、ユーザー指定どおり **EXIT / Capital Allocation / Portfolio統合へは進まない**。

## 9-State disposition

| State | T0 N | semantic/classification audit | performance disposition | new hypothesis |
|---|---:|---|---|---:|
| REBOUND | 192 | DONE | 1候補REJECT | 1/1 |
| RISE | 111 | DONE | 1候補REJECT | 1/1 |
| SHARP_RISE | 7 | DONE | INSUFFICIENT_FOR_PERFORMANCE_RULE | 0/1 |
| DROP | 1403 | DONE | 1候補REJECT | 1/1 |
| PULLBACK | 354 | DONE | 1候補REJECT | 1/1 |
| RANGE | 57 | DONE | HOLD — NO_JUSTIFIED_SINGLE_HYPOTHESIS | 0/1 |
| SHARP_DROP | 26 | DONE | HOLD — LIMITED_SUPPORT_NO_JUSTIFIED_SINGLE_HYPOTHESIS | 0/1 |
| DROP_STOP | 5 | DONE | INSUFFICIENT_FOR_PERFORMANCE_RULE | 0/1 |
| RISE_STOP | 0 | T0 + transition/code audit DONE | NO_OBSERVATIONS / INSUFFICIENT | 0/1 |

非zero blind semantic reviewは、future/outcomeを隠してreviewを固定した後にsealed baselineを開く順序を守った。reviewed samplesではREBOUND/RISE lane 34/34、RISE lane 36/36、SHARP_RISE 19/19、DROP 36/36、PULLBACK 36/36、RANGE 36/36、SHARP_DROP 36/36、DROP_STOP 17/17がbaseline Stateと一致した。これはreviewed implementation consistencyのEvidenceであり、全母集団の自然言語的意味分類100%を主張するものではない。

RISE_STOPはT0だけでなく保存checkpoint遷移でも観測0。一方、static code上は到達可能なのでdead enumとは断定せず、`NO_OBSERVATIONS` とする。

## Accepted Entry baseline — whole 2,155 Development population

今回のbounded passで採用候補が0だったため、accepted referenceは保存済みDROP/PULLBACK one-minute Development版のまま。

| KPI | ONE_MINUTE accepted baseline |
|---|---:|
| Population | 2,155 |
| Fill | 1,764 |
| Fill率 | 81.8561% |
| valid EntryPosition N | 1,751 |
| **EntryPosition mean** | **67.4868%** |
| Median | 49.60% |
| <=10% | 9.59% |
| <=15% | 15.19% |
| <=25% | 26.73% |
| <=50% | 50.37% |
| +3 Capture | 約71.88% |
| +5 Capture | 約73.53% |

ユーザーのaspirational completion evidenceである whole-Entry mean `<15%` に対し、現在は **67.49%**。差は約 **52.49 percentage points** であり、達成とは扱えない。

また、`<=15%` case-rate 15.19%はmean EntryPosition 15%未満を意味しない。両者を混同しない。

## Evaluated performance hypotheses

### REBOUND — REJECT

事前固定したconfirmation candidateはEntryPosition自体を大きくLow側へ動かしたが、Fillが約38%まで崩壊した。Opportunityを捨てる第二Selector化なのでGate FAIL。追加の閾値微調整は行わない。

### RISE — REJECT

run `35897369272`。Fill `-2.70pp`、<=15% `18.07% -> 14.81%`、+3 Capture `-9.30pp`、+5 Capture `-12.50pp`。common-case paired EntryPositionは約`-0.36pp`改善したが、Low->Entry distanceとpreservation Gateが失敗。

### DROP — REJECT

run `35897369272`。Fill `-3.85pp`、paired EntryPosition約`+1.93pp`悪化、<=15% `13.26% -> 10.71%`、+3 Capture `-6.86pp`。Gate FAIL。

### PULLBACK — REJECT

run `35897369272`。Fill `-4.52pp`、common-case paired EntryPosition約`+1.43pp`悪化、<=15% `15.38% -> 13.59%`、+3 Capture `-9.52pp`。aggregate meanだけの見かけの改善を採用しない。

4候補とも結果を見た後のthreshold sweepやalternate feature retryは実施していない。

## Remaining-State diagnostic and stop decision

precommit `REMAINING_STATE_LOW_CENTERED_DIAGNOSTIC_R1.md`に従い、SHARP_RISE/RANGE/SHARP_DROP/DROP_STOPのcausal checkpoint witnessをOracle Low開封前に完全構築し、その後Evaluator-onlyでLowにalignmentした。

最初のworkflow run `35902412560` は `ModuleNotFoundError: No module named 'scripts'` でFAIL。research semanticsとは無関係なPython path plumbingだったため、commit `f05fb2c3db13101f6efaf59d56d91cc581055b6f` で `PYTHONPATH=${{ github.workspace }}` だけを追加した。

正式corrected run:

- run `35909289314`
- job `107344746093`
- conclusion `SUCCESS`
- artifact `10772622341`
- artifact ZIP digest `sha256:e1f11e0dab4920f81e8d195a58a9322deb1a608cbc16395553b55241b650492f`
- `summary.json` SHA256 `0c08ad5464e5a0e6b4ac03d339cd3599845db6296d63e269e9278fc6b2980148`
- `manifest.json` SHA256 `11e39a917f2ac50562fdd497cec20f0245a7aba79eaa5d182c3d61cb981e4402`

Causality/integrity guard:

- causal witness built before Oracle open: PASS
- State future violations: 0
- closed-bar checks: 334/334 PASS
- Oracle Low/High decision use: 0
- future-outcome decision use: 0
- provider requests: 0
- protected data opens: 0
- accepted ONE_MINUTE identity: exact PASS

RANGEはaccepted policy上すでにinitial WAITで、first existing frozen Signalまたはexisting BUY State transitionでEntryする。診断ではLow後のBUY Stateがmedian約5 active minutes、first eitherがmedian約4分だが、これを「Lowから4〜5分待つ」ruleに変換するとfuture-Low alignmentからconfirmation durationを発明することになる。新しいcausal triggerの欠落は見つからなかった。

SHARP_DROPもinitial WAITで、Low後first eitherはmedian約7分、first BUY Stateはmedian約8分。T0 N=26で、pre-Lowに安定したfrozen causal markerがなく、結果からdelayを作る以外の単純候補がない。したがって性能trialを無理に消費しない。

## Completion Gate audit

| Gate | Result |
|---|---|
| 9/9 State classification/disposition | PASS |
| material shared classifier software failure | NONE FOUND |
| frozen Selector / 9-Pattern / six Signals preserved | PASS |
| provider new acquisition | 0 |
| Fresh/OOS/Validation/Prospective new opens | 0 |
| candidate trials precommitted before performance replay | PASS |
| rejected-trial threshold sweep / win-until-PASS | 0 |
| causality / evaluator isolation on measured candidates | PASS |
| accepted whole-population replay identity | PASS |
| Fill/Capture preservation for a new candidate | **NO ACCEPTED CANDIDATE** |
| whole-Entry mean EntryPosition <15% | **FAIL: 67.49%** |
| Entry Development completion | **FAIL / HOLD** |
| EXIT transition authorized | **NO** |

## Status interpretation

This result does **not** mean that better Entry is impossible. It means the currently authorized information/rule space — fixed 9-Pattern classifier, fixed six Signals, immutable Selector and bounded one-shot local timing candidates on this already-exposed Development population — did not produce a valid Entry candidate close to the requested Low-side target without sacrificing Opportunity/Fill/Capture.

A meaningful next Entry research stage requires a new authorization boundary rather than more attempts on the same exposed data. Examples of materially new scope include a new causal Signal/feature family, Volume/Dictionary, learned Entry model, explicit State semantic/threshold revision, or broader Entry architecture change. Such work must receive its own precommit/validation design and cannot be presented as continuation of this bounded pass.

## EXIT / Capital / integrated version

Not entered. Entry completion gate failed, so no EXIT baseline was reconnected to a new Entry candidate and no Capital Allocation/Portfolio mutation was performed.

This preserves the user’s explicit dependency:

`Entry PASS -> EXIT -> Capital Allocation -> integrated candidate`.

The first gate did not pass.

## Evidence map

- controlling protocol: `PROTOCOL_R0.md`
- exposure history: `EXPOSURE_LEDGER_R1.md`
- performance trial history: `TRIAL_LEDGER_R1.md`
- blind review CSVs: per-State `*_BLIND_REVIEW_R1.csv`
- corrected ONE_MINUTE authority: `PROGRESS_R8.md`
- RISE/DROP/PULLBACK trial results: `PROGRESS_R10.md`
- remaining-State diagnostic/disposition: `PROGRESS_R11.md`
- original accepted ONE_MINUTE source: `docs/evidence/phase57-drop-pull-1m-state-recheck-v1/FINAL_REPORT_R1-ja.md`
- accepted source run/artifact: `35818555587 / 10732168448`
- source ZIP SHA256: `74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8`

The original source artifact expires on 2026-12-22 and is not claimed as permanent raw preservation.

## Safety

LONG-only / cash-equity-only. `executionAllowed=false`, `brokerWriteAllowed=false`, `excelOrderWriteAllowed=false`, `rssOrderFunctionAllowed=false`, `liveTradingAllowed=false`, `paperTradingAllowed=false`, `automaticPromotionAllowed=false`, `productionUpdateAllowed=false`, `transmitted=false`.

No main merge and no production action.
