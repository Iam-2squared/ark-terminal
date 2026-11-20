# Phase57 WPSD EXIT — Controlling Handoff

Saved JST: 2026-09-28 22:05  
Repo: `Iam-2squared/ark-terminal`  
Branch: `research/phase57-long-only-cash-equity`  
Draft PR: #587

## 🧭 Cycle

**Winner-Preservation Structural-Damage EXIT is CLOSED at Phase 0: `PHASE0_NO_GO`.**
No WPSD candidate was implemented or selected. `selected=null`; production readiness remains false. This is a completed, precommitted negative research result, not an R54 reopening.

| Fixed item | Value |
|---|---|
| Selector | `FROZEN` |
| Entry | `IMMEDIATE` / `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF` |
| Entry Dual Freeze | `4878a1cc53430e816261dea0fb16aeb53b3c238d` |
| Capital | `SAVED_CAPITAL_V3_B_CI_RANK_AND_R37_SIZING_ONE_SHOT_ENTRY` |
| Control EXIT | `R50_A_LIFECYCLE` |
| Universe | LONG / CASH only; ¥1,000,000, 100-share lot, MAX3 |

R54 corrected Cycle2 remains **CLOSED**, integrity PASS, D incremental skill FAIL, Winner Gate FAIL, economic measurement blocked, and selected=null. Its teacher pin is `a017a10b…`; old R52 recovery is not the active instruction.

## 🔬 Phase 0 — precommitted separability

`PHASE0_PRECOMMIT.json` was committed before FIRST_DAMAGE_EVENT analysis. Its SHA256 is `792c05ab2bd4e8e6222baecfdaa5b7a7990cc97108a9137d03bd3ae0bc703332`. All frozen Entry checkpoints were scanned only through their individual saved Control lifecycle. One first Damage Score ≥1 anchor per Entry was selected without using R54 SELL as an anchor; post-entry upside was joined afterward for evaluation only. The bootstrap resampled 24 sessions with replacement, seed 52, 10,000 draws.

| Primary R50-funded arm | Entries / anchors | Defense <5% | Winner ≥5% | AUC |
|---|---:|---:|---:|---:|
| IM | 79 / 79 | 52 | 27 | 0.465456 |
| R1 | 32 / 32 | 20 | 12 | 0.508333 |
| Combined | 111 / 111 | 72 | 39 | **0.477920** |

Combined AUC 95% session-bootstrap CI: **[0.331841, 0.609957]**; 10,000/10,000 valid draws. Its lower bound is below the required strict 0.5. IM AUC is below 0.5, so the arm direction test also fails. The ≥10% subset has 23 primary Entries and is included within ≥5%, not added to it.

| Secondary all-Entry arm | Frozen | First Damage anchor | No anchor | Defense median Damage | Winner median Damage |
|---|---:|---:|---:|---:|---:|
| IM | 819 | 800 | 19 | 1 | 2 |
| R1 | 795 | 770 | 25 | 1 | 2 |
| Combined | 1,614 | 1,570 | 44 | 1 | 2 |

Both secondary arms reverse the required median direction. All 44 no-anchor Entries had evaluable checkpoints but never reached Damage ≥1; they were reported separately rather than counted as failures or assigned a score. There were no missing upside labels among anchored Entries.

| Frozen GO clause | Outcome |
|---|---|
| Primary combined AUC CI lower >0.5 | **FAIL** |
| IM and R1 Damage direction not reversed | **FAIL** (IM) |
| Both all-Entry arms: Defense median ≥Winner median | **FAIL** (both) |
| Pinned source lineage / historical as-of / safety | PASS within stated scope |

## 🧠 Structural Damage and 🛡 Preservation

F1 is `DROP`; F2 requires at least two known critical signals and known FALSE majority; F3 is R34 as-of Net ≤0 with a known zero upRun; F4 is signal loss or failed recovery. UNKNOWN casts zero vote and remains separately unavailable. P1–P4 produce a veto when at least two hold. The handoff's single-FALSE prohibition was resolved in PRECOMMIT before the results: one lone FALSE cannot make F2 vote.

