# No.1.1 RSS 口座観測・注文台帳の接続

## 現在の入口

`Run-No11ReceivedSessionReadOnly.ps1` は実送信を禁止したまま、既存の受信データ処理に口座観測を接続する。`brokerExecutionConfig` を指定した場合も、bootstrap は `DISABLED` または `OBSERVE_ONLY` のみ受け付け、service に `--broker-execution-readonly` を必ず渡す。設定を読み直した後に `LIVE` へ変わっていても、この入口から実送信へ進まない。

既存の Frozen モデル・Selector・Capital V5・EXIT のコードや重みを置き換える設定ではない。モデルの再学習、信用取引、対象市場の追加は含まない。broker 設定がなければ従来の動作を維持する。

検証で使用した約定・注文は synthetic fixture または PowerShell mock。Windows/Excel/RSS の実接続、実口座への発注・取消は実施していない。オフラインテストの成功は実機確認済み・本番利用可能という判定には使わない。

## 1. 補助 workbook をオフライン作成する

repository root をカレントディレクトリにし、既存の private ディレクトリを指定する。以下のパス・日付は例であり、利用中の保存先に合わせる。

```powershell
$no11 = '.\research\no12-prebuy-causal-runtime-20261011'
powershell.exe -NoProfile -File "$no11\windows\New-No11BrokerReadOnlyWorkbook.ps1" `
  -OutputPath 'C:\ArkPrivate\No11\books\Ark_No11_BROKER_READONLY.xlsx'
```

作成スクリプトは Excel を起動しない。既存ファイルは上書きせず、マクロを含まない新しい `.xlsx` を生成する。単一 sheet `ARK_ORDER_IDS_READONLY` の配置は次のとおり。

| セル | 数式・初期値 | 用途 |
| --- | --- | --- |
| A1 | `=RssOrderIDList(A2:F2)` | 実 RSS 発注 ID の 6 列 |
| H1 | `=RssOrderList(H2:AK2,0,1)` | 全状態・全入力経路の現物注文 30 列 |
| AM1 | `=RssExecutionList(AM2:BA2,1)` | 全入力経路の現物約定 15 列 |
| **BD1** | **文字列 `DISABLED`** | 将来の送信 guard セル。`guardCell` |
| **BD2** | **数値 `0`** | 将来の trigger セル。`triggerCell` |
| **BD3** | **文字列 `UNCONFIGURED_RSS_SESSION`** | 将来の session セル。`sessionCell` |
| **BD4** | **空、表示形式 General** | 将来の注文数式／応答セル。`formulaCell` |

BD1・BD3 は数式ではない。BD2 は文字列の `"0"` ではない。BD4 に注文関数を入れず、送信許可を自動設定しない。読み取り対象の 3 表は A:BA に収まり、BD 列とは重ならない。

実接続時には既存の `Ark_No11_MSII_RSS.xlsx`、`Ark_No11_MARKET_RSS.xlsx` と補助 workbook を同じ 1 つの Excel process で開く。collector は既存 book を開く・保存する操作を行わない。補助 book を明示しない場合は従来どおり原本 2 冊のみを認める。明示した場合だけ、元の 2 冊と同じ absolute path の補助 1 冊を認める。補助の sheet、header、3 数式、余剰数式の有無を確認するため、任意の 3 冊を認める変更ではない。

## 2. 送信 OFF の完全な設定例

### Broker 設定: `broker-execution-off.json`

例の `account` は `特定`、対応する `accountType` は `0`。自分の口座区分を確認するまでは `accountTypeVerified: false` を維持する。この未確認の初期値は coordinator の preflight を止める。実際の口座区分と既存の注文条件を確認して設定値を確定する。`allocatedCashJpy: "0"` は未割当の初期値であり、証券口座の余力を勝手に Ark 資金へ割り当てない。

```json
{
  "schemaId": "ARK_NO11_BROKER_EXECUTION_CONFIG_V1",
  "sessionDate": "2026-10-26",
  "evidenceMode": "BROKER_OBSERVATION",
  "ledger": {
    "schemaId": "ARK_NO11_BROKER_EXECUTION_LEDGER_CONFIG_V1",
    "sessionDate": "2026-10-26",
    "account": "特定",
    "allocatedCashJpy": "0",
    "externalSymbols": [],
    "maxSymbols": 3,
    "lotSize": 100,
    "evidenceMode": "BROKER_OBSERVATION",
    "productionReady": false,
    "orderTransmission": false
  },
  "transport": {
    "mode": "DISABLED",
    "orderTransmission": false
  },
  "orderTerms": {
    "orderType": "MARKET",
    "limitPrice": null,
    "timeInForce": "DAY",
    "sor": false,
    "accountType": 0,
    "accountTypeVerified": false
  },
  "originalArrivalTable": "C:\\ArkPrivate\\No11\\inputs\\original-arrival-table.json",
  "accountObservationFile": "C:\\ArkPrivate\\No11\\readonly\\account-source-2026-10-26.json",
  "reserveChargesJpy": "0",
  "productionReady": false,
  "orderTransmission": false
}
```

`originalArrivalTable` は既存原本を指定する。実行コードが確認する SHA-256 は `69f8edafb4708e9a7b61b4f85eb92f353049cf21324e1647602e9973f195f999`。新しく学習・推定した表で代用しない。`externalSymbols` は個人保有など Ark 管理対象外の既知銘柄を入れる欄で、当日の観測から判明した外部保有・外部注文も除外側へ加わる。

### Read-only 起動設定: `readonly-bootstrap.json`

```json
{
  "schemaId": "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1",
  "sessionDate": "2026-10-26",
  "dailyRun": "C:\\ArkPrivate\\No11\\daily-source",
  "datedMaster": "C:\\ArkPrivate\\No11\\inputs\\dated-master.json",
  "runtimeRoot": "C:\\ArkPrivate\\No11\\runtime",
  "h235ModelRoot": "C:\\ArkPrivate\\No11\\h235",
  "privateRoot": "C:\\ArkPrivate\\No11\\readonly",
  "previousContext": "C:\\ArkPrivate\\No11\\inputs\\previous-context.json",
  "brokerExecutionConfig": "C:\\ArkPrivate\\No11\\broker-execution-off.json",
  "orderIdWorkbookPath": "C:\\ArkPrivate\\No11\\books\\Ark_No11_BROKER_READONLY.xlsx",
  "samples": 390,
  "historyBars": 120,
  "warmupSeconds": 20,
  "productionReady": false,
  "orderTransmission": false
}
```

必要なディレクトリ、既存モデル、入力 JSON を用意してから使う。`previousContext` と `previousCaptureFiles` はどちらか一方のみ。broker 観測を接続する場合は `h235ModelRoot` が必須。既存の `shadowAccountConfig` を併用する場合も、broker 台帳とは別の shadow 状態として扱う。

`orderIdWorkbookPath` はこの JSON が基準となる。launcher に `-OrderIdWorkbookPath` を渡す場合は同じ full path に限る。補助 book の指定時には `-AccountWorkbookPath` も必須。環境変数による補助 book の差し替えは行わない。

## 3. Preflight と read-only 起動

事前確認では `-PreflightOnly` を付ける。これは実送信を認める操作ではない。

```powershell
powershell.exe -NoProfile -File "$no11\windows\Run-No11ReceivedSessionReadOnly.ps1" `
  -ConfigFile 'C:\ArkPrivate\No11\readonly-bootstrap.json' `
  -AccountWorkbookPath 'C:\ArkPrivate\No11\books\Ark_No11_MSII_RSS.xlsx' `
  -OrderIdWorkbookPath 'C:\ArkPrivate\No11\books\Ark_No11_BROKER_READONLY.xlsx' `
  -PreflightOnly
