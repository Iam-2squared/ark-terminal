# Publication reconciliation — append-only evidence completion

Recorded: 2026-09-22 21:41 JST.

During final byte verification, branch HEAD advanced from e6717d6d2c237819f5401affe91b53ec683a5a8e to 68f0e2ba277fe771ee1f6983c4f4d849c49c55d2. Direct comparison found exactly two added documentation files: A12_FORMAL_ACCEPTANCE_20260922.json and CHECKPOINT_20260922_2128_JST_STATE_V2_A12_COMPLETE.md. Both were read, retained byte-for-byte, and agree on tested code b784e97, CI35721458178, artifact10692617487, all4 canonical hashes, fixed population, A8 masking and historical-only/second-implementation scope. No engine or numerical changes intervened.

The final-acceptance-20260922 directory adds the detailed, hash-bound A1-A12 receipt, full report, delivery binding and three supplemental full-row audit receipts. The detailed receipt was assembled at21:31, before this final branch reconciliation; publicationParentObserved records its actual earlier observation, not the parent of the eventual publication commit. Its bytes and downloadable ZIP hashes remain unchanged.

The earlier compact receipt uses abbreviated descriptions for some gates. For exact frozen gate-to-evidence mapping, use this directory's A12_ACCEPTANCE_RECEIPT.json: A4 is schema/status/value/reason legality, A10 is coverage disclosure and A11 is explainability. The full executed evidence is not replaced by a frozen-rule or safety assertion. Both receipts preserve the same qualified acceptance verdict; the detailed mapping supplies the explicit scopes and36 evidence hashes.

Six prepared Git blobs were checked against local exact-byte SHA1 and SHA256 before publication. The detached staging commit0b331964e457fd5bd7d6fb473d647c6f46f078f3 was not force-pushed over concurrent documentation. Instead these identical blobs are appended on current HEAD68f0e2b. Prior results, failures, receipts and checkpoints are not overwritten.

The publication changes documentation/evidence only. No main merge, repeated numerical CI, provider request, protected-data opening, Recognition or trading is authorized or performed. All Safety9 flags remain false.
