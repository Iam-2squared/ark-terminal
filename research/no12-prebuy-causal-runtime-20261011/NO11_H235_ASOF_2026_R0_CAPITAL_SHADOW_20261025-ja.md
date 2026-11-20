# No.1.1 — 2026 H2/H3/H5 R0 Shadow + Original Capital V5 read-only bridge

Date: 2026-10-25 JST. Branch: `research/no12-prebuy-causal-runtime-20261011`, PR #592 only. Original Frozen strategy, model weights, PAVA/ML, Capital V5 logic, main, PR #591 and the existing Excel order setting remain unchanged.

## 1. Decision already made on 2026-10-12

The selected method is `DECISION_TIME_RECEIVED_LATEST_DATA`: use the freshest **closed** RSS bar and State9/Path observation actually received by the PC **by the BUY decision**, not the next hypothetical opening price or the archive's post-fill teacher fields.

This is an **input-semantic change**, even though the original ML weights and math remain byte-identical. Never report the 2025 Frozen score/rank, portfolio P&L, OOF parity or broker execution as reproduced by this alternative. The source of the prior decision is `ASOF_USER_SELECTED_POLICY_20261012.json`.

## 2. New explicit forward model dispatch (Shadow ONLY)

The 24 original models are eight historical OOF blocks × three heads (H2/H3/H5); H5 is the original CORE_P head. The original OOF timeline does **not** define any 2026 model selection. **For 2026-10-26..2026-12-31 Shadow evaluation only**, explicitly select **BLOCK_08**, the latest saved training endpoint (2025-08-20). This is a *new, non-optimized forward deployment experiment*, not an original Frozen policy, production authorization, or a fresh retraining.

The new module `tools/no11_h235_asof_forward_shadow.py`:

- Verifies original public `core_features.py`, `preprocessing.py`, `staircase.py` bytes against their Git blobs. Verifies **all 24 private model files** against the unchanged published SHA-256 and Git blob manifest before any model inference.
- Reuses the original Python `predict_saved` and `staircase.materialize` (three raw probabilities → native PAVA → `ML=(m2+m3+m5)/(base2+base3+base5)`; native S/A/B/C and native tie-break order).
- Starts from the unchanged original `core_features.project` AST and changes exactly two **projection-local accesses**: its `entry['fill_minute']` anchor becomes the latest *received and closed* bar-end, and its `entry['fill_price']/1.0005` calculation becomes the observed *raw closing reference price*. No fictitious fill price is ever inserted. The delay fields use the actual eligible elapsed minutes from Selector/P1 intent to that known bar-end.
- Requires original State9/Path trace records with first-observed JST timestamps and chronological closed bars. Future, out-of-order, excluded PULLBACK/SHARP_DROP, unavailable state, stale or invalid data are rejected. Scores and ranks are saved only in a local private result.
- Prevents a 2026 result from masquerading as original OOF ranking. New score sources never change Frozen model parameters. `newFits=0`, `orderTransmission=false`, `productionReady=false`.

This makes **received-time R0 computation possible** with real, verified private model files, without implying historical rank parity. The newly selected Block08 policy must be validated on actual RSS and independent prospective data before any future production discussion.

## 3. P1 -> State9 -> R0 integration

The existing `tools/no11_rss_state9_p1_runner.py` gains an **optional** `--h235-model-root`.

- Original State9 / Path trace rows, their incrementally emitted events and their PC first-seen timestamps are captured by the RSS stream as it runs. Missing scheduled bars remain missing, never fabricated price data.
- Only an actual `ForwardP1Session` `FIRST_ENTRY_CANDIDATE` becomes a possible H235 as-of snapshot. On the first Q70 crossing, the most recent received closed bar and true P1 score/threshold are bound to that original State9 trace.
- If the last State9 is unobserved or excluded, P1 remains locked but **H235 and Capital do not act**. Private model failures stop the path; no bogus R0 or funding is generated.
- Private H235 R0 batches are written under `--private-root` with a SHA256-derived immutable name. The runner prints only aggregate counters and hashes, not symbol or model scores.
- Without `--h235-model-root`, all existing P1-only behavior remains unchanged.

