# Final Validation model / Candidate2 artifact construction

Final model construction and integrity checks PASS. Required CI is pending; candidate freeze has not yet been issued. No Development performance was recomputed.

| # | Item | Result |
|---|---|---|
| 1 | Branch / PR / head | research/phase57-long-only-cash-equity / #587; source remote c19f599394a4df9f47f9284f7b9932859a4d5a97; tested remote head to be attested after CI |
| 2 | Latest main | 6b6c4d522cd1863132185463a0aed74bc819be01 |
| 3 | Selector SHA verification | PASS payload 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59; Ridge reference 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb (raw archived Ridge artifact not reacquired) |
| 4 | Fit Contract SHA | PASS 64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938 |
| 5 | Development Evidence SHA | PASS 68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead |
| 6 | Final Scope Contract | e18208a42ac034fde1f746c2f51146660f76080b33abaafe940ac6e85067686b; local pre-fit commit913981526b041f801be8493f9b62591c1ef374cc; additive contract, original historical finalAll76SessionRefit=0 unchanged |
| 7 | Training sessions | 76; 2024-09-17 through2025-01-09 |
| 8 | Session-list SHA | de4a4264a7d78446ff01f72c2f927cc29ec45b18126068ca2e9dc2cfe16c5483 |
| 9 | Selection events | 3800 /2743 symbol-sessions, repeated events correlated |
| 10 | Labelable rows | 1828; excluded1972: PROVIDER_GAP1424, LUNCH_BREAK380, SESSION_END168 |
| 11 | Training event identity SHA | c9ede1c330b1e5a4ab1765fa901a14258831a17be9a024c4ba7a56db418d8e06; payload SHA c323c2c8a329f5b6139f4c5887d75aed392527663f2a5af3edde43c56ba9a63f |
| 12 | Class0–4 counts | [606, 423, 271, 281, 247] |
| 13 | Feature order | frozenSelectorRidgeScore, frozenSelectorRidgeRank; optional none, price reference-only |
| 14 | Feature-order SHA | 7cc53df7093fdc34c14064115ba1b7ec57db9b526b1faf911d0255acbb3afbb3 |
| 15 | Final scaler mean/std | [60.20117963955238, 2.87636761487965] / [28.058491066824175, 1.4080223185525331]; ddof0; training1828 only |
| 16 | Final scaler SHA | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| 17 | Beta | [0.5459597493940448, -0.06632959941610062] |
| 18 | Cutpoints | [-0.7743958055133714, 0.2336052868133186, 0.9290677945713551, 1.960798088784609] |
| 19 | Lambda | 1.0, slopes-only; no cutpoint penalty |
| 20 | Solver/config | SciPy1.17.0 L-BFGS-B; maxiter2000, ftol1e-12, gtol1e-8; NumPy2.3.5/Python3.12.14 |
| 21 | Convergence | success=true status0 nit12 nfev15 njev15; CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 22 | Final objective | 2740.4209737429937 = SUM NLL + slope-only L2; fit diagnostic, not performance evidence |
| 23 | Model artifact SHA | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| 24 | Implementation SHA | 9e5910c476c6957aab65cc24490ffb2759084e5e49b36db42fe284674979ae74 |
| 25 | Serialization | EXACT_SYNTHETIC_PROBE_PROBABILITY_EQUALITY |
| 26 | Determinism | EXACT_ARTIFACT_AND_PROBE_EQUALITY |
| 27 | Probability integrity | PASS_INTERNAL_ALL_TRAINING_AND_FIVE_SYNTHETIC_PROBES; no probability/score distribution inspected |
| 28 | Development performance re-evaluation | 0 |
| 29 | OOF regeneration | 0 |
| 30 | Threshold performance search | 0 |
| 31 | Validation access | 0 |
| 32 | OOS access | 0 |
| 33 | Project EXIT access | 0 |
| 34 | Yahoo requests | 0 |
| 35 | J-Quants requests | 0 |
| 36 | Other market-data requests | 0 |
| 37 | Offline regression | 2847 unique suite tests PASS /0 FAIL /0 SKIP; Foundation39 repeated subset;6 network guard probes PASS |
| 38 | GitHub CI | PENDING_REMOTE_PUBLICATION; Freeze not issued until required CI PASS |
| 39 | Threshold Candidate | 2.0 only, not adoption;1.0 frozen scalar winner retained as historical fact, no replacement metric |
| 40 | Decision score | E[L]=0P0+1P1+2P2+3P3+4P4 in[0,4]; expected ordinal level, not return |
| 41 | State | ENTER if E[L]>=2.0 and not already entered in symbol-session; otherwise SKIP_THIS_DECISION; no WAIT/expiry/persistent SKIP |
| 42 | Candidate Contract SHA | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| 43 | Safety | All12 safety fields false (including all9 required flags) |
| 44 | Completion verdict | PENDING_REQUIRED_CI; not yet frozen |
| 45 | Exact next action | After CI and attestation: STOP. Separately preregister Validation dataset identity before access and authorize one frozen2.0 evaluation; no automatic Validation/OOS. |

