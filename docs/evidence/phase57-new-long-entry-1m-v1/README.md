# NEW LONG Entry 1m v1 — implementation complete, performance pending

2026-09-17 / PR #587 / research-only / LONG cash equity only.

**Status: IMPLEMENTATION_TESTED__REAL_1M_MEASUREMENT_BLOCKED.**
This is an executable, unvalidated research prototype, not a profitable or accepted Entry candidate.
The previous chat-only Phase3 performance claim was withdrawn and is not used as evidence.
Neither Phase1/2 failures nor this implementation prove that five-minute information is inherently unusable or that one-minute timing will improve performance.

## Implemented

- `predict/long-only/phase57-new-long-entry-1m.mjs`: streaming state machine, snapshots, reference fills, paired evaluator, screening, research-only EXIT handoff.
- `scripts/run_phase57_new_long_entry_1m.mjs`: explicit local JSON replay, per-candidate ledger, four chronological blocks, five symbol groups, one-minute execution-latency sensitivity.
- `scripts/prepare_phase57_new_long_entry_1m.py`: binds an already-authorized local minute projection to the existing Frozen Selector first-event population. No downloads, credentials or decryption.
- `predict/tests/phase57-new-long-entry-1m.test.mjs`: 59 synthetic/unit tests passed locally.
- `predict/research/phase57-new-long-entry-1m-v1.json`: fixed research specification before real 1m results.

## Single hypothesis

No Momentum-sign routing at selection. Start WATCH and process closed one-minute bars.
If no preceding closed pullback has occurred, a bullish close above the selection reference produces a continuation intent.
A close below the selection reference arms PULLBACK; a strictly later bullish close above the immediately preceding bar HIGH produces a rebound intent.
Unconfirmed candidates expire at 30 minutes or the continuous-session boundary. Missing minutes are UNKNOWN, not successful abstentions.
The earliest confirmation is after one completed minute, never retrospectively at selection.
This rule is a hypothesis, not a known good trading pattern. There is no learned model, parameter search, forced fallback Entry or repeat Entry.

## Timing and comparison

Only closed, available bars reach the decision kernel. Fill is a separate next scheduled OPEN reference; the signal-bar LOW is never a buy price.
Zero queue/latency is an optimistic reference assumption, not an actual fill. A fixed extra one-minute latency is reported separately.
Primary panel requires 60 continuously observed minute bars after selection, and is chosen by the evaluator, not by the decision kernel.
D30 uses 30 minutes after each actual reference Entry. Opportunity capture uses the common selection+60m endpoint.
Expired cases remain in the candidate denominator. Their noninvestment is zero only in the policy index, never a zero-loss synthetic trade. Missing outcomes stay null.
Engineering screen: at least 30 paired Entries / 10 symbols / 20 baseline winners at each +3/+5 level; 90% winner capture, 80% throughput, 10% mean D30 reduction, nonworse ES95, nonworse mean price and common-deadline net, plus period/symbol stability.
A screen success is only CONTINUE_NOT_VALIDATED. Candidate promotion remains false.
The handoff is an Entry reference record with quantity=null. Frozen EXIT, allocation, cash and Portfolio are not replayed or modified by this package.

## Evidence actually produced

59 local unit/synthetic tests PASS. Seven named synthetic E2E paths cover continuation, rebound, falling, flat, missing prefix, missing next OPEN and session boundary.
21 separately implemented checks passed on synthetic E2E and existing source metadata. These are not 21 market observations or 21 validation folds.
The source ZIP and all 12 source pins were verified; 3,800 events / 76 sessions / 2,743 first symbol-session anchors match prior identity.
Real 1m performance was not measured. Model fit=0; market-provider requests=0; Fresh/OOS=0; broker operations=0.
Initial test-file syntax errors were corrected before the final run; no real performance result was used to change the rule.
This commit relies on the existing Predict Tests workflow; it changes no workflow or secret handling. Check the final head's CI separately.

## Remaining blocker

The accessible source export contains five-minute future paths, not actual one-minute paths.
The existing `scripts/phase57_new_long_entry_minute_export.py` is a producer script, not evidence of an executed export. Its saved window ends at selection+30m, which alone cannot support every delayed Entry's 30-minute outcome or the common +60m panel.
Required input is an **already-authorized, locally available one-minute Development projection** plus its audit, including the same 2,743 anchors, 76 session source hashes, explicit missing rows and enough forward coverage through selection+60m where the session permits.
Do not bypass the previously blocked export/workflow action, retrieve keys, modify a trusted workflow to execute an unapproved export, or substitute five-minute interpolation.
The consumer can preserve shorter windows as unknown; it cannot declare completed economic evaluation from them.

## Commands (repository root)

```sh
node --test predict/tests/phase57-new-long-entry-1m.test.mjs
python scripts/prepare_phase57_new_long_entry_1m.py --source /path/to/entry-information-pinned-development-7599df4119.zip --output /path/to/new-readiness
# When an already-authorized minute projection and audit are available:
python scripts/prepare_phase57_new_long_entry_1m.py --source /path/to/entry-information-pinned-development-7599df4119.zip --minutes /path/to/minute-entry-paths.json.gz --audit /path/to/audit.json --output /path/to/new-input
node scripts/run_phase57_new_long_entry_1m.mjs --input /path/to/new-input/replay-input.json --output /path/to/new-results
```

All output directories must be new. The preparation-only command writes INPUT_MISSING and does not invent a replay file.
The producer audit schema is `PHASE57_NEW_LONG_ENTRY_MINUTE_EXPORT_V1`; prices are normalized percentage changes from each pinned decisionPrice, converted by the consumer to absolute prices.
Reconstructed availableAt=barEnd is not proof of actual historical publication/arrival time. Original raw duplicate, minute completeness, split adjustment and fill-quality certification remain separate data-quality responsibilities.
Historical Development and Frozen Selector's upstream exposure remain; this is not whole-pipeline OOS.

## Identity / safety

Source head: `7599df41199a8c4d1ea86d5f3cb595edd599dd21`.
Source ZIP SHA: `043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505`.
First anchor identity: `985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121`.
Rule SPEC SHA: `2331a9b47bed168e5f1ffb25c933b05b479d3f6afca47097f472255e7426c293`.
Frozen Selector / existing Entry / EXIT / Equal / cash ledger remain unchanged.
All nine write/trading/promotion flags remain false; no main merge or production integration.
