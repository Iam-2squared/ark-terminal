# 🧭 未閲覧期間への凍結Entry推論：最小asset確認

実時計JST: 2026-10-06T16:53:21.296236+09:00  
実時計UTC: 2026-10-06T07:53:21.296236+00:00  
basis HEAD: `a295df739a6810dd0081becd04a3380f6136b6ef`  
実行owner: `/root/frozen_asset_recovery`

## ✅ 結論・現状

現在のPrivate ZIPには、凍結P1の前処理・U/Q/Dモデル本体・参照分布・calibration・vocabularyが含まれない。未閲覧期間の固定Entry生成は現時点では未実行・未準備。既存Signモデルやtrain indicesで代用せず、正規Freezeから必要な9資産だけに絞って復元する。

| 最小確認 | 結果 |
|---|---:|
| 既知ZIP2個のP1推論41資産 | 含有0 |
| 既知ZIP内P1 train indices | F1〜F5の5個 |
| Actions metadata確認 | 最新900件 |
| 凍結Entry branchのActions runs | source export2件のみ |
| 追加payload取得／新fit／provider request | 0／0／0 |
| 保護body開封／Entry-EXIT再実行／GitHub変更 | 0／0／0 |
| 最新F5推論subset | 9資産、10,968,190 bytes（未圧縮） |

## 📦 必要な一点

正規 `Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip` の **P1_F5推論subset＋元manifest hash証拠**。現調査で取得可能な該当artifactは特定できていない。全repo歴史を無制限探索せず、既知metadata範囲の確認で終了する。

- 正規overlay: 271,218,356 bytes、SHA256 `0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7`
- base依存: `Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip`、524,938,461 bytes、SHA256 `c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15`

overlay/base全体は本作業の32MiB取得上限を超える。新sourceへの推論に必要なのは下記9資産で、元historical全再実行のためのbase RAW／全matrixを一括再取得する必要とは分ける。

| 必要asset | bytes | SHA256 |
|---|---:|---|
| `PRIVATE_MODELS/P1_F5_preprocessor.pkl` | 2,237 | `4f683c4ab77899a8fa5e8c02c2cefc213c4086b8604e02d3b4b6ff1a37a7b8fd` |
| `PRIVATE_MODELS/P1_F5_UPSIDE.pkl` | 339,831 | `e73d6310e465fcc3388d81ee8e76f51b857cbbe8da8687e5952769e0becb113a` |
| `PRIVATE_MODELS/P1_F5_QUALITY.pkl` | 338,048 | `9daa2a3b820051f7455e7328b9722fc883a00c8d1d417f0065e081775ee5c597` |
| `PRIVATE_MODELS/P1_F5_ADVERSE.pkl` | 339,728 | `aa456778ab8db0bab5eaff893c9cecfda8588333594a5af2b5331a0e854a044c` |
| `PRIVATE_MODELS/P1_F5_UPSIDE_train_prediction_reference.npy` | 3,311,648 | `6c9a961f2848d26bbc6e62d2d833f334215ca5aaccd4589e0ffbf926b66b75ce` |
| `PRIVATE_MODELS/P1_F5_QUALITY_train_prediction_reference.npy` | 3,311,648 | `909216ce5c06dc6f88094a1013e851dc80fd0b02d5cba427ebdb804fa2f3dfce` |
| `PRIVATE_MODELS/P1_F5_ADVERSE_train_prediction_reference.npy` | 3,311,648 | `74bd86bd2fdfe0a3be4319c99943974f808480d94bd28adc331d11c0c39add6d` |
| `PRIVATE_MODELS/P1_F5_calibration.json` | 494 | `714bdab6166401fd71d01a43914e1c135e328cfa0e8c3999f5527f96abf9de65` |
| `PRIVATE_INPUTS/category_vocabulary.json` | 12,908 | `08f5376e2d31914d1809222d922eef393e46f8cd60ba9125b98cb4e628fb2b1c` |

## 🔒 元モデルと次の方針

保存済み最新foldはF5。学習終端2025-08-06、purge2025-08-07、旧OOF対象2025-08-08〜08-25。Q70閾値は0.5833145705496771。原scoreは `(U_pctile + Q_pctile + (1-D_pctile))/3`、各percentileは元outer-train予測分布のmidrank。閾値や原headを新fitで作り直さない。

元前処理 `TrainPreprocessor.transform` →保存済み各model `predict` →固定参照分布 `percentile` が推論入口。周辺 `run()` はfitを実行するため今回呼んでいない。元causal featuresとfirst-cross machineも既存定義を維持する。

Fulltrain／より新しいproducer、およびF5を旧OOF範囲の後へ適用するrouting・availability契約は確認できていない。asset復元だけでFresh評価開始済み／productionReadyとはしない。次の未閲覧期間のauthorized source、固定producer routing、時点境界、Signの有限候補・予算・合否・終了条件を結果閲覧前に明示する。今回の調査は閉じた実験の再開や保護partition開封を承認しない。

`FRESH_FIXED_ENTRY_ASSET_READINESS.json` に原本asset41件の所在を記したinventoryへのhash、public code pin、関連artifact7件のID／サイズ／digest／expiryを残した。既知900metadataでの不在は、別のprivate保存先や削除済み資産まで不存在と証明するものではない。
