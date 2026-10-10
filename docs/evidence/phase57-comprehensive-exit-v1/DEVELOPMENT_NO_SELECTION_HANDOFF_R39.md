# Phase57 — Development finite EXIT result / controlling handoff R39

Saved at: 2026-09-26 16:44:51 JST  
Basis/latest HEAD before this evidence-only save: `dfac22b842e0e110036624ef44941cb38acf4f8c`  
Controlling outcome: **NO_SELECTION_STOP — DEVELOPMENT INTEGRATION NOT COMPLETE**

## Current state and authority

The R25/R33 finite experiment has completed. All 24 precommitted configurations
were evaluated, using six shared prediction specifications, three heads, two Entry
arms and four expanding temporal folds: exactly 144 fits. No candidate passed.
No EXIT is selected/frozen, and no Capital/Portfolio historical comparison occurred.
Do not interpret successful CI as successful trading performance or promotion.

R32 Pre-Design PASS remains historical and valid for its scope. R36's original
results remain preserved, but its Owned Peak Giveback/retention reporting is
superseded ONLY by R38's bounded evaluator erratum. The R36 zero-selection result,
all actions/fills/costs/net returns and the finite grid are unchanged. Statements
in R35/R36/R37 saying fit/result is pending are superseded by this handoff.

## What actually completed