```

相場中の観測は同じ引数から `-PreflightOnly` を外して開始する。`brokerExecutionConfig` を `OBSERVE_ONLY` にする場合も top-level と transport の `orderTransmission` は `false` のまま。`LIVE`、`OFFLINE_REPLAY` の設定を read-only bootstrap に渡すと拒否する。

停止後の再開は同じ config と `-ResumeRun '<記録された session run directory>'` を使用する。別の空 run を作って未確定注文や資金予約を消さない。run contract は broker JSON の **bytes** と補助 workbook の **path identity** を保存する。通常の workbook 保存で resume を壊さず、broker 設定の変更や別 workbook への置換を検出する。Excel process の再起動は別途 PID・開始時刻で検出する。

## 観測の意味と境界

| 項目 | 保持・検証するもの |
| --- | --- |
| RSS 発注 ID | ID、関数名、発注日・時刻、注文番号、結果。Excel PID・開始時刻・2 book の path hash から namespace を作る |
| 注文 | 注文番号、口座、売買、現物区分、銘柄、注文・約定数量、状態、受注日時、市場、入力経路 |
| 約定 | 同じ `Range.Value2` の行から日時・数量・単価・市場・取引区分を読む。後から `.Text` を別読みしない |
| 完全性 | header、範囲形状、行の空白途中抜け、重複 ID、重複注文番号、最大行数と末尾の overflow 行を確認 |
| 同じ観測範囲 | 補助 3 表の前後一致、従来 account snapshot の前後一致、現物注文・約定・保有数量・余力の両 book 間一致 |
| 鮮度 | 全体の取得時間は 25 秒未満、正規化時に取得完了から 30 秒以内。未来の日時、時系列逆転を拒否 |
| 重複再読 | 同一 timestamp・同一 source は再適用しない。Excel 再起動を最初に見た snapshot の再読でも hash を変更しない |

補助表は各 5,000 行まで。従来 account snapshot の検証上限（注文・約定は各 298 行、保有は 198 行）も維持するため、両 book 比較に必要な元データが上限を超えれば停止する。切り捨てた表を完全な表として使用しない。

`sameSnapshotVerified: true` は **複数回読んだ値が一致した** という意味で、broker が提供する原子的な snapshot や配信元 timestamp の保証ではない。`actualFeedTimestampCertified` と `buyingPowerFreshnessCertified` は `false` を保持する。余力の新しい表示には MSII タブの更新操作が必要なので、ファイルを新しく読めたことだけで実余力の更新済み判定を作らない。[楽天公式・注文約定](https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_05.html)

約定一覧には注文番号や個別約定 ID がない。約定日時・市場・現物区分・口座・売買・数量・単価を保持しても、複数の注文に配賦できる場合がある。実約定単価は別の attribution 層で一意性を確かめ、曖昧な場合は未確定のまま止める。`発注済み`、取消要求の応答、取消完了、約定完了は別状態として扱う。[楽天公式・取得項目](https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html)

## C50 の一時 book と将来の transport 設定

C50 はチャート取得用の保存しない book を 1 冊作り、`ARK_NO11_CUMULATIVE!G1` に当該起動だけの識別文字列を置く。`collector-ready.json` の `temporaryWorkbook` には次の **実測値** が入る。

```json
{
  "name": "Book1",
  "worksheetNames": ["ARK_NO11_CUMULATIVE", "Q01"],
  "identitySheet": "ARK_NO11_CUMULATIVE",
  "identityCell": "G1",
  "identityValue": "ARK_NO11_C50_TEMP_<この起動のGUID32桁>"
}
```

この例の book 名・sheet 一覧・GUID を固定値として使わない。実際の marker は全 sheet を含み、既存 ready receipt の hash で run に結び付く。transport の `expectedOpenWorkbooks` は保存済み 3 冊の absolute path、`expectedTemporaryWorkbooks` はその marker の descriptor を入れる別枠。transport は一時 book の `Path == ''`、名前、全 sheet 一覧、識別セルが literal で値が一致することを確認し、余分な book を拒否する。

将来、明示された実送信入口を検証するときに必要な値は次のとおり。read-only launcher はこれらを埋めても `LIVE` に昇格しない。

| 設定 | 実機で取得・一致確認する値 |
| --- | --- |
| `sessionDate`, `rssSessionKey`, `expiresAtJst` | 当該 session と観測された Excel namespace、有効期限 |
| `expectedExcelPid`, `expectedExcelStartedAt`, `expectedExcelHwnd` | 1 つの対象 Excel process の PID・開始時刻・window handle |
| `expectedAddInPaths` | 実際の `MarketSpeed2_RSS_32bit.xll` または `64bit.xll` と `MarketSpeed2_RSS_VBA.xlam` の absolute path |
| `expectedOpenWorkbooks` | 元の 2 冊と補助 1 冊の absolute path |
| `expectedTemporaryWorkbooks` | 現在の C50 ready marker の descriptor |
| `workbookPath`, `worksheetName` | 補助 workbook、`ARK_ORDER_IDS_READONLY` |
| `guardCell`, `triggerCell`, `sessionCell`, `formulaCell` | **BD1、BD2、BD3、BD4** |
| `dispatchDirectory` | run の送信記録を保存する private directory |
| `permitMaximumAgeMs`, `responseTimeoutMs` | 既存 transport が検証する上限内の値 |

初期 template の guard は `DISABLED`、trigger は `0`。過去の送信数式が残った BD4 を startup が自動消去したり、未確定送信を自動再送したりしない。

前回の結果や数式が残る場合は、trigger が **数値 0** であることと台帳の確定状況を実機で確認する。read-only C50 は既定の 3 読み取り数式以外を拒否するため、以前の送信セルが残った状態の再起動は確認済みとして扱わない。

## 残る実機確認

実機で残る作業は接続・設定値・実際の挙動の確認であり、この接続のためのコード編集は不要。

| 実施時期 | 確認する事実 |
| --- | --- |
| PC 上の事前確認 | Windows PowerShell 5.1、既存の pinned Python/モデル/Arrival 資産、Excel bitness、RSS add-in path、JST、元の 2 冊と補助の配置。`-OfflineSelfTest` は相場外でも実行可能 |
| 相場中・送信 OFF | 実 RSS の header と `Value2` の型、3 表と元 account snapshot の一致、実際の注文・約定・保有行、取得所要時間、更新停止・Excel 再起動時に停止すること |
| 実余力を使う前 | MSII タブ更新を実際に確認した証拠。観測値・更新時刻・session の一致。更新済みを推定で補わない |
| 実約定を台帳へ反映する前 | 同時注文や同秒・同価格の約定がある場合の一意帰属、取得元の修正・消失、手数料・税の根拠。曖昧な価格や費用は補完しない |
| 将来の明示的な実送信検証 | 1 回だけの送信、受理／拒否／応答不明、部分約定、取消完了、売却約定を実環境で照合。送信 OFF の確認完了から自動では開始しない |

2026-10-25 のこの環境では、broker snapshot の Node 検証と PowerShell 7 の mock/selftest、bootstrap/recovery の Python テストを実行した。Windows PowerShell 5.1 と実 COM/RSS 接続の確認はこの実績に含めない。

仕様照合には [楽天公式 RSS 関数一覧 PDF](https://marketspeed.jp/guide/manual/ms2rss_function.pdf)、[注文約定 help](https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_05.html)、[取得項目 help](https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html) を使用した。RSS ID は Excel 終了でリセットされ、注文・約定一覧は当日分のため、永続台帳の代用にしない。
