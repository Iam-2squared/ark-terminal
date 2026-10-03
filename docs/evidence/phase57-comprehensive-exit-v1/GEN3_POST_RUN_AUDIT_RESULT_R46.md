# Phase57 Gen3 R45 — Post-Run Audit and Formal Result

Saved: 2026-09-27 JST
Basis research HEAD: `9cc2e39e9b4b0defc7d6a9a7570701f3fa6c02a8`

## Integrity
- Learning run: 36251316248 — SUCCESS
- Artifact: 10909618948
- Artifact SHA-256: `d3936171002e7579e431568b9900ee5fa1fc8ade3dae0bf6de92870c8dbe4b38`
- Exact tested execution SHA: `a65b3530df53a7a28334d7d1d4218d561e38b06b`
- Protocol SHA-256: `e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5`
- 24/24 fits; 4/4 frozen policies replayed.
- All four policy ledgers plus HOLD_TO_TERMINAL_DIAGNOSTIC are byte-identical between Run A/B.
- providerRequests=0; protectedPartitionsOpened=0; Safety9 all false.
- Learning receipt remained AWAITING_POST_RUN_AUDIT with scorecardsProduced=0 / selection=null before this audit.

## Formal frozen-gate result
**NO_SELECTION_STOP — 0/4 candidates PASS.**

No candidate reached the frozen Overall Mean Net >= +2.00% in both Entry arms. All six bucket gates fail for both arms for all four candidates. The critical >=5% gate (Mean >= +3.25%, Median >= +2.00%, Median Capture >= 50%) fails for every candidate.

| Candidate | IM Mean | IM Median | IM PF | IM >=5 Mean | IM >=5 Median | IM >=5 Capture median | R1 Mean | R1 Median | R1 PF | R1 >=5 Mean | R1 >=5 Median | R1 >=5 Capture median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | +0.161% | -0.384% | 1.133 | +1.503% | -0.255% | -1.712% | +0.221% | -0.307% | 1.196 | +1.568% | -0.100% | -0.204% |
| 02 | +0.161% | -0.384% | 1.133 | +1.503% | -0.255% | -1.712% | +0.224% | -0.307% | 1.200 | +1.578% | -0.100% | -0.204% |
| 03 | +0.161% | -0.384% | 1.133 | +1.503% | -0.255% | -1.712% | +0.221% | -0.307% | 1.196 | +1.568% | -0.100% | -0.204% |
| 04 | +0.161% | -0.384% | 1.133 | +1.503% | -0.255% | -1.712% | +0.224% | -0.307% | 1.200 | +1.578% | -0.100% | -0.204% |

Candidate 02 is shown diagnostically only; it is NOT selected. Its bucket means (IM/R1) are:
- <1%: -0.672 / -0.615
- 1–2%: -0.645 / -0.541
- 2–3%: -0.645 / -0.638
- 3–4%: -0.373 / -0.446
- 4–5%: -0.188 / -0.096
- >=5%: +1.503 / +1.578

For Candidate 02, frozen relative Profit Retention and Loss Containment gates pass in both arms, but Winner Continuation fails in both arms. >=5% candidate Capture medians (-1.712% IM, -0.204% R1) are far below the neutral diagnostic medians (20.764% IM, 22.654% R1), with 0/4 winner folds passing in each arm.

## Freeze / Exposure
- Frozen Entry IMMEDIATE / ALL_MATERIAL_R1 unchanged.
- Gen3 protocol, candidates, labels, features, costs and Completion Gate unchanged.
- No fifth candidate, adaptive threshold, label/model/feature change, or Gate relaxation.
- Fresh/OOS/Protected unopened; no new provider retrieval.
- No Final EXIT Freeze because no candidate passed.
- No Capital performance replay.
- main/live/paper/production unchanged; Safety9 all false.

## Current state / next plan
Gen1 (24), Gen2 (16), and Gen3 (4) are all formal negative Development results. Gen3 is closed as NO_SELECTION_STOP. Do not promote the numerically least-bad candidate. Any further EXIT research requires a new performance-before-precommitted architecture/protocol decision; do not modify R45 after seeing these results. Entry remains frozen.
