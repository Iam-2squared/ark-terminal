# Phase57 9-State Entry Audit — PROGRESS R7

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## Scope

`PROTOCOL_R0.md` remains controlling. This append-only receipt records post-freeze semantic scoring and current Development anatomy. It does not change the frozen 9-Pattern Contract, Frozen Selector, six signals, original State-v3 baseline, saved DROP/PULLBACK one-minute baseline, or protected-data boundary.

## Git / CI identity re-read before this receipt

- source HEAD: `bb44dfaf149b801c4f1af0acd7f78bd557303676`
- PR #587: OPEN / DRAFT / unmerged
- REBOUND post-freeze score run `35850842830`: SUCCESS
- RISE/SHARP_RISE packet run `35861113436`: SUCCESS
- remaining-State packet run `35861980443`: SUCCESS
- Nine-State Anatomy v2 run `35865844490`: SUCCESS
- REBOUND candidate run `35865392687`: SUCCESS

## Post-freeze semantic score

Every review below was frozen with `chartInspected=YES` before the corresponding sealed map was used for scoring. Exact State agreement measures agreement with the fixed Contract/baseline on the deliberately mixed review samples; it is not a population accuracy estimate and does not mean every chart was visually unambiguous.

| audit lane | reviewed | exact match | rate | reviewer/blob identity | sealed source |
|---|---:|---:|---:|---|---|
| REBOUND mixed with RISE | 34 | 34 | 100% | `afb66ff0ee9dedc824f558e15d587da1f2390682` | artifact `10745366281`; dedicated score artifact `10744689791` |
| RISE mixed with REBOUND/SHARP_RISE | 36 | 36 | 100% | `5fbf2ab1d1f310f5d430ae68f4ae4128596c008c` | artifact `10749979582`; sealed SHA256 `5d44d63f0d1bbe9f6c57bf006c176a5445aa62c9ab21c7e568bd89c0f8a56deb` |
| SHARP_RISE mixed with RISE | 19 | 19 | 100% | `92d56abb0e00bf3cbcd6b42f6543c68761c98b30` | artifact `10749979582`; sealed SHA256 `cc2b3d74c154387364fb646fdee5b2cb6bd78bc60869b361f04bc6320c5b1558` |
| DROP mixed with PULLBACK | 36 | 36 | 100% | `c90cff55956ab5c7831a2c078bed0b08c05cbc43` | artifact `10750819100`; sealed SHA256 `ebc5a5e2bbc5707f14c8c5a410ad0810f753a7ca5d0b82190fdc2bab8dd44507` |
| PULLBACK mixed with DROP | 36 | 36 | 100% | `092f0803b6308322cf793464dd386438ef4218a4` | artifact `10750819100`; sealed SHA256 `844eda0df23199bf10d6c0faeb1a701321182e0dc662a0d27b55b169e69d72aa` |
| RANGE mixed with DROP | 36 | 36 | 100% | `aa007be62bdbec639a06288ed9d81d4055781842` | artifact `10750819100`; sealed SHA256 `2f5555e915e6ef29923a62e98d5e58fab9f0354ad23ba82954ee9dd777495b69` |
| SHARP_DROP mixed with DROP | 36 | 36 | 100% | `7d7becebb852c476269b08fa3e3dded6814f011a` | artifact `10750819100`; sealed SHA256 `74393e51fd597173f2115dbccfc8ed798fbc09ba75f52dc915e5e968fadb2ada` |
| DROP_STOP mixed with DROP/RANGE | 17 | 17 | 100% | `2446ed280959ab43c6771bf90450fc7de8a4c524` | artifact `10750819100`; sealed SHA256 `8ad36eb3702d4efbca174332629923eb68a04344a082e3d5773d871891bcc4f2` |

The RISE/REBOUND equality boundary and SHARP_RISE/SHARP_DROP shock-context cases still contain explicitly recorded semantic ambiguity. Therefore 100% exact agreement is implementation/Contract consistency evidence on reviewed cases, not proof that the vocabulary is visually natural or independently generalizes.

## RISE_STOP

The frozen transition census in artifact `10750819100` reports:

- `t0Population=0`
- `laterCheckpointRows=0`
- `uniqueOpportunities=0`
- `sessions=0`
- `prefixOnly=true`
- `outcomeOpened=0`

Disposition remains `NO_OBSERVATIONS / INSUFFICIENT_FOR_PERFORMANCE`. No threshold is relaxed to manufacture observations.

## Current Development EntryPosition anatomy

Nine-State Anatomy v2 is evaluator-only and uses the fixed original T0 cohorts. Overall ONE_MINUTE baseline remains far from the aspirational completion target:

- fills: `1846 / 2155` = `85.6613%`
- valid EntryPosition N: `1530`
- mean EntryPosition: `0.674877` = `67.49%`
- median EntryPosition: about `75.43%`
- <=15% case rate: `13.0719%`
- <=25% case rate: about `15.22%`

State-level ONE_MINUTE mean EntryPosition:

- REBOUND `67.81%` (valid N 164)
- RISE `61.76%` (valid N 90)
- SHARP_RISE `46.78%` (valid N 4; insufficient support)
- DROP `68.11%` (valid N 1039)
- PULLBACK `68.73%` (valid N 244)
- RANGE `52.42%` (valid N 5; fill only 10.53%)
- SHARP_DROP `60.21%` (valid N 10; limited support)
- DROP_STOP `86.26%` (valid N 4; insufficient support)
- RISE_STOP no observations

The saved one-minute intervention remains confined to DROP/PULLBACK as expected. Versus State-v3 on common filled cases, mean EntryPosition delta is approximately `-0.00144` for DROP and `-0.02560` for PULLBACK; it does not approach the <15% overall target.

## Trial ledger update — REBOUND hypothesis 1/1

The single precommitted REBOUND confirmation candidate was measured and is REJECTED.

- baseline REBOUND fill: `100%`
- candidate fill: `38.02%`
- candidate valid EntryPosition mean: `30.69%`
- candidate median: `24.19%`
- candidate <=25%: `51.06%`
- common paired EntryPosition: candidate `30.69%` vs baseline `44.17%`, delta `-13.48pp`
- common +3/+5 Capture: unchanged at `100%`
- causal checks: PASS
- rejection reason: fill loss `61.98pp`, far beyond the precommitted `5pp` tolerance; this behaves like an Opportunity-dropping second Selector.

REBOUND unattended performance-hypothesis budget is consumed. No result-driven threshold retuning is permitted in this bounded pass.

## Current disposition / next work

- Semantic review + sealed Contract-consistency audit: complete for all eight nonzero-T0 States.
- RISE_STOP: no observations; performance evidence insufficient.
- Material classifier implementation mismatch found in reviewed samples: none.
- Entry timing quality: still materially inadequate overall (`67.49%` mean vs aspirational `<15%`).
- REBOUND candidate: rejected; no further unattended retuning.
- SHARP_RISE / DROP_STOP: too small for a reliable new performance hypothesis.
- RANGE / SHARP_DROP: support limitations must be respected.
- RISE / DROP / PULLBACK remain the highest-support lanes for causal timing attribution before deciding whether their single allowed new hypotheses are justified.

Entry completion gate is NOT met. EXIT and Capital Allocation remain untouched by this audit.

## Safety / exposure

Provider new requests 0. No new Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access. No future Low/High/MFE/MAE/Capture was used in reviewer decisions or Entry decision logic. No main merge / production / broker / Excel order / RSS order / paper / live / automatic promotion action was performed. All safety/write/trading flags remain false.
