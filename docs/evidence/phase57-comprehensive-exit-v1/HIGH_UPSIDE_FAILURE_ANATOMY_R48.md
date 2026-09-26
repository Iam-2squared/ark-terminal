# Phase57 R48 — High-Upside Failure Anatomy

Saved: 2026-09-27 JST
Basis: R47 research-only historical simulation. Prior Gen1-3 results remain unchanged.

## Source
- R45 run 36251316248 / artifact 10909618948
- artifact digest d3936171002e7579e431568b9900ee5fa1fc8ade3dae0bf6de92870c8dbe4b38
- execution SHA a65b3530df53a7a28334d7d1d4218d561e38b06b
- protocol SHA e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5
- Development only; no protected/fresh/OOS data and no new provider retrieval.

## Large-upside evaluator slices
IMMEDIATE scored 1,150 entries: canonical >=5%=387; post-entry best-high >=5%=222; overlap=222.
R1 scored 1,107 entries: canonical >=5%=381; post-entry best-high >=5%=200; overlap=200.
Therefore 346 canonical >=5% scored cases had less than 5% remaining post-entry upside. Both slices must be reported separately; neither is an input feature.

## Gen3 overlap-slice result
All four Gen3 policies evaluated 422 overlap cases. Mean net was about +4.03% to +4.04%, median +2.516%, but median post-entry capture was only 30.28%. Candidates 01/03 closed 68 cases before the later best high; 02/04 closed 67.

Candidate 02 premature cases: 67 total; 61 came from NEUTRAL_DETERIORATION and 6 from PROTECTION. Their median net was -1.293%, median capture -14.94%, and median later missed opportunity 10.326pp.

## Root cause
Among 32,787 fresh overlap-winner checkpoints before the later best high:
- 12,368 (37.72%) were weak-state checkpoints.
- 2,163 showed causal recovery-like evidence.
- 1,870 matched the prior multi-evidence weak geometry.
- 600 matched the prior neutral-bad geometry.
- 190/422 overlap winners had at least one such pre-high bad-looking checkpoint.

Weak-looking NOW states are therefore common before later expansion.

## Strong NOW-known separators
Weak pre-high versus weak post-high medians:
- certified giveback: 1.884pp vs 6.536pp
- certified MFE: 1.941% vs 6.961%
- active bars held: 57 vs 149
- time since peak: 15 vs 64
- history.3 RECLAIM false: 0 vs 2
- history.3 CONTINUATION false: 0 vs 2
- Pattern187 STRUCT/Lrising: 1 vs 0

One-to-five active bars before the later best high, median current return was +5.77%, giveback 0.62pp, weakRun 0 and momentum5 +1.21%. Six-to-fifteen active bars after the high, medians were +4.62%, giveback 3.38pp, peak age 9 and momentum5 -0.43%. At 16+ bars after, current return fell to +1.61%, giveback rose to 7.05pp, peak age to 78, signalTrueN to 0 and signalFalseN to 3.

## Architecture implication
The next finite historical-simulation protocol should prioritize continuation and harvest of large post-entry upside. It should remove the prior early neutral-weakness authority, require explicit recovery/continuation vetoes, and make the main deterioration authority depend on mature owned-profit geometry plus persistent failed continuation rather than weakness or negative current return alone. A separate extreme-tail guardrail may remain.

No next-generation candidate was replayed or selected here. Exact labels, model family, finite candidate set, thresholds, selection rule and completion gate must be frozen before any next-generation performance is observed.