| Primary first anchor | Defense <5% N=72 | Winner ≥5% N=39 |
|---|---:|---:|
| F1 vote | 54 (75.0%) | 31 (79.5%) |
| F2 vote | 39 (54.2%) | 16 (41.0%) |
| F3 vote | 34 (47.2%) | 24 (61.5%) |
| F4 vote | 0 | 0 |
| F4 UNKNOWN | 72 | 38 |
| Preservation veto | 17 | 11 |
| Median Damage | 2 | 2 |

F1 fires frequently in both groups, while F3 fires more often in Winners. F4 is unknown for **110/111** primary anchors and supplies no primary vote. At all-Entry anchors, F4 is unknown for **1,493/1,570**, with 18 votes. The first primary Damage anchor falls in the early time bin for 101/111 Entries. This early concentration and source availability constrain the four-family architecture; UNKNOWN is not a proxy for a Winner.

The raw complete-prefix diagnostic is available at 104/111 primary anchors (Defense 68/72; Winner 36/39). It is descriptive, not early SELL authority. Historical closed-bar end serves as an as-of proxy; provider publication timing and live readiness are not certified.

## 🏆 R54 Winner-loss tail — supplemental

These are negative **R54 minus Control** paired trade deltas only, not WPSD performance. ≥10% is a subset of ≥5%. IM and R1 are alternative Entry worlds and cannot be added as portfolio PnL.

| Arm / post-entry upside | Negative paired trades | Gross negative deltas | Worst 3 share | Trades covering half |
|---|---:|---:|---:|---:|
| IM ≥5% | 13/27 | ¥353,000 | 62.46% | 3 |
| IM ≥10% | 7/15 | ¥299,800 | 73.55% | 2 |
| R1 ≥5% | 5/12 | ¥269,800 | 83.65% | 2 |
| R1 ≥10% | 4/8 | ¥266,500 | 84.69% | 2 |

## 💴 Downstream measurement and 🎯 Month 2x

| Stage | WPSD cycle result |
|---|---|
| WPSD_K2 / WPSD_K3 implementation and focused tests | Not run: Phase 0 NO-GO |
| Candidate Layer A Winner / Loser Gate | Not run |
| All-Entry candidate standalone | Not run; Phase 0 all-Entry diagnostic completed |
| Capital integrated Replay / fee stress | **0 / 22 invocations**; not run |
| Candidate reproducibility / 24-session Final Equity / DD | Not measured |
| ¥2,000,000 target and +2.93%/day gap | Not measurable for WPSD |

The known R54 auction/mark blockers (`2025-07-23|62650|883`, `2025-08-04|36700|602`) remain separate facts. No WPSD portfolio was run, so WPSD economic measurement status is **NOT_RUN_DUE_TO_PHASE0_NO_GO**, not a manufactured Final Equity or a new Capital failure.

## 🔁 Independent audit and 🔒 Safety

The independent read-only audit reproduced all 1,570 anchor IDs against R45 row identities and Control decision cutoffs, all source hashes and four output digests, State/signal/F1–F4 values at the anchors, AUC and the 10,000-draw session bootstrap. It found no discrepancy in the recorded NO-GO. The corrected R54 teacher's original bytes were not locally present, so its historical SHA is an upstream protocol/closure attestation, not an independent rehash here.

| Added in this WPSD cycle | Count |
|---|---:|
| Estimator fits / integrated Replay / threshold searches | 0 / 0 / 0 |
| New provider requests / Protected, Fresh, Validation, OOS opens | 0 / 0 |
| Orders / main merges | 0 / 0 |

All nine execution, broker, Excel order, RSS order, live trading, paper trading, automatic promotion, production update and transmission flags are false.

## ✅ Final boundary

`PHASE0_NO_GO / NO_SELECTION / selected=null / productionReady=false`.

Do not tune WPSD K, the four families, the veto, or grace in this cycle after seeing the outcome. A different EXIT idea needs a fresh pre-performance architecture cycle. R54's corrected closure remains unchanged.
