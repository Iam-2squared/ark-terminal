# Phase57 R49 formal closure and R50 basis

Saved: 2026-09-27 JST  
Basis HEAD: `f4c2173134a94d83e6d722546de0094c3b997d9e`

## Formal disposition

R49 is a formal negative result: three frozen candidates, zero PASS, `NO_SELECTION_STOP`.
The per-Entry-arm frozen gate was support >=50, median post-Entry-upside capture >=50%, mean net >=3.25%, median net >=2.00%, and premature rate <=10%. All candidates failed only the median-capture gate in both Entry arms. Candidate A is a terminal-hold control in observed execution (0 winner-harvest exits; 2,257 forced-terminal exits), not a harvesting solution.

| Candidate | IM mean / median / capture | R1 mean / median / capture | Disposition |
|---|---:|---:|---|
| R49_A | 4.372% / 3.524% / 48.757% | 4.044% / 3.310% / 39.810% | FAIL |
| R49_B | 4.974% / 3.581% / 45.700% | 4.480% / 3.419% / 39.894% | FAIL |
| R49_C | 4.605% / 3.524% / 43.700% | 4.241% / 3.230% / 39.597% | FAIL |

Primary means evaluator-only `POST_ENTRY_UPSIDE_GE5` (IM 222; R1 200), not `CANONICAL_L2H_GE5` (IM 387; R1 381). Neither bucket is a decision or training input.

## Failure anatomy

- R49_A funnel reached D>=0.55 zero times (IM 34,600→5,207→3,193→2,806→1,722→1,679→1,342→0; R1 30,814→5,089→3,578→3,188→1,831→1,787→1,481→0). Pre-exit D maxima were approximately 0.488 and 0.521. Lowering 0.55 after the result is prohibited.
- Winner-harvest coverage was low: B 29/222 IM and 32/200 R1; C 18/222 IM and 16/200 R1.
- Terminal giveback remained material: median High-to-Exit gap was 4.590pp IM and 5.017pp R1. R49_A IM had 67/222 negative-capture cases; its worst primary net was -29.033%.
- In the common IM primary set, B changed 28/222 exits versus A: 23 improved, 5 worsened, 194 unchanged. B improved the left tail and mean/PF-like economics but reduced median capture.

## Independent Claude review disposition

This section records the independently supplied review disposition; it is not presented as a new model run or direct transcript.

ACCEPT: R49 has an incremental-improvement structural ceiling; A is terminal-hold control; B is left-tail improvement with limited median improvement; post-peak deterioration and winner lifecycle are the next focus; D-score is diagnostic/secondary rather than mandatory; loss containment is not restored as Primary.

REJECT: result-derived coverage targets; R49 threshold relaxation; D 0.55→0.50; copying illustrative age/giveback values as tuned thresholds; any gate relaxation.

## Exposure and safety

The initial R49 full-scorecard loader decoded 3,220 allowlist-external payloads. They were not used for training, decisions, scoring, display, or tuning. The allowlist-first rerun passed 15/15 checks and its ledger/10 CSV outputs were byte-identical. This record does not claim zero out-of-scope access.

Development only; no Common Holdout, REPORT19, Validation, OOS, Fresh, Prospective, or Protected partition was opened; provider retrieval was zero. Entry/Selector were unchanged. Safety9 remains all false.

