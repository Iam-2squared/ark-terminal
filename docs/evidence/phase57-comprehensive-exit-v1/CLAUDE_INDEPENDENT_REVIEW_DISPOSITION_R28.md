# Phase57 — Claude Independent Review Disposition R28

Date: 2026-09-25 JST  
Basis HEAD before disposition: `b33ba0f4815cd41e9d85bbad2edd50b31a2fa1a7`  
Review source: user-relayed genuine Claude independent pre-design review.  
Claude verdict: **PASS WITH REQUIRED FIXES** (3 CRITICAL, 4 HIGH, 4 MEDIUM, 1 LOW).  
Status: **DISPOSITION RECORDED; PRE-PERFORMANCE CORRECTIONS REQUIRED BEFORE FIT**.

No NEW EXIT fit, replay or candidate performance is authorized by this document.

## Disposition principles

Claude findings are treated as independent review, not automatically accepted. Each is checked against R20/R23/R24/R25. Where the review asks for a policy restriction that would itself become an unregistered extra hyperparameter or would incorrectly suppress legal causal information, the correction is narrowed to the actual causal/encoding guarantee.

## Findings

| ID | Sev | Disposition | Basis / required action before performance |
|---|---|---|---|
| F001 | CRITICAL | **PARTIAL** | Valid concern: State timestamp/encoding must be explicit and no retroactive State is allowed. Reject mandatory hand-authored state→action mapping: R25 intentionally uses State as causal evidence inside the fixed model and a manual map would add a new unregistered policy layer. Pre-fit correction: current State is exactly the canonical State-v3 result computed at NOW from bars with knownAt<=NOW; no smoothing/backdating. All 9 states are categorical evidence with quality/confidence/missing flags. No state alone is a mandatory SELL or mandatory CONTINUE. The only action map is the already-precommitted R25 predicted-hold-value threshold/persistence rule. |
| F002 | CRITICAL | **ACCEPT** | R25 already says explicit UNKNOWN categories but encoding must be machine-frozen. Pre-fit correction: each signal is tri-state TRUE/FALSE/UNKNOWN; histories preserve counts/coverage. TRUE→UNKNOWN is not disappearance. Missing prediction/current fresh observation => HOLD_NO_ACTION. No opportunity-level complete-signal exclusion and no outcome-conditioned coverage filter; this avoids the review's suggested >75% filter becoming post-selection. Training and replay use the same encoder. |
| F003 | CRITICAL | **PARTIAL** | Accept need for strict known/owned definitions and stratified reporting. Reject the review's example premise that a High before NOW can be 'unknown at NOW' while present in runningHigh: R20 admits only completed bars with start+1<=NOW and knownAt<=NOW. Running observed High/Low are causal known history; 'owned' means position ownership, not execution of a hypothetical exit at that High. Pre-fit correction: observed extrema include only completed owned bars known by NOW; no current/unclosed or future suffix. Complete-prefix MFE/MAE/giveback remain null if any expected owned bar is missing. Add complete-prefix YES/NO scorecard strata. Never impute an unobserved bar High. |
| F004 | HIGH | **PARTIAL** | R23 already documents why all 30 are blocked: their exact prior-daily/context lineage is not pinned, not because PDH means future pivot. Claude's interpretation of PDH as 'Pivot Daily High' is not adopted without repo evidence. R23 also explains why 187 were fixed by family before performance, not by IC. Pre-fit: retain 30 BLOCKED and 187 fixed subset; add machine-readable rationale/source/knownAt already emitted by adapter. Correlation-to-future-outcome audit is DEFERRED because using outcome correlation to re-admit/remove features now would alter the precommitted feature set after exposure. |
| F005 | HIGH | **ACCEPT** | R24 already defines every completed continuous 1m endpoint and exact next scheduled OPEN. Clarify boundary timestamps are exact minute endpoints only; no intra-bar decisions. A bar's High/Low is usable only after its close/knownAt. 11:30→12:30 is a real lunch gap and exact 12:30 OPEN execution; no intervening price is known/used by the decision. Gap behavior is reported, not 'corrected' using future data. |
| F006 | HIGH | **ACCEPT** | Buckets are evaluator-only and must never define training folds, weights, candidate configuration, threshold or feature selection. R25 trains across Development sessions, not per outcome bucket. Report within-bucket diagnostics only after decisions. Capture denominator remains the actual canonical unclipped Low→High / Entry→High geometry. No bucket-conditioned model selection. |
| F007 | HIGH | **ACCEPT** | R24 already separates Owned Peak→Exit giveback from evaluator High→Exit missed opportunity. Pre-fit clarify: certified giveback only where owned prefix is complete; observed-only proxy must be labeled separately and cannot satisfy Profit Retention gate. Scorecard must show complete-prefix YES/NO and metric-specific denominator. |
| F008 | MEDIUM | **ACCEPT** | Claude's US-market reference is inapplicable; this cohort uses Japanese continuous sessions with lunch. R24 is controlling: 11:30→12:30 lunch, no overnight, mandatory 15:30 auction terminal, 63 missing auction refs remain UNRESOLVED_TERMINAL_EXIT/censored; never next-day re-evaluation. |
| F009 | MEDIUM | **ACCEPT** | R20 is controlling: missing fresh close does not use next close or forward fill. Current return is null; stale last-observed data stays separately labeled. State/Signal quality/missingness is explicit. R25: missing prediction/current observation => HOLD_NO_ACTION. Pattern inputs preserve null/availability; no future close substitution. |
| F010 | MEDIUM | **ACCEPT** | R25 already precommits exact 24 configs, four walk-forward OOF folds, gates, ranking, tie=no-selection and NO_SELECTION_STOP. No new threshold/gate may be added after results. Clarify no bucket enters selection. Protected partitions stay sealed. |
| F011 | MEDIUM | **REJECT** | R25 models numeric incremental HOLD5/HOLD15/HOLD_TERMINAL values, not P(EXIT). There is no probability→binary threshold. The two EXIT thresholds {0.00,0.10 pp} and persistence {1,2} are already explicit dimensions of the 24-config grid. No hidden threshold tuning is allowed. |
| F012 | LOW | **ACCEPT** | 58 sessions are 58 Opportunity-bearing trading calendar sessions, not Monte Carlo runs. Run A/B means independent deterministic regeneration of the same inputs/contracts and must be byte-identical. R25 keeps session grouping and session-equal weighting. |

