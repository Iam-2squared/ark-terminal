# State9 Structural EXIT v3 Local Guard

単一policy `STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD`。Frozen Entry1,600とv2 Full traceをexact reuseし、State9 confirmed local L0/H0/L1から作る次足有効guardだけを追加した。[REPORT-ja.md](REPORT-ja.md)が必須17回答を含む最終結果。自動PASS thresholdはなく、人間判断でSTOPする。

`CONTRACT.md`と6 decision filesはS0で実Replay前に固定。`frozen_v2_lifecycle.py`はexact v2のPRE/arm/main A/B/quality実装、`reused_fill.py` / `reused_clock.py`はexact source function slices。v2 runnerやState9/Path enginesは含まれず、実行しない。比較は保存済みv2 outcomesだけ。

## Evidence files

| 内容 | ファイル |
|---|---|
| 原traceとEntryのexact reuse | `V2_TRACE_REUSE_RECEIPT.json`, `V2_CODE_REUSE_RECEIPT.json` |
| 結果前contract/code固定 | `CONTRACT_FREEZE_RECEIPT.json` |
| exclusive primary v2→v3 | `EXCLUSIVE_ENTRY_HIGH_PRIMARY.json/csv` |
| ≥5保護・≥5 EXIT-C | `WINNER_GE5_PROTECTION.json/csv`, `WINNER_GE5_EXIT_C.json/csv` |
| C paired・bucket・元v2理由 | `EXIT_C_PAIRED_DIAGNOSIS.*`, `EXIT_C_EXCLUSIVE.*`, `EXIT_C_V2_REASON.*` |
| mechanics・全体・v3理由 | `LOCAL_GUARD_MECHANICS.json`, `ALL_ENTRY_ECONOMICS.*`, `V3_EXIT_REASON.*` |
| 別logic全件監査 | `INDEPENDENT_AUDIT.json`, `AUDIT_GATE_MAP.json` |
| private個別Evidence | `PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json`, `PRIVATE_EVIDENCE_SAVE_RECEIPT.json` |
| 三checkpoint | `CHECKPOINTS/` |

`paired_delta.median`は個別差分の中央値。`group_difference.median`はv3群中央値−v2群中央値。later Highなしはnullで、v2/v3のmetric Nが違う場合は共通known Entryのpaired deltaも見る。Profit givebackはpre-sell peakとfull-session observed Highで分離し、売却後missed upsideは別指標。

## 再現

Python3.11以上、標準ライブラリのみ。NumPy/model/provider不要。既存Evidenceを上書きしない別workspaceの `<workspace>/ark-terminal/` にこのbranchをcheckoutする。全Git-backed v2 public filesは継承済み。

既存 `Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip` を用意する。SHA256は `31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89`。取得できなければ再構築せずBLOCK。

```bash
cd ark-terminal/research/state9-structural-exit-v3-local-guard-20261003
python3 prepare_saved_v2.py /absolute/path/Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip
python3 -m unittest test_local_guard.py
python3 replay_v3.py
python3 evaluate_v3.py
python3 independent_audit.py
```

`prepare_saved_v2.py`はexact ZIP/各component/public manifest hashを確認し原bytesを配置するだけ。Entry、State9、Path、v2 Replayの計算はしない。v3 replayのみ1回。Auditはprimaryをimportしない別latch/ledger/Fraction/calendar/fill/economics。全1,600件を検算する。

個別v3 metadata/economics/paired rowsは `Ark_State9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_20261003_PRIVATE.zip`。元v2 traceは重複保存せずexact hash dependency。コード/reportはこのGit branchのFINAL checkpointを参照。Private row-level dataをGitへ公開しない。

Normal STOP: `STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY`。正式EXIT採用のFreeze、Re-entry、Capital、Portfolio、main mergeへ進まない。全safety flags=false、LONG-only / cash-equity-only。Historical actual_known_atはUNKNOWNで、bar_end availability仮定内の因果検算。Observed Highのsource coverageはv2から引き継ぎ、完全なsession Highとは称さない。