- R33/R34/R35 successful dedicated artifacts reused, not refitted.
- R36 run [36222151340](https://github.com/Iam-2squared/ark-terminal/actions/runs/36222151340)
  succeeded on `a10b3f25f79f8221c9a71c1b3ede245777bce058`.
  85 pre-fit focused tests, 144 fits, 24 policies, two replay/score passes.
- Independent local audit verified all 144 model bundle hashes, prediction hash,
  and all 50 original Run A/B files against the R36 receipt.
- R37 Capital connection was saved and its dedicated 35-test CI succeeded:
  [36227400440](https://github.com/Iam-2squared/ark-terminal/actions/runs/36227400440).
- R38 audit-only CI succeeded with 71 tests:
  [36227400437](https://github.com/Iam-2squared/ark-terminal/actions/runs/36227400437).
  Additional fits = 0; additional policy replays = 0; Portfolio replays = 0.
- Both R38 correction passes are byte-identical. Every local R38 result file also
  matches the independently executed GitHub CI result byte-for-byte.
- R23-R25 dedicated contract CI [36227400410](https://github.com/Iam-2squared/ark-terminal/actions/runs/36227400410)
  succeeded. Broad PR CI is NOT claimed all-green: unrelated legacy workflows
  have failures/running jobs, recorded in the adjacent CI snapshot. No failed
  history was erased or rerun to hide it.

## Main result (all 24 candidates, not a selected winner)

Primary sell cost 0.05 percentage points; buy-side Entry 5 bps unchanged.
These are per-trade OOF Development returns, NOT capital-weighted portfolio returns.

| Metric | IMMEDIATE | ALL_MATERIAL R1 |
|---|---:|---:|
| OOF Opportunity population | 1,267 | 1,267 |
| Frozen filled Entries | 1,150 | 1,107 |
| No Entry | 117 | 160 |
| Resolved EXIT N across candidates | 1,135–1,141 | 1,095–1,102 |
| Censored/unresolved EXIT N | 9–15 | 5–12 |
| Mean net range | −0.032876%…+0.157788% | +0.026672%…+0.286923% |
| Median net range | −0.099975%…+0.034729% | −0.099975%…+0.055369% |
| PF range | 0.947606…1.212883 | 1.054172…1.377236 |
| Mean net >= +2.00% gate passes | 0/24 | 0/24 |
| Winner Continuation gate passes | 0/24 | 0/24 |
| Profit Retention gate passes, corrected | 24/24 | 24/24 |
| Loss Containment gate passes | 24/24 | 24/24 |
| All-gate passes | 0/24 | 0/24 |

All six bucket completion gates fail for every candidate/arm. Concentration passes
48/48 arm cases. Cost stress results and every candidate-specific failure are in
`r38-result/candidate-summary.json`. Improved retention/loss containment does not
override the failed Winner Continuation and return gates. These facts do not
identify a new model, threshold or policy to try.

## Population and six-bucket interpretation

The 2,155-ID exposed Development cohort spans 58 sessions. The frozen four-fold
walk-forward scores only the last 34 sessions (1,267 Opportunities). Training and
purge rows are not scored as OOF performance. Full-cohort >=5% N=666 remains the
R31 anatomy figure, not the denominator of this OOF experiment.

| Ordered Low→strictly-later High bucket | OOF population | IMMEDIATE filled | R1 filled |
|---|---:|---:|---:|
| <1% | 85 | 60 | 57 |
| 1–2% | 220 | 200 | 183 |
| 2–3% | 246 | 234 | 226 |
| 3–4% | 151 | 144 | 140 |
| 4–5% | 106 | 103 | 103 |
| >=5% | 393 | 387 | 381 |
| Not evaluable | 66 | 22 | 17 |

Each of the 24 original and corrected full scorecards is committed under
`r38-result/original-scorecards/` and `r38-result/corrected-scorecards/`.
They preserve both Entry arms, four folds, six buckets plus not-evaluable and
metric-specific common-case paired R1-minus-IMMEDIATE results. Missing exact OPEN
counts, unresolved terminal exits and each metric's evaluable N remain distinct.

## Evaluator defect and disposition

**ACCEPT / REPAIRED:** R36's `numeric` rejects NumPy float32 scalars returned by
`_position`, making Owned Peak/time missing. It was a type-transport bug, not
universal market-data missingness. It did not change model inputs, predictions,
decisions, fills or return metrics.

R38 uses the same pinned raw source, R20 prefix/ownership rules and R21 kernel,
restores the original float32 peak as a Python scalar at the original decision
endpoint, and changes only `metrics.ownedPeakGivebackPp`. The corrected
retention scorecards/gates replace only those erroneous original reports.
Incomplete owned prefixes remain uncertified, and exit-candle H/L remain excluded.
All original evidence is retained. No estimator is fitted or policy replayed again.
The NO_SELECTION result was already independently forced by all 48 primary net
gate failures and remains identical after the repair.

Run A/B proves replay/evaluation reproducibility from a shared immutable OOF
prediction set; it does NOT claim two independently repeated estimator fits.

## Artifact identities and retention

| Checkpoint | Artifact ID | ZIP SHA256 |
|---|---:|---|
| R36 finite experiment | 10901042535 | `1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a` |
| R37 Capital prep | 10900329618 | `d2c121c9beea52208a5fbd10eb4fc94e037ac61fb2cd87f61703916cd54e8863` |
| R38 corrected audit | 10901355944 | `993c3a744b971ae8ccada9784a2c26180beb2abfd3c9c46e8b854ba28ce2f510` |

All three ZIPs were downloaded and independently SHA-256 verified.
OOF predictions SHA256:
`1c24a5ff04ba759c00b5cdc517f1a0ab037357658dca95f5497ed8af149d8ca8`.
Model identities, original/corrected selection details, audit hashes and full
scorecards are committed in `r38-result/`; CI keeps the complete ledgers/model
bundles/predictions. These Actions artifacts expire on **2026-10-26**; preserve
them before expiry if future raw model/ledger reconstruction is required. This
handoff does not falsely claim indefinite Actions retention.

## Capital lane: ready primitives, no integration claim

R34/R35 cash-only rule plus R37 interface/synthetic tests are implemented:
confirmed EXIT cash release → fresh NOW MTM → causal rank → MAX3/4/5 100-share
sizing. Missing mark prevents new sizing. Unresolved EXIT releases neither cash
nor capacity. Future bucket/PnL/capture fields cannot enter the intent allowlist.
Only MAX3 primary / MAX4 and MAX5 sensitivities exist.

There is no SELECT token or frozen EXIT to connect, so there is no historical
Portfolio result, final Entry comparison, capital reach/share/capture result,
production adapter qualification or Development integration PASS. The generic
score/attribution interfaces remain preparation, not a validated final portfolio.

## Freeze / exposure / Safety9

Frozen Entries remain `IMMEDIATE` and `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`,
Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`. No Entry changes.
Old Fixed12/Candidate A remain historical only; no reuse as baseline/fallback.
No new feature/model/alpha/threshold/persistence or 25th candidate.

The 2,155 Opportunities are outcome-exposed Development, NOT Fresh/OOS.
Common Holdout, REPORT19, Validation, OOS, Fresh and Prospective remain sealed.
Provider requests = 0; protected opens = 0.
All false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed,
rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed,
automaticPromotionAllowed, productionUpdateAllowed, transmitted.
No main merge, force push, live/paper/production.

## Hard blocker and next authorized step

The authorized finite experiment is exhausted with NO_SELECTION_STOP.
**STOP research here. Do not continue automatically to another candidate or
provisional EXIT Portfolio comparison.** The next step requires a user decision
whether to authorize a separately bounded follow-up research plan. Any such plan
must be append-only and precommitted before additional performance inspection;
current failures must remain visible. Until then, preserve this result and the
tested Capital preparation. There is no selected EXIT or final Entry winner.

