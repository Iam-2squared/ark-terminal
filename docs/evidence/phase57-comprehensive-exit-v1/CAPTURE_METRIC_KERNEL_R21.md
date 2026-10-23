# Phase57 — EXIT value capture metric kernel R21

Date: 2026-09-25 JST. Basis HEAD: db423414ef6529829e883c915954fb51a95a8668.
Controlling direction: R18 zero-base EXIT and its six opportunity-size buckets.
Status: **EVALUATOR_KERNEL_IMPLEMENTED_SYNTHETIC_TESTED_NO_CANDIDATE_PERFORMANCE**.

## 現状と今回の実作業

While the R20 full observation census runs, implement the requested capture
arithmetic as a separate evaluator-only module with 24 synthetic tests. This
module is never imported by the EXIT-NOW observer. It reads no real cohort or
future price archive and does not generate a SELL decision, train a model or
compare the retired EXIT policies.

R20 execution db423414, workflow36128852207, had passed mandatory core/canonical
producer tests and was running its two full-cohort censuses when this checkpoint
was prepared. Completion and counts require a later actual CI/artifact receipt;
this document does not certify their completion. Initial R20 import dependency
failure and repair remain recorded in CI_DEPENDENCY_REPAIR_R20_1.md.

## Fixed mathematical meanings — different highs are never silently mixed

Let E be unchanged effective Entry price, X actual resolved EXIT reference,
L_o/H_o the SAME canonical strictly-ordered Low/later-High pair used to define
an Opportunity, and H_e the best observed High STRICTLY AFTER Entry in the
separately frozen common evaluation horizon. H_o need not equal H_e.

|Quantity|Formula|Meaning|
|---|---|---|
|Opportunity range %|100*(H_o-L_o)/L_o|Defines common <1/1-2/2-3/3-4/4-5/>=5 buckets|
|Whole-opportunity capture %|100*(X-E)/(H_o-L_o)|What portion of the original price span Entry→EXIT realized|
|Entry→same ordered High %|100*(H_o-E)/E|Remaining move to the SAME ordered High, only when later than Entry|
|Same-High upside capture %|100*(X-E)/(H_o-E)|Conversion of that positive remaining move into realized movement|
|Entry→post-Entry best High %|100*(H_e-E)/E|Available upside using the separately identified post-Entry maximum|
|Post-Entry upside capture %|100*(X-E)/(H_e-E)|Requested realized/available post-Entry upside measure|
|Entry→EXIT gross %|100*(X-E)/E|Realized reference-price movement|
|Entry→EXIT net %|gross minus explicitly supplied cost_pp|Separate from raw geometric capture; no default inherited cost|
|High-to-EXIT evaluator gap pp|100*(H-X)/E|Can include a High AFTER EXIT; NOT owned profit giveback|
|Owned peak giveback pp|100*(max(E,X,verified owned peak)-X)/E|Only if the owned path is complete and peak was confirmed by EXIT|

Keeping both whole-opportunity and remaining-upside capture avoids ambiguity in
'how much of the Low→High move was taken'. Keeping H_o and H_e separate avoids
replacing the canonical Entry geometry with whichever High makes EXIT look better.
Both high definitions must use the SAME fixed horizon when supplied together.
No arithmetic kernel can prove that a caller supplied the true maximum: the
canonical raw join, coverage definition, source hash and horizon must be audited
in the later evaluator adapter. R21 does NOT reproduce the historical N=666.

## Denominators, coverage and ownership

Use unrounded range for half-open buckets: (0,1), [1,2), [2,3), [3,4), [4,5),
[5,infinity), with NON_POSITIVE_RANGE and UNAVAILABLE separate. Do not silently
place missing or degenerate cases in a winning bucket.

A geometric ratio with nonpositive denominator is null with a reason, never
0, epsilon-divided or made positive. Negative and >100% ratios are not clipped.
A >100% result against H_o is a diagnostic of the declared geometry, not permission
to replace H_o with H_e. Investigate impossible source geometry upstream.

No Entry remains NO_ENTRY with null return/capture. An unresolved EXIT remains
UNRESOLVED with null realized returns, but known evaluator upside is retained.
Partial geometry has an observed bucket separately; it is not certified as a
complete bucket. COMPLETE is always qualified by the named audited canonical
coverage definition; this helper must not change that definition or claim that
legacy observed-slot coverage proves every 1m was present. Preserve strict-1m
coverage separately when wiring the cohort. Valid realized return is not erased
just because the full opportunity geometry is unknown.

An owned peak must be confirmed AFTER Entry and no later than EXIT. The HIGH of
a candle that starts at EXIT OPEN is not yet known and is not owned. A later
outside-ownership High may remain the available-upside denominator, but its gap
is reported as missed opportunity, not giveback of previously owned profit.

## Tests and implementation

- scripts/phase57_exit_capture_metrics_v1.py: pure, evaluator-only kernel.
- scripts/test_phase57_exit_capture_metrics_v1.py: 24 synthetic tests PASS locally.
- Dedicated small CI runs only these tests, without re-running the R20 census.
- Tests cover all bucket edges, two High identities, different horizon rejection,
  no Entry, unresolved EXIT, partial coverage, nonpositive denominator, negative
  and >100% capture, explicit costs, and no after-EXIT peak ownership credit.

These are arithmetic/contract tests, not 24 trading experiments. No new EXIT
candidate performance has been inspected. The per-trade kernel is NOT the full
aggregate scorecard, a model/search freeze or an execution/terminal contract.

## 今後の方針

Finish and independently audit R20 census receipts and the actual Pattern-v2
registry. Complete EXIT-time feature recomputation/admission and declare NEW
EXIT execution, terminal and missing-reference semantics. Then wire canonical
ordered/high evaluators to this kernel with fixed cohort/horizon/coverage IDs.
Report all 2,155 Opportunities per Entry, each bucket's evaluable/missing counts,
per-trade mean/median ratios separately from ratios of aggregate moves, and
correct paired IDs. Do not select only complete profitable cases for Entry/Capital.
The full return/downside/concentration scorecard and finite candidate/search
selection rules still need precommit BEFORE candidate performance inspection.

Entry Dual Freeze4878a1cc unchanged; Fixed12/Candidate A historical only. New
provider requests, model fits, candidate evaluations and protected opens are0.
Safety9 allfalse. Evidence append-only; no main merge/force push/live/paper/
production. The hourly automation remains paused.
