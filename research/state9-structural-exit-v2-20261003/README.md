# STATE9_STRUCTURAL_EXIT_V2

Frozen Entry 1,600件を変更せず、Frozen State9のUP context生命周期をそのままHOLD/EXITに使用した単一zero-fit研究実装。最終結果は[REPORT-ja.md](REPORT-ja.md)。正常終了点は `STATE9_STRUCTURAL_EXIT_V2_EVIDENCE_READY`。EXITの正式採用、追加policy、Re-entry、Capital、main mergeへ進まない。

研究decision contractは[CONTRACT.md](CONTRACT.md)。性能結果を見る前に固定し、[CONTRACT_FREEZE_RECEIPT.json](CONTRACT_FREEZE_RECEIPT.json)に保存した。これは正式EXIT採用のFreezeではない。Full trace、Replay、評価、独立監査は別の実装ファイル。v1は継承された失敗Evidenceのまま閉じ、内容を開かず、再実行・比較しない。

## Evidence

| 内容 | ファイル |
|---|---|
| 6 Frozen pins・Entry・source identity | `IDENTITY_RECEIPT.json` |
| Full State9/Path再構築・saved overlap | `FULL_TRACE_RECONSTRUCTION_RECEIPT.json` |
| 1,600件Replay・sell source | `REPLAY_RECEIPT.json` |
| coverage・arm時間・suspension | `LIFECYCLE_COVERAGE.json` |
| 全体、累積/排他Winner、≥3/≥5詳細 | `ALL_ENTRY_ECONOMICS.*`, `WINNER_*.*` |
| armed/never、Entry Primary/context、EXIT理由 | `ARMED_VS_NEVER_ARMED.*`, `ENTRY_PRIMARY_CONTEXT.*`, `EXIT_REASON_DECOMPOSITION.*` |
| 全件独立検算、24項目への対応 | `INDEPENDENT_AUDIT.json`, `AUDIT_GATE_MAP.json` |
| container復元・非semanticコード修正 | `TRACE_CONTAINER_RECOVERY_RECEIPT.json`, `IMPLEMENTATION_IO_CORRECTIONS.json` |
| private ZIPのhash・保存結果 | `PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json`, `PRIVATE_EVIDENCE_SAVE_RECEIPT.json` |
| 四つのcheckpoint | `CHECKPOINTS/` |

Full traceと個別position rowsは `Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip` に保存。1,600本のFull trace、523,200 scheduled endpoints、全formal responseとPath events、1,600 Replay/economics rows、Frozen Entry原本gzip、対象1,600件のsaved raw/M0 source subsetを含む。private row-level dataはGitHubへ公開しない。

## 再現

Python 3.11以上、NumPyのみ。ネットワーク、provider、broker、modelライブラリは不要。通常のcheckoutを `<workspace>/ark-terminal/` に置く。`settings.py` のI/Oはその親workspaceの `inputs/` と `private_structural_v2/` を使う。既存Evidenceを上書きしない別workspaceで実行する。

二つの既存private source packageを `<workspace>/inputs/library_sources/` に用意する。

| package | SHA256 |
|---|---|
| `Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip` | `0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7` |
| `Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip` | `c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15` |

```bash
cd ark-terminal/research/state9-structural-exit-v2-20261003
python3 bootstrap_local_inputs.py
python3 -m unittest test_lifecycle.py
python3 reconstruct_trace.py --workers 4
python3 replay.py
python3 evaluate.py
python3 independent_audit.py
```

`bootstrap_local_inputs.py` はpackage SHAを検証して必要な5 source membersだけを開く。既存モデル、teacher、旧EXITのmembersは開かない。`FROZEN_ENTRY_IO_CONTRACT.json` はこのWorkが使った既存Entry I/O contractの保存bytesで、列順の参照だけに使う。Entry authorityはoriginal Frozen record gzipとFrozen HEADであり、Entry decisionを再実行しない。`FROZEN_SOURCE/` の6 pinsとcandidate/independent kernelはbyte-identical。

gzip streamのmtimeは0。圧縮実装が同じならcontainer SHAを再現できる。別Python/zlib環境では圧縮bytesが変わり得るため、formal response全値とPath eventsも比較する。今回の実環境で73本の不完全なgzip containerが発生し、全て最初に記録されたSHAのbytesへ復元してからReplay・auditを完了した。原receiptは上書きせず、復元経緯を保存した。

Historical `actual_known_at` はUNKNOWN、availabilityはFrozen Entryと同じbar_end仮定。未来leakage=0はこのcausal mapping内の全件検算結果。終値約定はexact dated terminal-auction sourceのみ、欠落はUNRESOLVED。Full-session pathが不完全な場合、観測Highとobserved Winnerをcomplete-session Highへ読み替えない。

全safety flags=false。LONG-only / cash-equity-only。teacher/model/OOF/score/rank/search/provider/新market data/State9変更/Path変更/Hard1/fixed stop/trailing/旧EXIT/Re-entry/Capital/Portfolio/orders/main merge/force pushは0。
