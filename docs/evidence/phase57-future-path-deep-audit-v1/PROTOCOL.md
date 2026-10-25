# STEP 1 — Future Path Anatomy v1 Deep Audit

Date: 2026-09-21 JST. Reference HEAD independently checked: 4ec55bb6923d0f69fbc9654ad33bb61cd2840780. PR #587 remains Draft/unmerged.

## One question and hard STOP

Does the existing 5+1 Future Path vocabulary adequately describe the actual observed price paths of the fixed 2,155 Opportunities?

This is a retrospective, evaluator-only audit on reused Development, NOT new State recognition, Entry research, independent validation or OOS. Preserve the existing classifier, thresholds, labels and evidence. Do not select or implement a replacement vocabulary. Save audit evidence and STOP FOR HUMAN REVIEW. STEP 2 and every later step require separate human authorization.

Forbidden in this audit: current-State prediction, T+ classification, Recent Daily feature evaluation, Signal evaluation, State x Signal, BUY NOW/WAIT evaluation, Entry price comparison, model fitting, Dictionary, Holdout, EXIT, capital, trading, promotion, provider acquisition. Reading the frozen census identity/allowlist contract is not running its signals. No inherited combined-study run entrypoint may be called.

## Fixed inputs and reconciliation

Use files already tracked at the reference HEAD:
- scripts/phase57_causal_entry_anatomy.py: original classify and reversal_count ONLY.
- scripts/phase57_entry_timing_census.py: future_rows and ordered_oracle ONLY.
- scripts/phase57_entry_timing_signals.py: pct and regular ONLY (no signal functions).
- scripts/phase57_causal_entry_state.py: scalar efficiency ONLY (no state or daily functions).
- scripts/phase57_entry_pattern_v2.py: minutes ONLY.
- docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json: exact IDs, Development allowlist and false safety flags.
- docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz and raw-paths-evaluator-only.json.gz: project only identity, selector timestamp/reference price, existing selector full-session availability and today's observed OHLCV/value path.
- docs/evidence/phase57-causal-entry-state-v1/ci-result/measurement/records.json.gz: compare existing pathEvaluatorOnly verbatim; do not use State, daily, trades, features or predictions.

Verify every input against its reference-HEAD Git blob and record SHA-256. Extract only the named pure function ASTs without importing the research modules or executing their top-level code. Strip decorators from extracted functions. No alterations to extracted function bodies. Use exact original full-session availability (selectorOutcome.mfeEnd is not null). Recompute original path labels and all original path fields; fail closed on any mismatch, duplicate ID, missing ID or out-of-allowlist date.

Expected counts: DIRECT_CONTINUATION=50; PULLBACK_RECOVERY=202; CONSOLIDATION_BREAKOUT=10; MULTI_SWING_CHOP=828; PERSISTENT_WEAKNESS=76; AMBIGUOUS_INSUFFICIENT=989. Path6: INSUFFICIENT_OBSERVATION=496; NO_DOMINANT_PATH=355; TRUE_MIXED_PATH=138. These are reconciliation assertions, NOT tuning targets.

## Observation insufficiency

Keep three original gate failures separately and jointly: original full-session unavailable, fewer than 20 observed future rows, fewer than 30 remaining scheduled active minutes. Empty paths are separate. Produce an exact gate-failure bitmask cross-tab and a deterministic exclusive primary reason: empty; remaining<30; rows<20; inherited full unavailable; not insufficient. Primary reason is administrative, not a claim of causality.

Separately report selection clock time and half-session, remaining active minutes, regular observed/expected rows, missing scheduled minute stamps and contiguous missing runs, first/last available future stamp, missing terminal auction row, lunch crossing, near morning end (11:00..11:30 inclusive), near afternoon regular end (last 30 scheduled minutes), before-lunch and after-lunch row counts. Lunch and auction intervals are not missing active minutes. Do not forward-fill or invent bars. Missing compact rows do NOT establish provider loss, halt or no-trade. Where compact evidence cannot distinguish these causes, explicitly retain UNRESOLVED_SOURCE_CAUSE. Co-occurring conditions are not exclusive causal attribution.

## Path predicates and witnesses

For every sufficiently observed Opportunity record all five original Boolean predicates, original assignment and CHOP-override status. Report predicate occurrence, exclusive occurrence, mixed occurrence and CHOP-absorbed occurrence. NO_DOMINANT means no predicate passed; it does not by itself prove absence of economically meaningful motion.

