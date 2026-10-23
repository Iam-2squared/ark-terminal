# No.1.1 — Frozen P1/Q70 score-only再生（2026-10-23）

## 目的と現在地

Stage 4の受領JSONは、244銘柄×10時刻=2,440件の価格・State9入力照合について、ファイルSHA256と集計の内部整合を確認済み。価格とCurrent Stateの重複588件、除外2State外525件は銘柄×時刻の件数で、BUYシグナルではない。元private GZIPは未添付のため、その実バイト再hash・行単位の独立再計算は未実施。記録は [Stage 4 receipt](NO11_STAGE4_FULL244_SOURCE_JOIN_OBSERVED_20261023.json) を参照。

正式private base/overlayを取得して保存SHAと照合し、この作業環境で元P1/Q70の学習済み重み・前処理・保存閾値による**全223,940 OOF行の推論とfirst-cross再生がPASS**。追加fitは0、再学習・再校正なし。公開する実測receiptは [NO11_FROZEN_P1_FULL_REPLAY_OBSERVED_20261023.json](NO11_FROZEN_P1_FULL_REPLAY_OBSERVED_20261023.json) で、実行結果のbyte同一コピー（SHA256 `9faa6cb373fab70f3d05705184168f0d3a3fd94326b971b95dc00427f4d422e9`）。receipt内部整合と公開集計のみであることを独立に確認した。

## 実モデルでの全件再生結果

| 項目 | 実測 |
|---|---:|
| hash確認したprivate artifact | 47 |
| 推論した元P1モデル | 15（5fold×3head） |
| 全OOF行 | 223,940 |
| prediction / percentile / scoreの最大絶対誤差 | すべて0 |
| Q70通過判定の不一致 | 0 |
| canonical Watch | 2,155 |
| 再現したfirst intent / intentなし | 1,631 / 524 |
| first-intent比較の全11項目の不一致 | すべて0 |
| 最初のcrossまでのscore判定 | 86,549 |
| first-intent固定後の行 | 137,391 |
| 追加fit・再校正 | 0 |

5foldの行数は42,760 / 47,202 / 45,271 / 44,320 / 44,387で、合計223,940。86,549判定+137,391固定後行も同じ総数となる。元公開snapshot20件のSHA再照合もすべて一致し、Frozen原本の変更はない。

実行環境はPython 3.12.14、NumPy 2.3.5、SciPy 1.17.0、scikit-learn 1.8.0。保存pickleの `_loss.CyHalfSquaredError` はhash一致済みモデルに限り、canonical `sklearn._loss._loss.CyHalfSquaredError` へ厳密に対応させた。Windows wrapperはCI確認待ちで、ユーザーPCでのscore再現PASSは未確認。

## 最速のPC配置（RuntimeOnly推奨）

この作業環境で全223,940行の再生が完了したため、ユーザーPCでは**約21MBの推論用bundleと一回のscript実行**で、元推論器の配置と固定160行の一致を確認する。bundleは15モデル、前処理・reference・閾値などの原本41ファイルと、各fold32行×5foldのprivate sampleを収録する。原本41ファイルのbyte一致と160行の元base特徴・OOF位置・期待値の完全一致を別途確認済み。公開仕様は [NO11_FROZEN_P1_INFERENCE_PACKAGE_20261023.json](NO11_FROZEN_P1_INFERENCE_PACKAGE_20261023.json) を参照。

| 推論用bundle | 値 |
|---|---|
| ZIP名 | `Ark_No11_FrozenP1_Inference_20261023_PRIVATE.zip` |
| サイズ | 20,883,703 bytes（約21MB） |
| SHA256 | `68d33ac71f90563fa69fcaa7702983db7230dbfefe0f2e23ea1b2942ec08329f` |

