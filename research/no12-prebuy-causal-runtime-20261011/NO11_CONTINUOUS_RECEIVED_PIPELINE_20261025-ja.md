# No.1.1：RSS観測の常駐取り込み → 定時Selector → State9/P1 → H235

作業日：2026-10-25 JST。対象はPR #592の既存作業ブランチのみ。元Frozenのモデル・特徴量数式・PAVA/ML・Capital V5・EXIT原本と別モデルブランチ、main、元Excel・発注許可は変更しない。

## 今回の到達点

`tools/no11_received_pipeline_tick.mjs` と `tools/no11_received_pipeline_service.py` を追加した。既存 `Probe-No11Chart50ContinuousReadOnly.ps1` が**継続保存している**private snapshotフォルダーを監視し、新しい受信分を代替Va付き確定足に変換する。元の10時刻Selectorを実行し、保存済み受信列を既存State9/P1/H235経路へ自動供給する。

これは**収集済みデータを手動でモデルへ渡す操作を常駐consumerで置き換える**実装。Excel収集プロセス自体の自動起動、当日銘柄マスタ・前日基準の自動作成、実口座・EXIT・発注管理までは追加していない。実RSS接続・私有モデルの連続実行・処理速度はCIでは確認できない。

## Selectorの時計を修正

`runtime/no11_frozen_selector_native_shadow.mjs` の外側入力契約を修正した。

- 元の判断時刻と、実際に受信・処理できた時刻を分離する。10:00までに閉じた足を10:00:15に処理できるが、10:01に閉じた足は10:00判断には使わない。
- ミリ秒付きJST受信時刻をそのまま扱う。受信時刻を過去の足締切に書き換えない。
- 既定は従来の厳格な同時刻入力のまま。遅延処理は `evaluatedAtJst` を指定した時だけで、上限は暫定の90秒。これは元モデルの閾値ではなく実装上のShadow上限であり、実機遅延の合格を意味しない。
- 初回のWatch再選定回数を0→1へ修正。同じ時刻の再実行は再選定回数を増やさない。

重み・15特徴量計算・Top5・10時刻は元実装を再利用する。RSS由来の代替Vaと絞り込んだ候補集合により、元の全市場戦略との経済的一致は引き続き保証しない。

## 常駐の実行・再起動

Node側は前回と今回の2つのsnapshotから**新しく確定した区間だけ**を既存Va importerへ通す。既に使った足・Vaを変更・消去・過去へ追加する入力は拒否する。全ての過去snapshotを毎分取り込み直す方式にはしない。

Selectorの実行結果・実受信時刻・Watch・実行済み時刻・採用済み分足をprivate checkpointへ保存する。判断時刻から90秒を過ぎた起動では、その時刻は `MISSED_NOT_BACKFILLED` とし、後から選出した結果を過去へ遡らせない。処理終了が期限を超えた場合もWatchを発行しない。

同じ観測対象を一日維持し、その中で選ばれたWatchを監視枠に固定する。今回は銘柄を動的に入れ替える機能は追加していない。保有・既存Watch・未約定の予約が必要な場合は、既存のprivate pins付きChart50計画が前提。

Python側はモデルを起動時に一度読み込み、単一プロセスロックで重複起動を防ぐ。State9は安全な受信prefix再生を使っており、**毎回のState9計算まで完全な増分化を実装したわけではない**。約47銘柄・終日の実処理時間を実機で確認する必要がある。

`ProcessingTimedP1` は、モデルを実行する時刻を実時計で保存する。入力の受信時刻はそのまま保持する。再起動後、すでに完了したP1評価は元の処理時刻のまま再利用する。一方、停止中に古くなってまだ評価していない足からは新しいEntryを作らない。モデル実行前に落ちた未完了記録も、古くなった後に再評価しない。

H235の原本24モデル照合・Block08の明示的Shadow指定は前回の実装を使用する。Capital V5の実口座配分・注文はこの常駐consumerに接続していない。

## 必要な実入力

1. 当営業日のChart50 private export receiptと、前営業日の日足から生成したG1 PASS mask。
2. 当日のマスタ受領記録：`schemaId=ARK_NO11_DATED_MASTER_RECEIPT_V1`, `sessionDate`, 実際にその情報を確認した `knownAtJst`, `rows`, `productionReady=false`, `orderTransmission=false`。rowsは既存Selectorの `symbol/asOfSession/rawPreviousClose/segment/sector/corporateActionsCleared/priceBasisVerified/commonEquity`。ETF等を通常株として偽装せず、不明なフラグを通過用にtrueへしない。
3. 既存 `ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1` 前日基準JSON。前日分足と価格基準を確認できない銘柄は既存経路で除外する。
4. 検証済み元P1 F5 runtime、および任意で元H2/H3/H5の24モデルroot。
5. 実際に新しい `snapshot-<sha256>.json` が追加される収集フォルダーと、リポジトリ外のprivate保存ディレクトリ。

手入力で値・受信時刻・確認フラグを捏造して用意するものではない。情報が不足している場合は接続未完了と扱う。

## 起動例

以下は必要ファイルが実際に存在し、別途既存read-only collectorが稼働しているユーザーPC用。ChatGPT側でユーザーPCのプロセスを起動したという意味ではない。

```powershell
python -B research/no12-prebuy-causal-runtime-20261011/tools/no11_received_pipeline_service.py `
  --session 2026-10-26 `
  --capture-folder "<既存collectorの今回のsnapshotフォルダー>" `
  --plan "<今回のno11-chart50-private JSON>" `
  --mask "<今回のno11-observed-pass-watch JSON>" `
  --dated-master "<実確認済み当日master receipt JSON>" `
  --previous-context "<実確認済み前日context JSON>" `
  --runtime-root "<検証済みP1 runtime root>" `
  --h235-model-root "<元24モデルroot>" `
  --private-root "<今回用のprivate保存ディレクトリ>"
```

`--preflight-only` はモデルと前日入力の読み込み確認のみで、場中入力の検証・本番合格ではない。`--once` は一回だけ取り込む診断。既定では2秒間隔で新ファイルを確認し、変化があった時だけ処理する。受信停止120秒、実時計・価格基準・checkpoint変更などでは終了する。15:26以降はconsumerを終了する。consumer停止は別プロセスのcollectorを終了しない。

保存先は `pipeline-current.json`、ハッシュ名のtick記録、private SQLite、`pipeline-latest-report.json`、既存H235 private batch。stdoutは集計件数と状態のみ。元モデル・銘柄別価格・口座情報をGitHubへ送らない。

## テストと限界

追加テストは、元Ridgeを使った10時刻/Top5・再選定・遅延/未来足拒否・再起動・時刻超過、P1実処理時計、single-service lock、checkpoint破損、実State9/Pathから元H235計算までの接続を検査する。H235係数とRSS観測はテスト用合成データである。

**CI成功 = 実機成功ではない。** 実RSSの終日供給、非公開P1/H235の実データ連続推論、前日基準/当日masterの自動供給、速度、保有・EXIT・口座照合・部分約定・取消・復旧・実発注は未確認または未接続。`productionReady=false`, `orderTransmission=false`。
