# No.1.1 — 原本rawからFrozen P1/Q70への接続と再生（2026-10-23）

## 目的と現在地

Stage 4の受領JSONは、244銘柄×10時刻=2,440件の価格・State9入力照合について、ファイルSHA256と集計の内部整合を確認済み。価格とCurrent Stateの重複588件、除外2State外525件は銘柄×時刻の件数で、BUYシグナルではない。元private GZIPは未添付のため、その実バイト再hash・行単位の独立再計算は未実施。記録は [Stage 4 receipt](NO11_STAGE4_FULL244_SOURCE_JOIN_OBSERVED_20261023.json) を参照。

正式private base/overlayを取得して保存SHAと照合し、この作業環境で元P1/Q70の学習済み重み・前処理・保存閾値による**全223,940 OOF行の推論とfirst-cross再生がPASS**。追加fitは0、再学習・再校正なし。公開する実測receiptは [NO11_FROZEN_P1_FULL_REPLAY_OBSERVED_20261023.json](NO11_FROZEN_P1_FULL_REPLAY_OBSERVED_20261023.json) で、実行結果のbyte同一コピー（SHA256 `9faa6cb373fab70f3d05705184168f0d3a3fd94326b971b95dc00427f4d422e9`）。receipt内部整合と公開集計のみであることを独立に確認した。

続いてユーザーPCのWindows実行receiptを受領し、**元15モデル・固定160行sampleの推論一致PASS**を確認した。Windows側の結果はsampleによる配置・実行確認で、上記の全件再生とは確認範囲を分けて記録する。

さらに、保存済みの元分足・売買代金・Watchを入力に、**148 numeric + 15 categoricalの再生成 → 元15モデル → Q70 first-cross**を連続実行し、5 Watch・585行で全項目一致した。元rawは既存base ZIP内から取得できたため、追加アップロードやPCでの160行sample再実行は不要。

## 原本rawからの全特徴量・first-cross接続（今回追加）

[NO11_FROZEN_P1_RAW_FEATURE_REPLAY_OBSERVED_20261023.json](NO11_FROZEN_P1_RAW_FEATURE_REPLAY_OBSERVED_20261023.json) は、この作業環境で実行した結果のbyte同一コピー。選定規則は**各保存test foldについて、元WATCH_RECORDS順で最初の行数が正のcanonical Watchを1本**。score・正解intent・収益を見て選定していない。各Watchの一部時刻を抜き出す方法ではなく、対象Watchの全行を処理した。

| 確認項目 | 結果 |
|---|---:|
| hash照合したprivate files | 50 |
| 選定Watch / 全対象行 | 5 / 585 |
| fold別行数 | 2 / 175 / 65 / 173 / 170 |
| 再生成numeric / categorical | 148 / 15 |
| numeric最大絶対誤差 / 値不一致 / NaN位置不一致 | 0 / 0 / 0 |
| categorical不一致 / global辞書にないセル | 0 / 0 |
| original compact / lexeme照合 | 7,974値、不一致0 |
| セッション開始からのRC2 scheduled ticks | 1,626 |
| 実行した元P1モデル | 15 |
| prediction / percentile / score / 4閾値の最大誤差 | すべて0 |
| 4閾値の判定不一致 | 0 |
| first intent / intentなし | 4 / 1 |
| first intentまでの判定 / 固定後の行 | 113 / 472 |
| first-cross比較の不一致 | 全項目0 |
| 新fit / 再校正 | 0 / 0 |

計算経路は、元MANIFEST・FEATURE_FREEZE・4計算コード・RC2の16ファイル・profileをhash固定し、元`state_task`計算ASTをそのまま使用する。`run()`・fit・teacher・dataset writerは読み込まない。前日資料は`previous`・`previous_daily`・`previous_session`だけを渡し、当日入力はdecision cutoffより前に閉じた足へ先に切る。現在の価格に加え、元Pathと状態履歴を保持して全特徴量を組み立てる。

新しい`score_named_batch()`は実際のカテゴリ文字列を受け取り、元global vocabularyのindexへ変換する。未登録文字列は元fold preprocessorの既存UNKNOWN bucketへ入る。RSSをJ-Quantsへ置換したり、欠損・履歴不明・formal nullを同一値へ潰したりしない。既存の整数入力`score_batch()`は範囲外コードを引き続き拒否する。実private固定160行でもnamed/coded/保存期待値の最大差0、4閾値判定不一致0を別途確認した。

保存feature matrixは再生成した値による推論・first-crossの後に比較する。期待OOFと期待first intentsは対象全Watchの決定が終わってから開く。期待値が推論入力やWatchの生成に使われる経路はない。公開receiptには行単位の銘柄・時刻・価格・予測値を含めない。

この追加確認は**5 Watch・585行のraw再生成を含む接続検証**であり、`fullRawFeatureReplay=false`、`fullOofReplay=false`を保持する。全223,940行の保存特徴量からの推論一致は先行する全件receiptの証拠を参照する。元履歴資料のknownAtは`UNKNOWN`、利用可能時刻はbar-end仮定のままで、今回の結果から2026当日の受信時刻やライブ動作を認証しない。

再実行が必要な開発環境では、次の入口を使う。ユーザーPCでの追加操作を要求する手順ではない。

```text
python -B research/no12-prebuy-causal-runtime-20261011/tools/no11_frozen_p1_raw_replay.py --base <original-base.zip> --corrected <corrected-overlay.zip> --private-root <private-cache>
```

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

