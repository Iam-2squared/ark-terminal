# Phase57 9-State Entry Audit — PROGRESS R10 / Confirmed BUY Persistence Results

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## Scope

`PROTOCOL_R0.md` remains controlling. This append-only receipt records the first and only unattended performance hypotheses for `RISE`, `DROP`, and `PULLBACK`, all precommitted in `CONFIRMED_BUY_PERSISTENCE_HYPOTHESES_R1.md` before candidate replay. It does not alter the frozen 9-Pattern Contract, six frozen Signals, Frozen Selector, or accepted baselines.

`PROGRESS_R8.md` remains the authoritative correction for ONE_MINUTE baseline anatomy; `PROGRESS_R9.md` records the pre-measurement Low-centered diagnosis and hypothesis freeze.

## Exact run / artifact identity

- source HEAD: `0996a1f643ed7fdb5d535fc66ee2b41376dfc3d4`
- workflow: `Phase57 Confirmed BUY Persistence Candidates R1`
- run: `35897369272`
- job: `107304537350`
- conclusion: `SUCCESS`
- artifact: `10767577373`
- artifact digest reported by Actions: `sha256:9ca0460eacaa133f325e02165dc787765d58a73ef1b31b560a18f8bd39ea4174`
- population: `2155`
- candidate replay performed twice with deterministic directory diff: PASS
- focused syntax + frozen regression tests: PASS
- approved evaluator substrate hash verification: PASS
- accepted ONE_MINUTE artifact hash verification: PASS
- causal isolation guard: PASS

Causality receipt:

- closed-bar checks: `322978 / 322978` PASS
- signal closed-bar checks: `377450 / 377450` PASS
- future-suffix rows checked: `4104`; violations `0`
- State future violations: `0`
- Oracle Low/High decision use: `0`
- future-outcome decision use: `0`
- provider requests: `0`
- protected data opened: `0`
- State-v3 Contract changed: `false`
- frozen Signal definitions changed: `false`

## Precommitted gate results

All three candidates used the exact same fixed rule family `CONFIRMED_BUY_PERSISTENCE_V1`: target State only, first checkpoint with either BUY-State + existing frozen Signal concurrence, or two consecutive existing BUY-State observations. Non-target Opportunities remained exact ONE_MINUTE baseline.

### RISE — hypothesis 1/1 — REJECT

| metric | ONE_MINUTE baseline | candidate | delta / paired interpretation |
|---|---:|---:|---:|
| Fill | 77.4775% | 74.7748% | **-2.7027pp FAIL** |
| EntryPosition mean | 62.8843% | 58.7667% | aggregate lower, but not sufficient |
| EntryPosition median | 41.2800% | 44.6150% | worse |
| <=15% | 18.0723% | 14.8148% | **-3.2575pp FAIL** |
| <=25% | 33.7349% | 27.1605% | **-6.5744pp FAIL** |
| +3 Capture | 76.7442% | 67.4419% | **-9.3023pp FAIL** |
| +5 Capture | 75.0000% | 62.5000% | **-12.5000pp FAIL** |
| Low->Entry mean distance | 2.5945% | 2.6679% | worse |

Common filled/evaluable paired EntryPosition delta was `-0.003605` (about `-0.36pp`, favorable), but paired Low->Entry distance delta was `+0.08815pp` (worse). The preservation and threshold-rate gates fail, so this candidate is rejected despite the small paired EntryPosition improvement.

### DROP — hypothesis 1/1 — REJECT

| metric | ONE_MINUTE baseline | candidate | delta / paired interpretation |
|---|---:|---:|---:|
| Fill | 76.7641% | 72.9152% | **-3.8489pp FAIL** |
| EntryPosition mean | 67.7651% | 68.4218% | worse |
| EntryPosition median | 51.7142% | 51.9373% | worse |
| <=15% | 13.2586% | 10.7073% | **-2.5514pp FAIL** |
| <=25% | 24.9300% | 21.2181% | **-3.7119pp FAIL** |
| +3 Capture | 67.4779% | 60.6195% | **-6.8584pp FAIL** |
| +5 Capture | 71.4894% | 64.2553% | **-7.2340pp FAIL** |
| Low->Entry mean distance | 2.6108% | 2.7090% | worse |

Common-case paired EntryPosition delta was `+0.019280` (about `+1.93pp`, worse) and paired Low->Entry distance delta was `+0.11984pp` (worse). All performance-preservation / timing gates fail. Candidate rejected.

### PULLBACK — hypothesis 1/1 — REJECT

| metric | ONE_MINUTE baseline | candidate | delta / paired interpretation |
|---|---:|---:|---:|
| Fill | 92.9379% | 88.4181% | **-4.5198pp FAIL** |
| EntryPosition mean | 62.5865% | 61.3795% | aggregate appears lower |
| EntryPosition median | 46.1014% | 45.8542% | slightly lower |
| <=15% | 15.3846% | 13.5922% | **-1.7924pp FAIL** |
| <=25% | 29.2308% | 24.9191% | **-4.3117pp FAIL** |
| +3 Capture | 72.0238% | 62.5000% | **-9.5238pp FAIL** |
| +5 Capture | 68.8172% | 60.2151% | **-8.6022pp FAIL** |
| Low->Entry mean distance | 3.0268% | 2.9908% | aggregate slightly lower |

The aggregate mean is misleading because the filled set changed. On common cases, paired EntryPosition delta was `+0.014339` (about `+1.43pp`, worse) and paired Low->Entry distance delta was `+0.12502pp` (worse). Candidate rejected.

## Trial-budget disposition

- REBOUND: hypothesis `1/1` already consumed and rejected on run `35865392687`.
- RISE: hypothesis `1/1` consumed and rejected on run `35897369272`.
- DROP: hypothesis `1/1` consumed and rejected on run `35897369272`.
- PULLBACK: hypothesis `1/1` consumed and rejected on run `35897369272`.
- No result-driven persistence-length change, threshold sweep, alternate feature, new Signal, Volume, Dictionary or learned model is permitted for these States in this bounded unattended pass.

No candidate from these four States is eligible for integration. The accepted ONE_MINUTE baseline remains unchanged.

## Remaining States / independent diagnostic

`SHARP_RISE`, `RANGE`, `SHARP_DROP`, and `DROP_STOP` have not consumed a performance hypothesis. A diagnostic-only causal Low-centered run is separately precommitted in `REMAINING_STATE_LOW_CENTERED_DIAGNOSTIC_R1.md`; it must not manufacture a performance trial from tiny samples. `RISE_STOP` remains `NO_OBSERVATIONS / INSUFFICIENT_FOR_PERFORMANCE`.

## Current completion status

Entry completion gate remains **NOT MET**. The authoritative accepted ONE_MINUTE full-population baseline remains:

- Fill: `1764 / 2155 = 81.8561%`
- valid EntryPosition N: `1751`
- mean EntryPosition: `67.4868%`
- median: `49.6029%`
- <=10%: `9.5945%`
- <=15%: `15.1913%`
- <=25%: `26.7276%`
- <=50%: `50.3712%`
- +3 Capture: `71.8791%`
- +5 Capture: `73.5294%`

The aspirational whole-Entry mean `<15%` gate is far from met. EXIT and Capital Allocation remain untouched.

## Safety / exposure

Provider requests 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access. No main merge / production / broker / Excel order / RSS order / paper / live / automatic promotion action. All safety/write/trading flags remain false.
