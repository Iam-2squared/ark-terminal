# Phase57 9-State Entry Audit — PROGRESS R11 / Remaining-State Diagnostic Closeout

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## Scope

`PROTOCOL_R0.md` remains controlling. This append-only receipt closes the diagnostic-only pass for `SHARP_RISE`, `RANGE`, `SHARP_DROP`, and `DROP_STOP`, records one workflow-plumbing repair, and fixes the remaining State dispositions. It does not change the frozen 9-Pattern Contract, six frozen Signals, Frozen Selector, accepted ONE_MINUTE baseline, BUY/WAIT semantics, or any protected-data boundary.

## Git / workflow identity

The precommitted diagnostic workflow first ran at source HEAD `6500fa8edcaa7b9b58b3af5f45717d405fc7bca0`:

- workflow: `Phase57 Nine-State Low-Centered Attribution v2`
- run: `35902412560`
- job: `107321643787`
- result: FAIL
- failing step: `Build frozen causal witnesses then align evaluator-only Low anatomy`
- exact cause: `ModuleNotFoundError: No module named 'scripts'`

The generalized source-generation step and both approved artifact restore/hash-verification steps had already passed. The failure was Python module-path plumbing, not a research result.

Minimal repair commit `f05fb2c3db13101f6efaf59d56d91cc581055b6f` adds only `PYTHONPATH: ${{ github.workspace }}` to the workflow environment. No sampling rule, State definition, Signal, timing rule, target, evaluator, threshold, Gate, or data scope changed.

Corrected dedicated run:

- run: `35909289314`
- job: `107344746093`
- conclusion: `SUCCESS`
- artifact: `10772622341`
- artifact digest: `sha256:e1f11e0dab4920f81e8d195a58a9322deb1a608cbc16395553b55241b650492f`
- artifact expiry: `2026-12-22T19:26:08Z`

The corrected run passed source generalization, approved raw-substrate SHA verification, accepted ONE_MINUTE evidence SHA verification, diagnostic build, causal/integrity guard and artifact upload.

## Causal / integrity result

- population: `2155`
- target States: `SHARP_RISE`, `RANGE`, `SHARP_DROP`, `DROP_STOP`
- causal witness fully built before Oracle Low open: PASS
- State future violations: `0`
- closed-bar checks: `334 / 334` PASS
- Oracle Low/High decision use: `0`
- future-outcome decision use: `0`
- provider requests: `0`
- protected-data opens: `0`
- safety/write/trading flags: all false
- accepted ONE_MINUTE identity guard: `1764 / 2155` fills and mean EntryPosition `0.6748679920277816` exact match

Oracle Low is used only after the causal checkpoint witness is frozen, for Development attribution. No candidate decision function receives Oracle Low.

## Remaining-State diagnostic

### SHARP_RISE — N=7 — INSUFFICIENT

The cohort remains too small for a defensible performance rule. The diagnostic does not reveal a software/Contract defect.

- population: `7`
- baseline Fill: `100%`
- baseline EntryPosition mean: about `61.75%`
- first existing BUY State after evaluator Low: median about `5` active minutes
- first either existing BUY State/frozen Signal after Low: within `1` minute for all seven only in the evaluator-aligned description, not a causal Low detector

Disposition remains `INSUFFICIENT_FOR_PERFORMANCE_RULE`. No performance hypothesis consumed.

### RANGE — N=57 — HOLD / NO JUSTIFIED SINGLE HYPOTHESIS

Accepted ONE_MINUTE baseline:

- Fill: `55 / 57 = 96.49%`
- valid EntryPosition: `55`
- mean EntryPosition: `73.10%`
- median: `51.97%`
- <=15%: `12 / 55 = 21.82%`
- <=25%: `14 / 55 = 25.45%`
- baseline comparable filled entries before evaluator Low: `35 / 55 = 63.64%`

Causal witness after evaluator Low:

- first existing BUY State: median `5` active minutes; <=3 minutes `36.84%`; <=5 minutes `59.65%`; <=10 minutes `87.72%`
- first frozen Signal: median `7.5` active minutes among observed; `7 / 57` have no such post-Low signal in the window
- first either existing BUY State or frozen Signal: median `4` active minutes; <=3 minutes `45.61%`; <=5 minutes `64.91%`; <=10 minutes `89.47%`