## Fit accounting and network protection

One final construction fit/scaler plus one explicitly authorized determinism verification fit/scaler recomputation. The second fit was only executed after the first fit and reload/probability checks passed; its artifact is not a candidate. Frozen fit internally validates all1828 training-row probabilities per fit. Outside that required integrity check, only five deterministic synthetic probe inputs were predicted. No external Project predictions, threshold decisions, score distribution, training quality, CV or OOF were generated. Synthetic regression model fits are separate from these Project counts.

Construction and regression ran under the existing inherited seccomp Internet socket/connect guard plus Python/Node fail-closed audit. Unexpected network attempts0; market-data requests0 confirmed for those process trees. Six synthetic guard probes intentionally test blocking; they transmit no requests. GitHub reads/writes and CI package installation are not market-data requests.

## Existing evidence protection and limitations

Only additive scope, construction script, artifacts, candidate contract, tests and reports. Frozen Selector/model implementation/Fit Contract/Development OOF/reports and fold artifacts are byte-unchanged. OOF SHA1428f222b19203bc6736cf4ef3bd3ae18be068f289657e9c2b59ecbe6ec44c34; Development report SHAeb5cff588991543e5900d1b7b6827f8e567d72633326168d6508b20f7dc692e0. Existing BORDERLINE verdict and original selectedThreshold=null remain historical evidence.

- Strict30m trueMAE absent Development ledger; not computed or substituted.
- CURRENT Entry only24/66 strict30m comparable PASS; not fully paired.
- Development coverage is future-labelable subset coverage, not operational coverage.
- Saved Selector cadence10 decisions/session approximately30m, not5m.
- Development-only and upstream Selector outcome-exposed; not end-to-end OOS.
- Only Selector Score+Rank, no independent market timing information.
- Principle-based verdict leaves judgment uncertainty; do not invent numeric gates after Validation.

## Candidate governance

The user-authorized independent review disposition registers2.0 as one prospective hypothesis. This is not a claim that2.0 maximized the Frozen scalar objective;1.0 remains its Development winner. No review artifact was supplied for independent reinspection. No new weights/metrics or retrospective numeric gates were added. Validation1.0/3.0 comparisons and fallback are forbidden. Any FAIL stops v1; BORDERLINE/insufficient evidence stops for review; no automatic OOS.

Validation must freeze a dataset manifest before access under a separate authorization. Prospective decisions cannot use future labelability. Report all events/ENTERS and conditional labelable cohorts separately. Admission Preservation is not return captured; timely admission and remaining opportunity are separate. Strict30m trueMAE uses only the same complete future LOW path, otherwise MISSING. The same10 daily Selector timestamps are required;5mSelector reconstruction is a different experiment.