1. 配布された推論用ZIPをPCのDownloadsへ保存する。展開はscriptが行う。
2. PR #592の更新済みリポジトリrootで、PowerShellから次の一行を実行する。Python 3.12（`py -3.12`）が必要で、必要な数値計算libraryはscriptが専用venvに揃える。
3. scriptがZIP/memberのhashを確認し、PCに推論器を配置して15モデルで160行を照合する。完了後に表示・選択される小さな結果JSONでPC実行結果を確認する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\research\no12-prebuy-causal-runtime-20261011\windows\Run-No11FrozenP1ScoreReplayReadOnly.ps1" -RuntimeOnly
```

ZIPを別の場所へ保存した場合は、同じコマンドに `-RuntimeBundleArtifact "推論用ZIPの保存場所"` を追加できる。指定を省略すると既知の保存場所を探し、見つからなければファイル選択を開く。

配置tool自体も作業環境（Linux）で実bundleを使って実行済み。43memberの検証と15モデル・160行の推論がPASSし、全foldのprediction / percentile / score / 4閾値の誤差と判定不一致はすべて0。sample実行receiptのSHA256は `d50a4f8ec5b7096c12a5bc39c73f4ccce4f875c9505fda016a49f9e0253e7f5b` で、`windowsRuntimeObserved=false` を保持する。

`-RuntimeOnly` の合格範囲は**PC推論器の配置と160行sampleの推論一致**で、`fullOofReplay=false` を保持する。全223,940行・2,155 Watchのfirst-cross一致は上記の既存全件receiptを参照し、sample実行による再確認と混同しない。**ユーザーPCでのPASSはまだ未確認**。追加fit0、2026日付のfold選択・live特徴量生成・注文は行わない。

## 実行方法と入口

| 実行方法 | 入力と確認範囲 |
|---|---|
| `-RuntimeOnly`（PC配置に推奨） | 推論用bundle一つ。15モデルの配置と固定160行sampleのscore一致。 |
| flagなし（全件replay） | 元baseとcorrected overlay。全223,940行のscoreと全Watchのfirst-cross一致。既にこの作業環境でPASS済み。 |

- [tools/no11_frozen_p1_runtime_install.py](tools/no11_frozen_p1_runtime_install.py)：推論用bundleのhash検証・配置と固定160行sampleの照合。
- [tools/no11_frozen_p1_score_replay.py](tools/no11_frozen_p1_score_replay.py)：元base/overlayのhash検証・必要member抽出、全OOF score再生。
- [tools/no11_frozen_p1_first_cross.py](tools/no11_frozen_p1_first_cross.py)：全件replay時にbaseのwatch/gridと再生scoreで、watchごとの最初の閾値crossを照合。
- [windows/Run-No11FrozenP1ScoreReplayReadOnly.ps1](windows/Run-No11FrozenP1ScoreReplayReadOnly.ps1)：上記2経路に共通するユーザーPCのread-only入口。

## 全件replay用の正式artifact

Frozen契約の採用元は `research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003`。P1は5fold×UPSIDE/QUALITY/ADVERSEの**15モデル**。UPSIDEは元モデルの同一byte再利用、QUALITY/ADVERSEはcorrected calendar refitの保存済みモデルを使う。旧baseのQ/Dモデルを選ばない。

| 区分 | ZIP名 | SHA256 |
|---|---|---|
| Base入力 | `Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip` | `c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15` |
| Corrected overlay | `Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip` | `0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7` |

Baseから148 numeric + 15 categoricalの保存入力、category vocabulary、watch/gridを使い、overlayからモデル・前処理・train prediction reference・calibration・corrected OOF・保存first intentsを使う。必要memberは公開manifestのpath/hashで固定し、元ZIP名だけで同一性を判断しない。weight、行単位データ、ユーザーPC内の保存場所は公開しない。

## 全件replay（flagなし）の照合範囲

1. ZIP/memberのhashを照合してから必要artifactを読み込む。corrected lineageに一致する既存preprocessorと15モデルだけを使用する。
2. **標準は全223,940 OOF行**。元NPZの `row_indices` でbase特徴行を選び、各行の保存 `fold` で3headを推論する。外側訓練の保存referenceからmidrank percentileを計算し、`(U_pctile + Q_pctile + 1 - D_pctile) / 3` と保存Q70をcorrected `PRIVATE_INPUTS/oof_P1.npz` に照合する。
3. baseのwatch/gridの因果順に、最初の `score >= Q70` を再現し、corrected `FIRST_INTENTS_PRIVATE.jsonl.gz` の該当P1/Q70意図との一致まで確認する。以後のfill・未来成績・教師値はscore/first-cross判定に使用しない。

NPZの列順はprediction/percentileがUPSIDE・QUALITY・ADVERSE、thresholdがQ70・Q80・Q90・Q95。NPZ内の行位置をbase特徴行番号と取り違えない。元receiptのscikit-learnは1.8.0。元コードの学習用 `run()` や修正fit scriptは起動しない。

| score_replay.pyのオプション | 検証の範囲 |
|---|---|
| 指定なし | 全223,940 OOF scoreの推論一致と、全watchを用いたfirst-cross一致を確認する標準経路。 |
| `--sample-per-fold N` | foldごとに限定行を推論するsmoke。全OOF parityや全watch first-cross一致とは区別して報告する。 |
| `--verify-only` | NumPyのimport・pickle復元を行わず、hash検証と必要member抽出だけを実施。標準ライブラリpickleのimportは行う。モデル推論・score parity・first-crossの合格を意味しない。 |

## 全件再生PASS後も残る範囲

今回確認したのは保存済み過去foldでの元P1推論とfirst-crossの再現。2026日付にどのfoldを適用するかは未決定で、F5や平均への自動dispatchは行わない。2026のVa/Watch/全148+15特徴量と実受信knownAtの接続も別途未完了。Stage 4のprivate価格・State9 GZIP未添付という確認範囲も変わらない。

元Frozen、PR #591、mainは変更しない。追加fit0、実注文OFF、`productionReady=false`、`orderTransmission=false`。この全件再生PASSに、2026のlive First Entry認証・実受信時刻認証・Windows PCでの実行確認は含まれない。