## Required pre-fit closure

Before the first estimator fit/performance inspection, create a machine-readable correction contract/tests that enforce:

1. State at NOW = canonical unsmoothed State-v3 from strict known prefix; no state-only mandatory action.
2. Six Signals encoded TRUE/FALSE/UNKNOWN with explicit missingness; TRUE→UNKNOWN never FALSE/failure.
3. Running extrema only from completed owned bars known by NOW; incomplete prefix cannot produce certified giveback; complete-prefix strata required.
4. Decision epochs are exact minute endpoints; no intra-bar snapshots.
5. Outcome buckets are evaluator-only and never enter training/selection.
6. 63 terminal missing references remain censored; never overnight/next-day fill.
7. Missing fresh close/reference is never forward-filled.
8. R25 selection/gates remain controlling; no extra post-review performance gate is invented.
9. No probability threshold exists beyond the registered numeric hold-value thresholds.
10. 58 sessions are calendar sessions; Run A/B is deterministic regeneration.

## Review corrections that must NOT be adopted

- Do not add a hand-coded State→SELL mapping merely because Claude requested one; it conflicts with the already-frozen finite model protocol and could prematurely kill DROP→REBOUND winners.
- Do not exclude opportunities based on high Signal UNKNOWN percentage; preserve all IDs and explicit missingness.
- Do not treat causal completed-bar running High as future merely because the path is incomplete. Incomplete means missing scheduled observations, not that already observed High occurred in the future.
- Do not interpret `PDH` as 'Pivot Daily High' without repository evidence.
- Do not add post-fit feature correlation pruning or new gates after performance is observed.

## Exposure / safety

NEW EXIT fits=0; candidate performance inspections=0; provider requests=0; protected opens=0. Entry Dual Freeze unchanged. Fixed12/Candidate A historical only. Safety9 all false. No main merge/live/paper/production/force push.

## Next

Implement the pre-fit correction contract and focused tests, rerun relevant CI, append a Claude-review closure receipt, and only if all required corrections pass may R25's exactly 24 configurations begin Development fitting.
