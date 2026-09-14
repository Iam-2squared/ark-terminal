# Phase57 LONG-only Cash Equity — Data Budget and Dataset Split v3

Date: 2026-09-15 JST  
Branch: `research/phase57-long-only-cash-equity`  
PR: #587

## Purpose

This research line is not a Selector-only experiment. The objective is to build and compare a complete cash-equity LONG-only stack:

`JPX PIT universe -> LONG Selector -> LONG Entry -> EXIT -> Capital Allocation -> Cash Equity Portfolio`

against the current integrated Ark baseline. SHORT, margin, leverage and broker execution remain prohibited.

## Current entitlement evidence

User-provided J-Quants account screenshots on 2026-09-15 confirm:

| Entitlement | Status | Scheduled end |
|---|---|---|
| Light | Active | 2026-10-06 19:02 JST |
| Tick + OhlcMin | Active / cancellation scheduled | 2026-10-06 19:07 JST |

No API key value was observed or stored.

## Acquisition policy

New Historical acquisition is still blocked. The branch must not start J-Quants downloads automatically.

Remaining blockers:

1. Re-attest private-storage and post-cancellation deletion terms.
2. Freeze exact Fresh prospective dates.
3. Receive separate explicit operator authorization at runtime.

## Clean historical allocation

The existing metadata inventory exposes 205 clean, outcome-unread historical session identifiers. v3 allocates all 205 while preserving a true reserve:

| Partition | Sessions | Purpose |
|---|---:|---|
| Development A | 25 | L0 definition / initial census |
| Development B | 15 | L0 replication / L1 label contract |
| Development C | 20 | L1 ablation / L2 model selection |
| Development D | 20 | threshold freeze / integrated Development replay |
| Validation | 30 | frozen first-pass evaluation |
| Validation Replication | 20 | locked replication |
| Primary OOS | 30 | true outer OOS |
| Contingency OOS | 30 | sealed insurance if Primary OOS is invalidated for non-performance reasons |
| Admission Reserve | 15 | replacement for admission failure only |
| **Total** | **205** | |

Fresh prospective sessions are outside this 205-session historical accounting.

## Why Reserve exists

Reserve is operational insurance, not extra tuning data. It may be used only when an admitted session is invalid because of precommitted data-integrity failures such as:

- raw hash mismatch;
- provider page corruption;
- missing mandatory Daily or dated Master data;
- unresolved corporate-action ambiguity;
- PIT Master divergence.

Poor model performance is never a Reserve deployment trigger.

## L0

L0 remains Daily-only and uses dated PIT Master plus adjusted daily fields. It measures opportunity density for +3%, +5% and +10% sessions by JPX segment. Minute requests remain zero in L0.

Development A defines the census contract; Development B replicates it. L0 results cannot choose Validation/OOS dates.

## L1 / L2

L1 introduces causal intraday 5-minute reconstruction from released minute data. Future labels are evaluator-only and cannot enter decision features.

L2 evaluates a limited set of predeclared feature families. The primary target, final feature set, model family and threshold rule must be frozen before Validation.

Future MFE/MAE may be labels, but normalization used in the live decision semantics must be causal (for example decision-time ATR), not future realized volatility.

## Minute-data conservation

The core rule is:

**Do not spend J-Quants minute data only on Selector research.**

Any authorized intraday acquisition is persisted once and reused for:

- Selector research;
- LONG Entry replay;
- EXIT replay;
- Capital Allocation;
- integrated portfolio replay.

Winner / near-winner / control samples are diagnostic only. Final L2 fit, threshold calibration, Validation, OOS and integrated performance claims require the full point-in-time JPX cross-section for released session dates.

## Purge / embargo

There is no blanket ban on causal historical prices from an earlier partition. Past information that was genuinely available at a decision timestamp remains valid.

The actual protections are:

- labels must resolve within the same JPX trading session or be ineligible;
- no target horizon may cross session close;
- next-session prices are not features;
- scalers, weights, thresholds and other fitted statistics are learned only on authorized Development blocks;
- Validation/OOS outcomes stay sealed until release.

## Human-overfitting controls

Before Validation:

- primary target frozen;
- feature set frozen;
- model family frozen;
- threshold rule frozen;
- current-Ark comparison metrics frozen;
- GO/NO-GO rules frozen.

Validation and later sets cannot trigger retuning. Contingency OOS is not a retry after a bad Primary OOS result.

## Integrated comparison contract

The end point is an integrated comparison, not a Selector scorecard.

| Comparison | Requirement |
|---|---|
| Baseline | current Ark Selector -> Entry -> EXIT integrated system |
| Candidate | new LONG Selector -> LONG Entry -> EXIT -> Allocation -> cash portfolio |
| Evaluation window | same window |
| Cost model | same cost assumptions |
| SHORT contribution in candidate | exactly 0 |
| Margin trades in candidate | exactly 0 |

Minimum frozen metrics are after-cost Net, PF, MaxDD, Return/DD, win rate, trade count, portfolio return, cash utilization, missed opportunity and symbol/sector concentration. A Development win only qualifies a candidate for frozen evaluation; Validation/OOS determine whether the improvement survives.

## Data budget

Daily + Master for the 205 clean historical sessions remains light compared with intraday data. Intraday is released by partition, not acquired for all 205 upfront.

Current planning upper bound for Development 80 intraday sessions, extrapolated from the prior 90-session audit:

| Item | Planning estimate |
|---|---:|
| Development sessions | 80 |
| Minute pages | ~1,056 |
| Minute rows | ~33.7M |
| Daily + Master + minute requests | ~1,216 |

This is an upper planning bound, not authorization to download.

## Independent review disposition

Claude returned `CONDITIONAL GO`. Ark accepted the useful controls, corrected arithmetic/date/timestamp issues, rejected a blanket prohibition on causal past history, and retained Ark's existing timestamp semantics.

See `docs/phase57-long-only-independent-review-disposition-v1.md` for the itemized disposition.

## Speed policy

The project target is to finish the LONG-only research candidate and current-Ark integrated comparison this week. Speed comes from removing duplicated work, not from weakening research controls.

Therefore:

- do not repeat audits already evidenced;
- do not reacquire identical data;
- do not stop all work while waiting for Claude when a non-contaminating task can proceed;
- move directly from Formal L0 to L1 once the census contract passes;
- reuse the same released Development raw data through Selector, Entry, EXIT and Allocation;
- do not consume Validation/OOS merely to accelerate Development.

## Next step

1. Clear the remaining non-data blockers.
2. Freeze Fresh dates.
3. Get explicit operator acquisition approval.
4. Acquire the minimum Daily + Master payload once.
5. Run Formal L0 immediately.
6. Progress quickly into L1/L2 while preserving the same raw data for Entry/EXIT/Allocation integration.
