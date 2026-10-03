# Phase57 LONG-only EXIT v5 BAR5 Fast Track

2026-09-16 JST — **V5_LONG_MEASUREMENT_BLOCKED**

Repo: Iam-2squared/ark-terminal. Branch: research/phase57-long-only-cash-equity. PR #587.
Start head: 59a7c5eac21cf8fed9fecef83957d9e551d405e8. Main: b7801ce2c13772cbc3f5b51506819c119fe868ea.
No main merge or promotion. Final head and its CI are reported in the completion message / GitHub history.

## Result

Selected BAR5 historical simulator semantics were isolated into a mechanical adapter and tested against the actual selected simulator. This resolves BAR5 versus old BAR6 for the supported historical-result interface. **It does not create a standalone online LONG EXIT.**

The final simulator requires a causally eligible v4 outcome before *any* v5 branch. It has no definition for running without that dependency. All277 fixed entries lack the required causal v4 continuation in the recovered evidence. Full v5 replay eligible N=0; Fixed/v5 paired N=0; all paired performance metrics are NULL, not zero returns.

Status: `V5_RUNTIME_SEMANTICS_BLOCKED` for absent causal v4 continuation / standalone runtime. Mechanical adapter status: `BAR5_SELECTED_SIMULATOR_MECHANICAL_PARITY_PASS`. These are different claims.

No v3/v4 comparison, no causal analog construction, no new EXIT tuning. `V5_LONG_MINIMAL_ADAPTATION_REQUIRED` was **not** inferred from incomplete performance, so its conditional authorization to tune a LONG variant was not activated. No LONG EXIT Development Final is issued. Capital Allocation integration remains pending.

## Authoritative source and precedence

Source research branch: `research/phase57-exit-v4-hybrid-msh-large-scale`, current head `ea15a594103bd6c9146f19a4aebafb83067d869b`, remotely verified unchanged.

| Artifact | Identity | Meaning |
|---|---|---|
| Final Candidate | `EXIT_V5_DYNAMIC_RECLAIM_BAR_5` | DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED |
| Final Candidate commit | `417ad9d6dc92c3110e680cdc4a6c8dcf94b4ee5e` | 2026-09-12 20:31 JST |
| Final Candidate file SHA | `a597ea41f277ef10ab4bb4a763d2a1eb87dc45bed7bd32709798d4d77a44c7af` | Full source bytes; semantics projection saved separately |
| Selected sweep implementation commit | `aaa99030295ffb447de273881b16aad1eab1a7e9` | Source of sim(t,5); no sweep executed |
| Selected simulator source SHA | `209f2857a62c1cb7e655417d2769b952b4b9fa3ce4e3c2e99e4c228d6c9664f7` | Archived read-only as final-sweep-source.txt |
| Old first-state router freeze | `de46ec70e0236a793567e5c5b020d4849188f049` | Older v3/v4 router, not Final BAR5 |
| Old dynamic BAR6 freeze | `7d2b204c10763261216e8c7a4db13c4e5cc0645d` | Older dynamic candidate; not silently substituted |
| Review process contract | `15074ef8b84e9d0aec973a71e6d5af3bfbbf1118` | Process contract, not a replacement continuation |

The selected simulator source is archived for exact parity tests. Tests evaluate only its pure `sim(t,5)` fragment with synthetic LONG data; they do not execute top-level research data reads or the horizon sweep. Old mixed-direction performance is not reused as LONG evidence.

## Mechanically resolved behavior

| Condition | Selected simulator behavior | Adapter |
|---|---|---|
| Not causal-eligible or no v4 result | Return null before state logic | Explicit block; no trade |
| First completed directional close >=0 | Return original v4 result | Same |
| First completed close <0 | Inspect original v4 management trace through bar5 | Same |
| Reclaim >=0 at/before bar5 | Return original v4 result | Same |
| No reclaim, bar5 exists in trace | Bar5 completed-close return minus0.05% | Same |
| No bar5 in truncated trace | Original v4 outcome, HORIZON_FALLBACK_V4 | Same; no invented HOLD |
| Early original v4 exit | Preserve truncated-trace fallback | Do not extend trace or re-enter |
| Missing causal v4 | No alternative policy defined | Block even if raw market path has5 negative closes |
| BAR6 | Older candidate | Not used |

The interface accepts finite numeric first-bar fields and rejects missing/null values rather than inheriting JavaScript `Number(null)=0` coercion. Parity is claimed on well-formed numeric inputs only. Neither this input guard nor the adapter selects a new threshold. BAR5 and0.05% cost are fixed. No actual causal v4 outcome is fabricated for any of the277.

The source candidate's intent “DEFENSIVE until BAR5” and the selected simulator's use of a truncated v4 trace do not fully specify an independent live state machine. Continuing through an early v4 exit or replacing absent v4 with Fixed/Session-End would change the strategy, not just field mapping.

## Frozen data and upstream

All277 original ENTER identities retained, 76 sessions2024-09-17–2025-01-09, direct Entry Development / IN-SAMPLE. Historical BORDERLINE; Fresh Validation PENDING. No Fresh, OOS, Prospective or production claim.

