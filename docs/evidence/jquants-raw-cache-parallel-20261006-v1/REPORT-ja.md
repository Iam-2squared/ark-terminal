# 📦 J-Quants RAW全量キャッシュ — 実行前提確認結果

実時計JST: 2026-10-06T13:06:30.931959+09:00

## 📍 現在地

**CACHE_BLOCKED_AUTH_OR_STORAGE**。専用branchで実行前提確認と取得台帳の準備を実施した。RAW全量取得は開始できていない。本線のIndependent Sign V1は既存の完了・不採用を保持し、再開していない。本線branch・snapshot・Selector／Entry／EXITには書き込んでいない。

## ✅ 実施した確認

- 現行公式仕様・利用権・終了時の扱いを照合。Light候補には初期WorkにないVALUATIONを追記。10 bulk dataset＋直近予定API snapshot＝11候補。実アカウントの権限確認は未完了。
- 現環境の環境変数・既知の認証設定を確認したが、J-Quants APIキーはない。ブラウザーの契約画面はサインイン待ち。GitHubの既存workflowにJQUANTS_API_KEY参照があるが、存在・利用可能性は専用metadata preflightで別確認する。
- DATA_LOCATIONの2台帳、Sign・旧Sign・RNEGのsource binding、旧取得コード、既存source runのartifact metadataを確認。戦略コードはimportせず、本線入力を変更しない。
- 旧コードのlimiterはprocess内だけのため、本Workの共有limiterとは認定しない。全アカウント利用者の接続・固定予算は未成立。
- 11件の合成guard検証がPASS。実ダウンローダのページング／転送障害／lease／CRC等の検証は未実施。

## 📊 実行量

|項目|実績|
|---|---:|
|取得候補dataset|11|
|照合した保存台帳|2|
|現物metadata確認済みartifact|65|
|artifactに記録された圧縮サイズ合計|4,226,884,950 bytes|
|元runから消失した旧cache artifact|2|
|今回RAW再利用hash確認|0|
|新規RAW保存／永続readback|0／0|
|provider API requests／署名URL発行|0／0|
|モデルfit／Capital Replay|0／0|
|本線job停止／本線branch書込み|0／0|

65件・4.23 GBはsource runのmetadata上の値であり、このWorkに原本を保存した値ではない。65件中、1件は選択済み派生subsetのexportである。既存ciphertextの復号・現bytes・native field set・source version・公開範囲は未確認であり、RAW_VERIFIEDには数えない。元runの一覧にない2件は旧L0および旧L1 shard0で、記録期限が既に経過した。他保存先のコピー消失まで断定していない。

## 🧱 取得を妨げる前提

|前提|状態|必要なもの|
|---|---|---|
|現契約・datasetごとの利用期限|実アカウント未確認|現在の契約状態と終了時刻の証拠|
|API認証|ローカルにはなし|既存キーを実取得processで安全に利用できること|
|本人専用の永続保存先|BLOCKED_DURABLE_DESTINATION|既存private disk／bucket、閲覧制御、容量、削除・再読取アクセス|
|本線を含む共有rate limit|未接続|全利用者の共通limiterまたは合意済み固定予算|
|本線のreader allowlist|未確認|hash固定snapshotを新rootから隔離したreaderの証拠|

Work sandboxの空き容量は確認したが、消える作業領域を永続保存先として数えない。Libraryの既存source packも、全RAW用のACL・容量・実行process接続を確認した保存先としては未成立。GitHub public repositoryやpublic artifactへRAWを置かない。

## 📦 dataset別coverage

|dataset|公式の想定範囲|対象object|既存reuse|新保存|不足|今回圧縮bytes|検証|確認済み利用期限|
|---|---|---:|---:|---:|---:|---:|---|---|
|MINUTE|2年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|TICK|2年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|DAILY|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|DATED_MASTER|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|VALUATION|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|FIN_SUMMARY|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|EARNINGS_DATE|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|INVESTOR_TYPES|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|TOPIX|5年・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|CALENDAR|5年（CALENDARは翌年末まで含む）・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|
|EARNINGS_CALENDAR_LATEST|直近snapshotのみ・実権限未確認|未確定|0|0|未確定|0|未実施|未確認|

全dataset・全期間のprovider listingは未取得で、TARGET_LISTING_MANIFESTは未成立を表す空ファイル。対象数・不足数・date/code coverage・field coverage・保存率はnullであり、0件完了／100%保存にはしない。未知の総量・帯域・所要時間は見積もれないためPARTIAL_EXPECTEDの定量判定も未実施。

## ▶ 次方針と期限

現契約、本人専用永続先、共有limiter、reader隔離を実環境で固定してから、全endpointのlistingを保存し、既存完全原本をhashで照合して再利用する。その後Q_SMALL／Q_MINUTE／Q_TICKを同時に公平配分し、hash・CRC・必要な構造検査・永続readback・独立検算まで進める。旧artifactのmetadataと期限は残してある。過去runの再実行、契約変更、追加購入、Capital Replay、モデル学習は行わない。

WorkにあるLight 19:02／分足・Tick 19:07は画像由来の計画値で、実期限へ昇格しない。18:52の設計上の保存確認目標も保持する。期限延長の証拠なしに取得・利用期限を伸ばさない。

公式FAQ上、キャンセル適用後はRAW・複製・復元可能な派生物の利用停止・削除が必要。取得前に保存すれば解約後も使えるとは扱わない。削除対象をまとめるが、大量自動削除は実行していない。元データを復元できないモデル重み等の扱いは同FAQの私的利用条件に従う。

取得processは稼働していない。metadata preflightだけを実際のPID／run IDで報告する。本線のsnapshot採用や新RAWによるState／Entry／EXIT／Rank再計算は0。READY_PARTITION_MANIFESTは新規partitionなし。

公式根拠: [利用目的・ライセンス](https://jpx-jquants.com/ja/help/usage)、[キャンセル](https://jpx-jquants.com/ja/help/plan)、[プラン別データ仕様](https://jpx-jquants.com/ja/spec/data-spec)、[Bulk一覧](https://jpx-jquants.com/ja/spec/bulk-list)、[レート制限](https://jpx-jquants.com/ja/spec/rate-limits)。