The frozen baseline already treats initial RANGE as WAIT and enters on the first existing frozen Signal or first transition into an existing BUY State. Therefore the diagnostic does not expose an omitted causal trigger. Converting the evaluator-aligned post-Low delays into a new waiting threshold would use future-Low attribution to invent a persistence duration. The only previously precommitted generic confirmation family was already rejected on the larger RISE/DROP/PULLBACK cohorts because it degraded Fill/Capture and threshold rates.

Result: no defensible new one-shot candidate is precommitted. `RANGE = NO_JUSTIFIED_SINGLE_HYPOTHESIS / HOLD`. Hypothesis budget remains `0/1` rather than spending it on an outcome-derived delay.

### SHARP_DROP — N=26 — LIMITED SUPPORT / HOLD

Accepted ONE_MINUTE baseline in this diagnostic:

- Fill: `22 / 26 = 84.62%`
- valid EntryPosition: `22`
- mean EntryPosition: `72.11%`
- median: `49.27%`
- <=15%: `0 / 22 = 0%`
- <=25%: `3 / 22 = 13.64%`
- comparable filled entries before evaluator Low: `11 / 22 = 50.0%`

Causal witness after evaluator Low:

- first existing BUY State: median `8` active minutes; <=5 minutes only `15.38%`; <=10 minutes `80.77%`; one missing
- first frozen Signal: median `9.5` active minutes among observed; `8 / 26` missing
- first either: median `7` active minutes; <=5 minutes `26.92%`; <=10 minutes `84.62%`

There is no stable pre-Low causal marker in the frozen inputs that identifies the evaluator Low. Initial SHARP_DROP is already WAIT under the accepted policy, so a new rule would have to add a post-trigger confirmation delay or a new feature. A delay chosen from the evaluator-Low alignment would be outcome-derived; a new feature/Signal is outside authorization. With only 26 T0 observations and no clear Contract/software defect, spending the single performance trial would be weak and post-hoc.

Result: `SHARP_DROP = LIMITED_SUPPORT_NO_JUSTIFIED_SINGLE_HYPOTHESIS / HOLD`. Hypothesis budget remains `0/1`.

### DROP_STOP — N=5 — INSUFFICIENT

The cohort remains too small for a performance rule and no Contract/software defect was found. Disposition remains `INSUFFICIENT_FOR_PERFORMANCE_RULE`; no hypothesis consumed.

## Nine-State bounded-pass disposition

| State | T0 N | classification audit | performance disposition | hypothesis use |
|---|---:|---|---|---:|
| REBOUND | 192 | DONE | candidate REJECTED | 1/1 |
| RISE | 111 | DONE | candidate REJECTED | 1/1 |
| SHARP_RISE | 7 | DONE | INSUFFICIENT | 0/1 |
| DROP | 1403 | DONE | candidate REJECTED | 1/1 |
| PULLBACK | 354 | DONE | candidate REJECTED | 1/1 |
| RANGE | 57 | DONE | HOLD — no justified single hypothesis | 0/1 |
| SHARP_DROP | 26 | DONE | HOLD — limited support / no justified single hypothesis | 0/1 |
| DROP_STOP | 5 | DONE | INSUFFICIENT | 0/1 |
| RISE_STOP | 0 | code/transition audit DONE | NO_OBSERVATIONS / INSUFFICIENT | 0/1 |

All nine States now have a bounded-pass disposition. No rejected candidate is eligible for integration.

## Entry completion status

The accepted ONE_MINUTE baseline remains the reference because no new candidate passed its precommitted Gate:

- Fill: `1764 / 2155 = 81.8561%`
- valid EntryPosition N: `1751`
- mean EntryPosition: `67.4868%`
- median EntryPosition: `49.60%`
- <=10%: `9.59%`
- <=15%: `15.19%`
- <=25%: `26.73%`
- <=50%: `50.37%`
- +3 Capture: about `71.88%`
- +5 Capture: about `73.53%`

The whole-Entry mean `<15%` aspiration is not remotely met. More importantly, the bounded authorized rule space produced no accepted local performance candidate. Therefore the strict Entry completion gate is **NOT MET** and automatic transition to EXIT / Capital Allocation is prohibited.

Further performance work that could materially change this conclusion would require a separately authorized expansion such as a new Signal/feature family, Volume/Dictionary input, learned model, State semantic/threshold change, or broader Selector/Entry architecture change. None is performed here.

## Safety / exposure

Provider requests remain 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access. EXIT / Capital / Portfolio remain untouched. No main merge / production / broker / Excel order / RSS order / paper / live / automatic promotion action. All safety/write/trading flags remain false.
