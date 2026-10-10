# Phase57 Dual Entry -> EXIT -> Capital Integration Plan R11

Date: 2026-09-25 JST  
Repo: Iam-2squared/ark-terminal  
Branch: research/phase57-long-only-cash-equity  
PR: #587

## Status

Entry research is closed for the current Development pass.

Frozen Entry candidates:

1. `IMMEDIATE`
2. `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`

Controlling dual-freeze evidence:

- commit: `4878a1cc53430e816261dea0fb16aeb53b3c238d`
- `docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json`

Older Entry policies (Entry v1, original State-v3, ONE_MINUTE and prior experiments) remain immutable historical Evidence. They are not deleted or rewritten, but they are no longer final Entry candidates for the next integration stage.

No additional Entry feature/model/horizon/probability-threshold optimization is authorized in this integration plan.

## Why two Entry policies remain

### IMMEDIATE

Strengths:
- selector denominator 2,155 preserved
- Fill 91.09%
- Median EntryPosition 42.26%
- <=10/15/25/50 case rates 18.69/24.65/35.73/55.77%
- Low->Entry mean 251.33 bps
- strong +1/+2/+3/+5 Capture: 85.23/85.58/85.28/87.50%
- ordered Low->strictly-later-High >=5% group (N=666) Mean EP 44.36%

Weaknesses:
- Mean EP 65.40%, worse than All-Material R1
- Entry->strictly-later-High mean 272.90 bps, lower than R1
- adverse excursion is worse than R1 on the canonical 30m/60m comparison

### ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF

Source:
- workflow run `36099497597` SUCCESS
- artifact `10851958443`
- artifact digest `sha256:33a0f64d48d25701215dadb82b9769a9c3bde2b9fec3d82d9879706f8f90e1a0`
- Run A / Run B byte-identical PASS

Strengths:
- Fill 87.47%
- Mean EP 61.53%, best of the final compared Entry family
- Entry->strictly-later-High mean 288.66 bps, better than Immediate
- lower Mean EP than Immediate in ordered range buckets <1%, 1-2%, 2-3%, 3-4%, and 4-5%
- improved 30m/60m MAE relative to Immediate/ONE_MINUTE
- finite precommitted temporal Nested/OOF protocol; no result-following Entry optimization after the one-shot result

Weaknesses:
- Fill lower than Immediate
- Median EP 46.09%, worse than Immediate
- <=10/15/25/50 case rates lower than Immediate
- +1/+2/+3/+4/+5 Capture about 67.81-70.66%, materially lower than Immediate
- ordered >=5% group Mean EP 46.03%, slightly worse than Immediate 44.36%

Therefore Entry-only metrics do not select the final integrated Entry. The final choice is deferred until both policies pass through identical EXIT and Capital semantics.

## Next stage: Frozen EXIT integration

Use the latest Frozen NEW LONG EXIT candidate first:

`NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` (Candidate A)

Do not retune its thresholds.

Policy semantics:
- HOLD by default
- first completed regular 5m HIGH >= entry +3% arms PROTECT
- first later completed regular 5m CLOSE <= entry +1% emits EXIT signal
- execution reference is next regular 5m OPEN
- if not triggered, use exact Fixed12 terminal cap
- round-trip cost = 0.05 percentage points
- do not add loss-defense, BAR5, two-lower-closes, re-entry, or learned EXIT logic

The existing Candidate A implementation is tied to an older INITIAL/DIP Entry substrate. Build an integration adapter that maps each frozen final Entry ledger to the approved post-entry regular-5m path substrate while preserving Candidate A policy bytes/thresholds and causal event ordering.

Required EXIT comparison:
- IMMEDIATE + Candidate A
- ALL_MATERIAL_R1 + Candidate A
- identical Opportunity lineage, cost, path, timestamp and fill semantics
- paired comparison where both policies are evaluable
- Fixed12 comparator under the same Entry ledger
- return distribution, mean/median net return, PF, win rate, p05/worst, holding time, exit reason, +3/+5 preservation, missing/evaluable counts
- reproducibility and leakage/causality checks

Entry full future paths may be used only after Entry is frozen as evaluator/EXIT replay data. They must never flow backward into Entry decisions.

## Capital Allocation stage

Do not reuse the old 277-Entry Capital performance as if it were comparable. The existing integration is tied to an older Entry and older EXIT.

After EXIT integration is frozen, construct a new ledger for each:

- IMMEDIATE + Candidate A
- ALL_MATERIAL_R1 + Candidate A

Preserve:
- initial cash JPY 1,000,000
- LONG cash equity only
- 100-share lots
- cash nonnegative
- existing transaction cost semantics
- existing completed-bar -> EXIT/cash release -> new Entry event ordering
- unresolved/missing positions must remain explicit and lock capital where required
- no future PnL/MFE/MAE/EXIT outcome in allocation decisions

Start with existing simple reference allocation architecture such as Equal/MAX3 under identical conditions. Do not perform an unbounded result-following allocation grid.

Required Portfolio comparison:
- final equity and return
- Max Drawdown
- PF / win-loss statistics where contractually defined
- capital utilization / capital lock
- concurrent positions
- rejected/deferred entries due to cash constraints
- symbol/session/time concentration
- contribution concentration
- paired opportunity/trade lineage
- deterministic replay
- safety flags

The final Entry choice is made only after this end-to-end Development comparison.

## Data / Evidence boundaries

The 2,155 selector Opportunities are outcome-exposed Development data. They are not Fresh/OOS.

Do not newly open:
- Common Holdout
- REPORT19
- Validation
- OOS
- Fresh
- Prospective

Provider new acquisition: 0.

Evidence is append-only. Do not overwrite prior formal Evidence or erase failed/rejected trials.

GitHub Actions artifacts are expiration-bound unless separately persisted in an approved durable location. Do not call an expiring artifact permanently preserved.

Do not force push or overwrite another worker's changes. Re-read latest HEAD, commits, CI and controlling Evidence before every mutation.

## Safety

Keep all false:

- executionAllowed
- brokerWriteAllowed
- excelOrderWriteAllowed
- rssOrderFunctionAllowed
- liveTradingAllowed
- paperTradingAllowed
- automaticPromotionAllowed
- productionUpdateAllowed
- transmitted

No main merge, production promotion, live trading or paper trading is authorized by this plan.

## Completion target for the next phase

Produce two directly comparable Development pipelines:

`Frozen Selector -> IMMEDIATE -> Candidate A -> Capital -> Cash Equity Portfolio`

`Frozen Selector -> ALL_MATERIAL_R1 -> Candidate A -> Capital -> Cash Equity Portfolio`

Then compare them under identical causal data, cost, event-ordering and allocation semantics and preserve the complete lineage/hashes/CI receipts. Do not call the result Fresh/OOS validated, production-ready, or live-ready.
