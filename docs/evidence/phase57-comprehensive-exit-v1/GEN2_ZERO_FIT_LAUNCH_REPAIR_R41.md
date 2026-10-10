# R41 launch transport repair before any model fitting

The first launch reached GitHub Actions but failed in preflight. It did not reach dependency installation, R35 restoration, feature/label preparation, model fitting or causal replay.

- Run: `36233376942`; job: `108380613334`; attempt: 1.
- Execution SHA: `8ecad9f0fd412e9ceb9ed04cc1e691979ad60d99`.
- Required CI at its implementation parent: `36233205154`, SUCCESS, 91 tests; existing EXIT foundation CI `36233205098` also SUCCESS.
- Failure artifact: `10903576190`, `phase57-exit-gen2-r41-36233376942`.
- Archive SHA256: `f4830ec87fc55c00de2397056e657fbba01f49f4d09b50ca381482e6fe0456b8`.

Cause: `github_get` rejected every endpoint containing `..`, which accidentally rejected the legitimate GitHub compare endpoint `/compare/<base>...<head>`. Synthetic tests had mocked the higher-level GET function and missed this transport-layer validation. The correction permits the valid comparison syntax while continuing to reject traversal path segments, foreign URLs and malformed endpoints. A regression exercises the actual GET wrapper with a mocked response.

The downloaded failure archive was independently hashed and inspected: nine members, all contract or launch logs/receipts; no prepared data, model bundles, predictions or ledgers. The saved failure receipt says `PREFLIGHT_FAILED_FIT_NOT_STARTED`, `modelFitsPerformed=0`, `candidateReplaysPerformed=0`. The workflow job metadata independently shows dependency install, R35 restore, prepare, pre-fit recheck, fitting/replay and final completion check all SKIPPED. Upload succeeded. Copies of the receipts and archive membership audit are committed under `r41-zero-fit-launch-failure/`.

This is a launch-code repair, not a performance-driven protocol change or extra research fit. The frozen protocol SHA remains `5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4`. Architecture, features, labels, four specifications, 16 policies, thresholds, 64-model budget, split, gates and selection rule are unchanged. Development fits/replays/performance inspections remain zero.

The duplicate guard retains its fail-closed behavior. Exactly this independently audited failed run is recognized by hard-pinned run ID, execution SHA, attempt 1, failed authorization step, skipped data/fitting steps and uploaded artifact identity/digest. Every other previous R41 run is rejected. A new attempt-1 workflow run may start only after the repaired source completes required CI, followed by a new marker-only direct-child commit. No GitHub rerun or silent resume is used; original failure evidence remains intact.

Safety9 all false; provider requests 0; protected partition opens 0. Do not interpret the failed launch as fitted models or performance evidence. The controlling stop condition and next-Work boundary remain unchanged.
