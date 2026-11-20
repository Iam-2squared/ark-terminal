# ¥75 Selector overlay — lineage and audit record

Date: 2026-09-18 JST. Research branch / Draft PR #587 only.

The human-defined policy was committed before implementation and before measuring
this overlay: `dd93029c7e1b68ba8f0d030740c055ea81ef0fc1`.
The price is not optimized, swept or selected by measured performance.
Existing Development outcomes and the previous MAE attribution were already known
before the user specified the policy. This work is not fresh validation.

- Starting remote HEAD: `a42c6c3573c2fe868d5d3288dae1abb69de40f61`.
- Parent frozen predictive Selector: `565d74b3dea823581fdb32380113aac5913a248d`.
- Parent payload: `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59`.
- Policy digest: `b991d0ececd4719318d8bd60bc98fa03e782cd56bef9af4bddce5c3294c26120`.
- Frozen Entry snapshot: `6fabde7dfe208e19d5611e0a290b4df6724e562e`.
- Candidate A: `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1`, unchanged.
- Prior EXIT Development limit and Candidate C KILL remain in force.

## Numeric serialization audit

The existing parent pandas CSV parser may differ from raw JSON score values by
floating-point serialization precision. A pre-measurement transport check of the
3,800 saved scores found 486 representation differences, with maximum absolute
difference 2.842170943040401e-14. The cross-format source check therefore allows
at most 1e-12 absolute difference and reports its actual count and maximum.

This is not score rounding, ranking tolerance, or a price tolerance. Old/new
scores in the same measurement frame must be exactly identical. Score ordering
uses the original floats, including distinctions smaller than 1e-12. The original
selected identities, original ranks and Decision Prices must match the frozen
ledger exactly. A dedicated test verifies that adjacent floats remain ordered.
The price rule has no tolerance: exactly 75 is ineligible.

Implementation commit `37363ccdf286ac29409abc78a8662899221080b3` was superseded by
`92595219285bade4c18a60c1704f811346ea503c` for this serialization check only.
The unfinished impact jobs 35335853270 and 35336201453 were cancelled when the
latest job superseded them, before impact measurement was completed. Their GitHub
history is retained. No performance result was used to alter the policy.
Commit `dee68ee333f28679399c564b9d7f24efd43a5a0d` permits cancellation only within
this new impact workflow's concurrency group, to avoid redundant unfinished runs.

## Population and denominator safeguards

1. Use all 76 saved Development sessions and 760 decision timestamps.
2. Apply parent eligibility, then the human price gate, before ranking / Top5.
3. Report eligible-universe recall per arm and common-old-universe recall.
4. Future-path coverage never determines eligibility or replacements.
5. Replay the exact Frozen Entry only for new first-per-symbol-session anchors;
   reuse saved decisions for identical anchors. Report retained/removed/added
   populations separately. Opportunity events are not funded ENTER/fills.
6. Use the prior contiguous-six-completed-5m strict30 definition for Entry MAE,
   not the different Selector endpoint evaluator. Preserve missing/boundary rows.
7. Test the old 17-yen identity using its Selector Decision Price, not Entry price.
8. No EXIT replay is needed for this policy impact audit. Prior A evidence stays
   associated with the original Selector lineage.
9. Symbol exclusions in concentration diagnostics use the old selection frequency
   top three on both arms; they never become policy exclusions.
10. Freeze is an integrity/safety-policy decision, not a prediction contest.

All nine trading/write/promotion Safety flags remain false. LONG / cash equity
only. Fresh/OOS remains sealed. No subsequent Entry, EXIT, capital, portfolio or
production work is authorized by this freeze record.

## Completed measurement and delivery audit

Impact run 35336375591 on `dee68ee333f28679399c564b9d7f24efd43a5a0d`
passed, including seven byte-identical measurement regeneration files. Artifact
10543866482 is the sole completed measurement used for the decision. A signed
download URL returned HTTP 403 in the work environment. Read-only export run
35338170559 copied the same eight derived artifact files without evaluating data
again. Export ZIP SHA256 is
`77f1f38660e8d270377c8f1b0b542503eb9b3a722ad64319e3369bdd824b2860`;
per-file manifest hashes and ZIP CRCs were verified after transfer. Log transport
inserted two BOM characters; removing those transport markers restored the exact
hash. No evidence file bytes were changed.

PR path filters use the cumulative PR diff, so the export commit inadvertently
started another impact job (35338170486). It was cancelled, and commit
`4574f9edc3d2c2719b16ea8fcc9665542fbbc7ee` restricts heavy measurement to the
already-tested implementation HEAD. No result from the cancelled repeat was used.
Subsequent CI audits the immutable outputs, rather than repeating measurement.

The parent Decision Price kinds include a causally available 11:30 auction close:
old selected rows comprise 3,492 LATEST_ACCEPTED_MINUTE_CLOSE and 308
TERMINAL_AUCTION_CLOSE; new rows comprise 3,532 and 268, respectively. All auction
references in this evidence are at 11:30 with age zero. This is existing parent
price semantics, not the use of a future afternoon/session-end closing price.
The parent `lastAvailable(minutes, decision)` ordering is unchanged. The initial
unpublished ledger-audit assertion assumed only the first kind and was corrected
to verify both existing kinds; neither measurement nor policy changed.

The outcome is a safety-policy trade-off, not a predictive improvement:
+3 Precision falls 47.2559% to 30.8241%, +5 falls 24.9868% to 14.1838%.
All four chronological blocks show lower +3/+5 Precision. Strict30 MAE <=-10%
falls from 25/1,697 to 9/1,872, with worst -29.6703% still present. The old pair
of concentrated symbols loses 16 of its 17 deep-tail identities; another removed
identity is 81070. No symbol blacklist is added. DIP p05 changes slightly adversely
from -5.4458% to -5.4613%, so the overall tail improvement is not universal.

The relevant impact and Predict Tests workflows pass. The pre-existing
`Phase57 EXIT CC Freeze Audit` continues to fail its Candidate C preservation
gate, as intended by the existing KILL evidence. It is not described as green,
fixed, bypassed or revived by this Selector policy freeze.