全件再生の実行環境はPython 3.12.14、NumPy 2.3.5、SciPy 1.17.0、scikit-learn 1.8.0。保存pickleの `_loss.CyHalfSquaredError` はhash一致済みモデルに限り、canonical `sklearn._loss._loss.CyHalfSquaredError` へ厳密に対応させた。

## Windows PCのsample実行結果（受領receipt確認済み）

ユーザーPCから受領した `no11-frozen-p1-score-replay-ed79e1f0933349cf.json` の実SHA256は `ed79e1f0933349cf73d818e41eae173d00e5b597af488443399bb8785cf03612`（4,379 bytes）。公開記録 [NO11_FROZEN_P1_WINDOWS_RUNTIME_OBSERVED_20261023.json](NO11_FROZEN_P1_WINDOWS_RUNTIME_OBSERVED_20261023.json) は受領ファイルのbyte同一コピー。

Windows AMD64、Python 3.12.10、NumPy 2.3.5、SciPy 1.17.0、scikit-learn 1.8.0。receiptは43ファイルの検証、15モデル、各fold32行×5fold=160行の実行を記録し、prediction / percentile / score / 4閾値の最大誤差は全foldで0、Q70と4閾値の判定不一致も0。7件の公開source pin、推論package receipt、bundle、既存全件receiptへのhash参照はすべて固定値と一致した。

`windowsRuntimeObserved=true`、`scoreParityPassed=true`。範囲は `SAMPLED_PC_RUNTIME_ONLY` で、`fullOofReplay=false`、`firstIntentParityPassed=false`、追加fit0を保持する。PCの全223,940行やfirst-crossを再実行したという記録ではなく、全件再現の証拠は先行する作業環境receiptにある。

独立に確認したのは、受領JSONのhash・固定契約との対応・集計の内部整合。Windows実行PASSはそのreceiptに基づく確認で、実PC内のprocess、配置先cache、43privateファイルの実byteをこの環境から直接再検査する作業は未実施。

## 最速のPC配置（RuntimeOnly、今回PASS済み）

今回、ユーザーPCの元推論器配置と固定160行の一致確認は受領receiptで完了した。以下は再配置時の手順として保持する。**約21MBの推論用bundleと一回のscript実行**を使用する。bundleは15モデル、前処理・reference・閾値などの原本41ファイルと、各fold32行×5foldのprivate sampleを収録する。原本41ファイルのbyte一致と160行の元base特徴・OOF位置・期待値の完全一致を別途確認済み。公開仕様は [NO11_FROZEN_P1_INFERENCE_PACKAGE_20261023.json](NO11_FROZEN_P1_INFERENCE_PACKAGE_20261023.json) を参照。

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

`-RuntimeOnly` の合格範囲は**PC推論器の配置と160行sampleの推論一致**で、`fullOofReplay=false` を保持する。全223,940行・2,155 Watchのfirst-cross一致は上記の既存全件receiptを参照し、sample実行による再確認と混同しない。**ユーザーPCのsample PASSは受領receiptで確認済み**。追加fit0、2026日付のfold選択・live特徴量生成・注文は行わない。

## 実行方法と入口

| 実行方法 | 入力と確認範囲 |
|---|---|
| `-RuntimeOnly`（PC配置に推奨） | 推論用bundle一つ。15モデルの配置と固定160行sampleのscore一致。今回Windows受領receiptでPASS確認済み。 |
| flagなし（全件replay） | 元baseとcorrected overlay。全223,940行のscoreと全Watchのfirst-cross一致。既にこの作業環境でPASS済み。 |

- [tools/no11_frozen_p1_runtime_install.py](tools/no11_frozen_p1_runtime_install.py)：推論用bundleのhash検証・配置と固定160行sampleの照合。
- [tools/no11_frozen_p1_score_replay.py](tools/no11_frozen_p1_score_replay.py)：元base/overlayのhash検証・必要member抽出、全OOF score再生。
- [tools/no11_frozen_p1_first_cross.py](tools/no11_frozen_p1_first_cross.py)：全件replay時にbaseのwatch/gridと再生scoreで、watchごとの最初の閾値crossを照合。
- [tools/no11_frozen_p1_feature_runtime.py](tools/no11_frozen_p1_feature_runtime.py)：hash固定した元計算によるraw→148+15と、full State→Path→状態履歴の逐次境界。
- [tools/no11_frozen_p1_raw_replay.py](tools/no11_frozen_p1_raw_replay.py)：保存test foldのWatchを固定選定し、raw→全特徴量→元推論→Q70 first-crossまでを連続照合。
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

今回確認したのは保存済み過去foldでの元P1推論・first-crossと、原本rawからの特徴量再生成を含む接続。2026日付にどのfoldを適用するかは未決定で、F5や平均への自動dispatchは行わない。2026の真正Va・元Selector Watch・日付付きmasterと実受信knownAtをこの計算経路へ接続する部分は未完了。Stage 4のprivate価格・State9 GZIP未添付という確認範囲も変わらない。次の入力契約と残件は [NO11_LIVE_INPUT_CONNECTION_20261023-ja.md](NO11_LIVE_INPUT_CONNECTION_20261023-ja.md) に整理する。

元Frozen、PR #591、mainは変更しない。追加fit0、実注文OFF、`productionReady=false`、`orderTransmission=false`。作業環境での全件再生PASSとWindows PCのsample PASSを確認済み。2026のlive First Entry・実受信時刻・実売買の認証は未完了。
