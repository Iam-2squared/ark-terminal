# Confidence-aware sparse Dictionary — research design, not promotion

## Decision

A sparse representation is feasible. A practically validated symbol/cluster-specific personality system is not yet established. The unchanged v0 Completion Gate remains FAIL. No WATCH/INSUFFICIENT cell is promoted, and no new Entry/EXIT is authorized by this design.

The existing Gate requires a population-level set of at least 8 USABLE traits, 4 families, 2 daily and 2 intraday traits. It does not require every symbol to possess all traits. Sparse storage therefore addresses missingness and heterogeneous coverage, not the statistical reasons for failure.

## Record and interface

Use a keyed list, not a dense mandatory feature vector:

`(symbol join key, lane, trait_id, definition_hash, window_start, computed_through, availability_time)`.

Each cell preserves raw estimate with units/transform; peer prediction; peer-relative residual; posterior and posterior scale; n_sessions; nEff; event-session count and distinct event count separately; coverage; CI with its method; shrink weight; posterior SD; original global reliability metrics/status; symbol eligibility; temporal validation status; stability/drift; regime/calendar version; historical/PIT evidence class; source hashes. Unknown remains null with a reason, never zero. Symbol ID is only a join key.

Separate statuses: `globalTraitStatus`, `symbolObservationEligibility`, `symbolTemporalReliability`, `clusterTemporalReliability`, `freshness`, `readerCompatibility`. Current ELIGIBLE only satisfies observation-count rules. It is not a per-symbol USABLE certificate. Existing 20/60/250 estimates and their normal/Beta intervals do not constitute temporal calibration evidence.

Expose a trait cell only for strictly later sessions than `computed_through`, with a separately validated same-definition Reader feature mapping. Full-session outcomes, conditional future response labels, HOD/LOD and session-end values cannot be read during that same session. The daily lane ends 2024-09-13, whereas intraday ends 2025-08-25: their evidence must not be silently joined as equally fresh current personalities.

## Symbol and peer integration

Preserve the existing A-only peer model and existing nEff/(nEff+20) shrinkage as a reference, not a newly validated optimal rule. A symbol can carry only its supported traits. Missing traits cause abstention/unknown, not fabricated neutral scores. Small samples may retain a prior explicitly labelled PRIOR_ONLY, but only a separately validated peer prior could support a future decision.

Keep `peer_explained_component` and `symbol_residual_component` separate. A raw signal disappearing after joint logVa/logS/logPrice/coverage adjustment is not proof that a particular one of these variables caused it. Current files lack separate covariate ablations, price/volatility-stratum validation, and B-period cluster outcomes. In-sample A peer association cannot certify cluster persistence. Any future peer grouping must be finite, A-only, exclude symbol ID/outcomes and be frozen before its Development evaluation; report group membership drift and out-of-group coverage.

## Short / medium / long and drift

Retain separate 20/60/250 snapshots, not one 2-year mean. These are grid-position windows, not promises of 20/60/250 observed sessions. Intraday exclusions remain missing. Do not choose a window after seeing a favorable result. The 20-vs-250 correlation in this audit is descriptive and overlapping: it cannot certify recent-only reliability.

Keep the saved drift statistic and nEff visible as evidence, not a newly invented confidence score. Drift can downgrade availability or require abstention under a future precommitted policy; it must not trigger automatic refitting/promotion. New temporal evidence requires non-overlapping causal Development cuts, fixed selection rules, multiple-testing accounting and independent assessment. It is absent in the current snapshots and has not been manufactured here.

## Operational meaning and safeguards

`diagnostic/07_sparse_availability.json` enumerates combinations that can be represented from unchanged USABLE traits plus existing eligible cells. It certifies data availability only. Separate frozen endpoint dates mean no current deployment is implied. No trading profitability is measured.

The joint Dictionary/Reader interface is NOT READY: actual-history schema mismatch, silent value-baseline mismatch, and stale-bar context acceptance remain in the unchanged Reader. Synthetic witnesses are in `scripts/test_phase57_dictionary_anatomy.py`. A future version must fail closed on invalid/missing/current-date history, handle session/phase transitions and stale bars explicitly, normalize units, preserve timestamp provenance, and map dictionary scales to Reader scales without arbitrary z-score conversion.

Once both Dictionary and Reader are independently Development-usable, freeze their versioned interface and then redesign **NEW LONG Entry** (ENTER/WAIT) and **NEW LONG EXIT** (HOLD/EXIT) around personality × causal chart context. This must be a new architecture, not a minor edit to legacy Entry/EXIT. Frozen Selector and Capital remain unchanged. This condition is not met now.
