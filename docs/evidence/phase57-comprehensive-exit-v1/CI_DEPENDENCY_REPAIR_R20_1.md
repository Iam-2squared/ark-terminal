# R20.1 — canonical producer import dependency repair

Date: 2026-09-25 JST. Basis HEAD: f8cae260f5cc776266a5b9c68cf9269586cc803f.
Controlling research: R18 / R20 observation contract. No policy change.

## 現状 / failure evidence

Initial dedicated run 36128498119, job 108050052986, failed before the R1 artifact
download or any real-cohort census. All 31 core tests passed. Canonical test-class
setup failed with ModuleNotFoundError: scipy. The actual import chain was
signal detector → Pattern-v2 → chart Entry → behavior helpers → dictionary helper
→ scipy.stats.rankdata. This is an import-time dependency, not Dictionary feature
admission and not an authorization to train any model.

Failed artifact 10861226003 is retained, ZIP SHA256
`aee8b8c04192e39bb9d227ddfad61bb437cbfa1b32011c7b6b2b215c62b8280e`.
No failed artifact is overwritten. Do not claim canonical tests or full census
passed on this first run.

## 実修正

Only the dedicated workflow dependency installation changes. Reuse exact pins
from the existing canonical signal-census workflow on this same HEAD:
`numpy==2.3.5 scipy==1.17.0 scikit-learn==1.7.2 pandas==2.2.3`.
The checkpoint generator, tests, clocks, Entry ledgers, State/Signal producers,
missingness, source pins and all research semantics are unchanged. Canonical
checks remain mandatory; no skip, mock substitution or test weakening is used.

## 次工程 / unchanged boundaries

Run the corrected dedicated CI, then inspect its actual canonical tests, complete
2,155-ID observation census for both Entry arms, A/B file hashes and artifact.
NEW EXIT policy/model/performance remain unimplemented and unevaluated. Old
Fixed12/Candidate A are still excluded. Entry2 remain frozen; provider acquisition
and new protected partition access stay zero. Safety9 stay false. No main merge,
force push, live/paper/production or automatic monitoring restart.