Audit DIRECT atomic clauses (+1% high exists; first +1% precedes -0.5% dip without same-bar ambiguity; terminal>=0; efficiency>=0.2). Audit CHOP reversal>=4 and efficiency<=0.3, and original multiple-predicate override reversal>=6/efficiency<=0.15. Audit WEAKNESS terminal<=-1%, observed closes below selector fraction>=0.6, ordered recovery<2%. Audit RECOVERY using the exact running-low chronological predicate, preserving the low/high/terminal witness and an additional descriptive later-recovery-exists flag without terminal requirement. Audit CONSOLIDATION as the original contiguous10-bar range<=0.6%, next<=10 contiguous bars breakout-close>=priorHigh*1.003 and bar range>=1.5*prior mean range, followed by terminal>=breakout close. Save counts passing each clause conjunction, including existence before the terminal condition. These are descriptive clause ablations; no alternative classifier is installed, scored or selected.

Record time-stamped retrospective events: first +1% high, first -0.5% dip, original recovery witness low/high, original consolidation/breakout witnesses, and all original confirmed 0.5% reversal times. Mixed combinations are all concurrently true existing predicates, NOT automatically sequential transitions. Order the observed witnesses and label same-bar/overlap ambiguity rather than claiming an unobserved order. No causal State inference and no new State vocabulary.

## Shape metrics and CHOP heterogeneity

Use fixed descriptive metrics: frozen close efficiency and reversal count; observed close direction changes (zero differences excluded, reset across missing/lunch); full observed high-low envelope; terminal return vs selector; close-to-close realized volatility on contiguous regular minutes; observed low/high times; best strictly ordered low-to-later-high range and times; terminal position within envelope; closing recovery from minimum low; below-selector close fraction; confirmed swing amplitudes; upward/downward movement and segment lengths. Keep whole-path measures and gap-reset measures explicitly distinct.

Report count/missing count, minimum, P10, P25, median, P75, P90, maximum, mean for each existing class/reason and each CHOP predicate signature. CHOP descriptive slices use existing thresholds only: terminal<=-1, (-1,0), [0,1), >=1; ordered range<2 or >=2; original predicate signature. No clustering, fitted model, threshold sweep, performance maximization or label replacement.

## Representative price charts

Representatives are for explanation, not an outcome subset. Predeclare selection: all original DIRECT (50) and CONSOLIDATION (10); within each Path6 reason x true-predicate signature and CHOP signature, choose up to three sorted-ID tie-broken examples closest to the median, minimum and maximum whole-path efficiency (for undefined efficiency use remaining active minutes). Also select low/median/high terminal-return CHOP examples. Include full population numeric rows regardless of chart selection.

Charts must show actual observed post-selection OHLC high/low/close normalized to selector reference, clock-time x-axis, visible breaks at missing/lunch, selector time, low/high and predicate witnesses. Never connect gaps as continuously observed prices. Save a representative index with selection reason, original label, complete predicate signature and source ID. Chart witnesses are future anatomy, never executable trades.

## Evidence and verification

New directory only; no overwrites of prior evidence. Save protocol, script/source/input hashes, all 2,155 numeric raw audit records, projected observed future OHLCV/value paths, aggregate counts/distributions, selection-time/observation tables, representative SVG charts and index, report, manifest and receipt. Deterministic gzip mtime=0, sorted serialization, no wall-clock data in measured files. Run audit twice and compare all measured file hashes. Synthetic tests must cover exact gate boundaries, empty/late/missing/lunch cases, overlapping predicates and CHOP override, no-dominant, same-bar ambiguity, deterministic representatives, and source/input corruption rejection. Synthetic cases are NOT market evidence.

Completion assessment is separate from test success. For each of seven requested completion gates report PASS/PARTIAL/UNRESOLVED, evidence filenames and limitations. Do not declare observations complete where source-cause distinctions or semantic judgments remain unresolved. Vocabulary recommendation may identify evidence for retaining or revisiting the single-label representation; actual vocabulary decision belongs to human review/STEP 2.

Dedicated audit CI and entire-PR status must be reported separately. No merge or promotion. At the end STOP, even when all seven gates pass.

## Safety

LONG-only, cash-equity-only. Preserve false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

Frozen Selector unchanged; no retrain/rerank/refilter. No Opportunity rejection. providerRequests=0; holdoutOpened=0; training=false; dictionaryUsed=false; entryTimingEvaluated=false; statePrediction=false; exitResearch=false. No credentials or external market calls are needed; use only committed Development paths.
