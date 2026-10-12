# Dual frozen Entry -> Candidate A / Fixed12: R14 result

## Scope and integrity

Controlling Entry dual freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`.
Adapter preregistration/implementation: `416595cc824068fb34abcdc2e2bc368e8c155831`.
Workflow `36115061827`, job `108007095280`: SUCCESS. 26 synthetic tests pass.
Run A/B and local/CI agree byte-for-byte on all five output files.
All 2,155 current, outcome-exposed Development opportunities retained per Entry;
58 frozen evaluation sessions. Provider requests and newly opened protected partitions: zero.
No Entry model/refit/reselection or Frozen Candidate A/Fixed12 source change.

## Within-Entry paired comparison

Each row pair uses the same filled and EXIT-evaluable identities, not different denominators.
Returns are unit-notional reference trade returns, NOT portfolio returns.

|Entry|EXIT|Paired N|Mean net %|Median net %|PF|Win %|p05 net %|Worst net %|Mean clock minutes|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|IMMEDIATE|Fixed12|1118|-0.076639|-0.099975|0.934604|45.3488|-5.186266|-17.295678|67.9401|
|IMMEDIATE|Candidate A|1118|-0.054139|-0.099975|0.950482|46.3327|-4.768918|-17.295678|64.8327|
|ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF|Fixed12|1105|-0.125400|-0.099975|0.890843|44.8869|-4.852976|-20.257963|74.5710|
|ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF|Candidate A|1105|-0.083436|-0.099975|0.921115|45.8824|-4.508773|-20.257963|71.4751|

Both Entry arms improve relative to Fixed12, but Candidate A mean net remains
negative and PF below one. Do not call this absolute profitability PASS.

## Cross-Entry under the same Candidate A

Use the 1,101 opportunities resolved under Candidate A in BOTH Entry arms:

|Entry|N|Mean net %|PF|Win %|p05 net %|Mean clock minutes|
|---|---:|---:|---:|---:|---:|---:|
|IMMEDIATE|1101|-0.078085|0.928821|46.5032|-4.760857|64.4859|
|ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF|1101|-0.084914|0.919873|46.0490|-4.509535|70.8383|

R1 minus Immediate mean net: -0.006829 percentage points on this common set.
This small conditional difference does not choose the final integrated Entry.
The four-cell common-resolved set is 1,093; full tables remain in artifact summary.json.

## Availability and preservation

|Entry|All opportunities|No Entry|Frozen fills|Fixed12 resolved|Candidate resolved|Candidate unresolved|Candidate-only resolved|
|---|---:|---:|---:|---:|---:|---:|---:|
|IMMEDIATE|2155|192|1963|1118|1133|830|15|
|ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF|2155|270|1885|1105|1115|770|10|

Immediate +3 preservation: 305/305 (100%). +5 legacy-slot: 137/145 (94.4828%);
strict ownership-time: 136/145 (93.7931%). One EXIT-bar HIGH occurred after the
OPEN exit and is not owned. R1 +3: 290/290 (100%); +5: 129/137 (94.1606%) under
both definitions. Preservation is not the Entry-stage Capture metric.

Candidate A unresolved first-gap at 15:30: Immediate 202, R1 217. Other missing
regular buckets account for the remaining 628 / 553 unresolved fills. Terminal
geometry alone is not the whole coverage problem.

## Adapter assumptions (preregistered, not retuned)

Actual frozen Entry price/time preserved. 529 Immediate and 621 R1 fills are
off-grid. Only complete calendar-anchored buckets wholly after Entry are used;
09:31 Entry stays 09:31 and first eligible bar is 09:35-09:40. This is an explicit
off-grid adapter convention, not a claim that the old INITIAL/DIP contract covered it.
Sparse OPEN references use actual first source-minute timestamps, never backdated.
Keep the inherited 15:30 calendar, missing 15:25-15:30 bars, and no auction substitution.

Final Entry prices already include 5bps buy slippage. Preserve those prices and
subtract frozen EXIT round-trip cost 0.05pp once; total friction is NOT all-in 5bps.
All results are reference-price Development measurements, not executable fills.

## Capital handoff

Use every final R13 ledger row. Never filter by resolved EXIT, future PnL, MFE,
MAE or future State. Frozen capital contract uses initial JPY1,000,000, lot100,
budgetDivisor3 and **maximumConcurrentPositions10**. MAX3 denotes budget division,
not a three-position cap. Preserve exact costs, event ordering and unknown-price
rules. Compare ONE_LOT_REFERENCE and EQUAL_MAX3 first; do not fabricate rank/risk
inputs or reuse old277 results. No final Entry winner, main merge or promotion.

Full artifact: 10855136419, expires 2026-10-25T08:50:29Z (not permanent storage).
Hashes and verification receipt: EXIT_RECEIPT_R14.json. Safety flags all false.
