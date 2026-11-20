# Phase57 Capital v3 — final audit closure

Saved JST: 2026-09-27T18:12:44.796145+09:00. Basis research HEAD: `35e5c4c2a205f61b8aa2321bd3e37f7308088570`. This file is an append-only reporting and pinned-input checkpoint; re-fetch the branch HEAD for its own SHA.

## Controlling disposition

**0/2 PASS / NO_SELECTION_STOP.** `CAPITAL_V3_CONTROLLING_HANDOFF.md` is the full scorecard and decision record. Existing R35 is a control/fallback only. No selected Capital v3 rank, no v3 asset/daily curve, no Final EXIT or v3 funded EXIT threshold research.

## Exact verification chain

- Frozen design/geometry/feature Gate was saved before v3 funded performance, at `597752ccee71e8fefd7b2f15b8ccf3ae69ac7e34`.
- Outcome-blind contract CI run `36307624818` SUCCESS, source `404293f674f1c796f9204abcfec73ec69740e5dd`. Local 52 focused tests PASS; CI zero fits and zero funded performance, feature source pins passed.
- Finite Action run `36307805922` SUCCESS, source `89ab75d7665818c3533963c486a6388d417067c2`, exactly 16 fits; artifact ZIP SHA256 `d9c0731560fe8e63039dc563ec8c3af279b0e2a08df39745b9bcd63b677c0de7`.
- Independent result CI run `36308475948` SUCCESS, exact tested source `35e5c4c2a205f61b8aa2321bd3e37f7308088570`. It re-read permanent result file hashes, rejoined all four funded ledgers with pinned source labels, checked exclusive misses and no false selection, and verified Safety9.
- Exact local repeat: all four MAX3 funded ledgers were byte-identical with CI, and both verdicts NO_SELECTION_STOP. Feature matrix/prediction hashes differed, with max prediction deltas A `2.6879043e-7`, B `8.173906e-12`. Exact prediction-byte reproducibility is **not demonstrated**. Cause remains undetermined. No post-result change to model/features/Gate/rounding was made.

## GitHub-only reconstruction

- `INPUTS/R1-entry-records.json.gz`: SHA256 `15ddb5cfc5169024878ee72d9dbecc6e1d9dec24e78afa2dcdf8dea891117fa6`.
- `INPUTS/R50-terminal-ledger.jsonl.gz`: SHA256 `770f02612cdd97ed2420f14a2fe6ab6ed1f50a96f222afa9b3c376982c8ea476`.
- `CAPITAL_V3_PERMANENT_INPUTS.json` identifies the original GitHub Actions artifacts and pins the source files. These two copies preserve exactly the previously used Development bytes after artifact expiry; no new provider data or cohort was introduced.
- `RESULT/` stores CI report, all OOF predictions, four funded MAX3 ledgers, independent audit and execution SHA. `CAPITAL_V3_RESULT_MANIFEST.json` gives every SHA256. Code, contracts, 254-feature audit, geometry, Gate and tests are committed on this branch. Other pinned raw paths already live in the repository.

Recheck from repository root:

```bash
python -m scripts.phase57_capital_v3 --mode preflight \
  --r1-records docs/evidence/phase57-capital-v3/INPUTS/R1-entry-records.json.gz \
  --benchmark-ledger docs/evidence/phase57-capital-v3/INPUTS/R50-terminal-ledger.jsonl.gz \
  --out /tmp/phase57-v3-prefit.json
python -m scripts.phase57_capital_v3_audit \
  --source docs/evidence/phase57-capital-v3/RESULT \
  --r1-records docs/evidence/phase57-capital-v3/INPUTS/R1-entry-records.json.gz \
  --benchmark-ledger docs/evidence/phase57-capital-v3/INPUTS/R50-terminal-ledger.jsonl.gz \
  --out /tmp/phase57-v3-audit.json
```

## Exposure, safety, next action

Development Opportunities 2,155, previously outcome-exposed. New Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective / Protected opens 0; new provider requests 0. Past R49 and superseded v0 allowlist-external decode remains disclosed. Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` unchanged. Safety9 all false. No main merge, force push, live, paper, production, broker/Excel/RSS order write or transmission.

Preserve this negative result. Next research must address numerical byte identity and independently documented R1 unresolved auction/mark continuity. Any model/Gate/EXIT replacement needs a new performance-blind protocol and independent evidence; do not relax the v3 Gate or relabel the existing control as selected Capital v3.