Example (requires actual complete private RSS/P1 original assets and historical context):

```powershell
python -B research/no12-prebuy-causal-runtime-20261011/tools/no11_rss_state9_p1_runner.py `
  --session 2026-10-26 --through "2026-10-26T10:00:15+09:00" `
  --minute-feed "<LOCAL_PRIVATE_APPROX_VA_JSON>" `
  --selector-events "<LOCAL_PRIVATE_RECEIVED_SELECTOR_JSON>" `
  --previous-context "<LOCAL_PRIVATE_PREVIOUS_CONTEXT_JSON>" `
  --runtime-root "<LOCAL_VERIFIED_P1_RUNTIME>" `
  --h235-model-root "<LOCAL_ORIGINAL_24_MODELS_ROOT>" `
  --private-root "<LOCAL_PRIVATE_OUTPUT_OUTSIDE_REPOSITORY>"
```

The P1 runner still consumes existing saved source receipts, not an automatically running Excel service. Continuous source/Selector feed collection, multi-checkpoint E2E real-data operation, fresh economic validation, execution/partial-fill/account reconciliation and the original EXIT integration are not certified.

## 4. Original Capital V5 (synthetic, optional, not an order)

`tools/no11_h235_capital_v5_shadow.py` converts the above saved **native-math R0-ranked** candidates to the original unmodified `integration/no1-1-msii/frozen-capital-v5/{slot_policy,allocation,execution}.py` via the pinned existing `no11_capital_v5_crlf_safe_synthetic.py` adapter.

The private original `ARRIVAL_TABLE.json` is mandatory and must have **SHA256 `69f8edafb4708e9a7b61b4f85eb92f353049cf21324e1647602e9973f195f999`**, agreeing with `SOURCE_BINDING.json`. Absence, hash mismatch, unknown layout or missing decision-minute counts fails closed. The scenario is explicitly **synthetic account cash**, never a real account authorization. The observed reference is a **shadow funding estimate**, not an actual fill price. Model/slot/amount input is checked; actual Capital Python S/A/B, MAX3, 100-share-lot, reserve and cash allocations are exercised.

```powershell
python -B research/no12-prebuy-causal-runtime-20261011/tools/no11_h235_capital_v5_shadow.py `
  --h235-batch "<LOCAL_PRIVATE_H235_BATCH.json>" `
  --original-arrival-table "<VERIFIED_ORIGINAL_ARRIVAL_TABLE.json>" `
  --synthetic-account-scenario "<EXPLICIT_SYNTHETIC_ACCOUNT.json>" `
  --private-output "<NEW_PRIVATE_FUNDING_RESULT.json>"
```

The 24 private models, original Arrival Table, actual 2026 RSS snapshots and broker/account data are **not present in GitHub CI**. CI runs only genuine original *code* on synthetic inputs, and verifies fail-closed source protections. CI success must never be described as having executed real original model weights or brokerage.

## 5. Unchanged safety and remaining gates

**No real orders, no paper orders, no Excel workbook mutation or Safety reset.** Existing No.1.1 Frozen conditions (MAX3, cash only, 100 shares, personal ownership, PULLBACK/SHARP_DROP, first SELL fill blocks later BUY, structural and 15:20 EXIT) remain immutable. The new Capital bridge is expressly synthetic and **does not authorize any account movement**.

Before considering real orders: finish authenticated RSS continuous reception and real selector receipt clocks, observe real 2026 full-day runtime and H235 as-of changes, validate the new Block08 dispatch and altered feature semantics prospectively, use actual account+broker IDs/partial fills, exercise EXIT/failover and review independent validation. All are presently **BLOCKED/UNVERIFIED** for execution.