| Pin | SHA-256 |
|---|---|
| Candidate Contract | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` |
| Final model | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` |
| Final scaler | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` |
| Selector payload | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| Selector Ridge | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| 277 ENTER ledger | `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236` |
| Global195 Budget | `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f` |
| Prior derived path (uncompressed) | `01543fb3c003f939d73567280f9141392f254f1ec3c058b3163f5dede33fc5fd` |
| This pre-diagnostic contract | `f3f755b375977308e8f5c2693d72b18d7bc20a18031f54727357bf7755f4552a` |

All source pins in the prior diagnostic contract were rechecked, plus exact field-by-field identity for277 entries. Entry threshold2.0 / model / scaler / features / state remain unchanged. No prediction or original Entry replay.

Only the saved, authorized path artifact from run35091141862 is reused. The earlier unused diagnostic run35087975004 remains unused. No raw encrypted checkpoint recovery or provider access was needed in this task.

## BAR5 raw-path prefix diagnostic — not full v5 transitions/trades

| Observation | Count |
|---|---:|
| Original fixed entries | 277 |
| First completed trading bar observable | 250 |
| First close non-adverse; requires v4 | 189 |
| First close adverse | 61 /250 (24.40%) |
| Reclaim observed by BAR5 | 33 |
| Five completed negative closes, no reclaim | 25 |
| First adverse observed, subsequent prefix missing | 3 |
| First bar missing | 7 |
| No remaining bar | 20 |
| Total UNKNOWN prefix | 30 |
| Reclaim / all observed adverse | 33/61 (54.10%; lower bound with3 unknown) |
| Reclaim / resolved adverse prefix | 33/58 (56.90%) |
| Reclaim at bar2 /3 /4 /5 | 19 /6 /4 /4 |
| Actual v5 RECOVERED / forced EXIT counts | NULL /NULL |

BAR1 means next completed **trading** bar, not necessarily wall-clock+5m. Lunch is skipped in bar indexing while clock elapsed time is retained. This explains250 first trading-bar observations versus225 strict wall-clock+5m observations in the previous report; it is not new Entry selection or missing-bar fill. Missing expected slots are UNKNOWN. No-trade is not silently assumed flat. The existing session-end/15:25 auction representation is retained as unresolved and is not needed for a complete first-five-slot prefix. Session-End is omitted from the main comparison as authorized.

Using available strict30m CLOSE only as a separately labelled diagnostic:9/24 observed-reclaim cases are below Entry at30m;4/21 no-reclaim-through-BAR5 cases are at/above Entry at30m. These are **not** v5 final winner rates, false recovery, false defensive exit or realized returns. Future MFE/MAE is not used by the adapter. Intrabar HIGH/LOW ordering is not inferred.

## Requested Fixed vs v5 metrics

| Metric family | Fixed on common eligible set | V5 BAR5 |
|---|---|---|
| Eligible N | 0 | 0 |
| Net sum / mean / median / win rate / PF / worst | NULL | NULL |
| DD / MAE distribution / p05 / MAE<=−10 cohort final loss | NULL | NULL |
| Tail reduction vs Fixed | N/A | NULL |
| MFE / capture / giveback / +3,+5 winner final net | NULL | NULL |
| Premature exit / saved or lost winner | NULL | NULL |
| Actual recovered final winner / non-recovered final return | N/A | NULL |
| False recovery / false defensive exit | N/A | NULL |
| Top1/3/5, symbol/session concentration | NULL | NULL |

Fixed alone has173 path-available identities under the previous definition; they are not mixed with zero eligible v5 trades to manufacture a paired comparison. Previous41-session-end-complete reference results are not relabelled as this task's v5 performance. No portfolio Max Drawdown is inferred from a missing v5 return series.

## Minimal resolution proposal and next action

The mechanical solution is complete only for a caller supplying an original causal v4 result and matching management trace. It cannot solve absence of that research dependency. New causal analog construction is explicitly stopped per this request.

To move beyond the block, explicitly contract a **new LONG continuation policy** replacing the unavailable v4 dependency, with treatment of first non-adverse, reclaim, unrecovered bar5, early continuation exit, missing bars, lunch and session boundary specified before measurement. That is a new LONG Development strategy version, not unchanged v5 or a mechanical adapter. This report does not choose Fixed12, Session-End, bar6 or any favorable replacement.

The current instruction permits tuning only after a measured `V5_LONG_MINIMAL_ADAPTATION_REQUIRED`; a runtime block cannot satisfy that condition. Therefore no alternative is tuned or promoted here. Exact next action is to resolve that new-continuation design authorization/specification, while keeping Entry frozen and the195 Fresh budget intact. This is a single concrete dependency, not a request to reopen v3/v4 research.

## Verification and safety

Focused offline tests:16 PASS (BAR5 source parity/boundaries6; artifact/identity/reproducibility3; existing upstream freeze7). The final-head GitHub checks are verified after publication. A green integrity CI is not scientific validation.

Entry changes=0; Selector changes=0; v3 replay=0; v4 replay=0; full v5 replay=0; analog pools built=0; EXIT fit/tuning/sweep=0; J-Quants/Yahoo/other market-data requests=0; Fresh/OOS accesses=0; Fresh budget consumption=0; SHORT market evaluation=0; forward-fill/interpolation/future substitution=0. Synthetic SHORT rejection is a safety test, not a market evaluation.

All false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

**STOP — V5_LONG_MEASUREMENT_BLOCKED.** No LONG EXIT Development Final; Capital Allocation not started.
