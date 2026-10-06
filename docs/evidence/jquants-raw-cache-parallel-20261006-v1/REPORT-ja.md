# 📦 J-Quants RAW全量キャッシュ — 実行前提確認結果

更新実時計JST: 2026-10-06T13:25:14+09:00

**取得経路の追記**：GitHub Actionsの既存 `JQUANTS_API_KEY` を使うv2 API直接取得・復元方法を、成功run 35447995157（57/57 job成功）で確認した。ブラウザー403はAPI認証失敗の証拠ではない。旧L0/L1等の許可日付コピーを含む約469 MBのA8 reuse archiveも残る。今日のprovider疎通・RAW保存は未実施。詳細は [ACQUISITION_METHOD-ja.md](./ACQUISITION_METHOD-ja.md)。

以下の事前確認は2026-10-06T13:14:21.374173+09:00の実行記録。artifact metadata数値は上記更新時刻で6 runを再照合した。

## 📍 現在地

**CACHE_BLOCKED_AUTH_OR_STORAGE**。専用branchで実行前提確認と取得台帳の準備を実施した。RAW全量取得は開始できていない。本線のIndependent Sign V1は既存の完了・不採用を保持し、再開していない。本線branch・snapshot・Selector／Entry／EXITには書き込んでいない。

## ✅ 実施した確認

- 現行公式仕様・利用権・終了時の扱いを照合。Light候補には初期WorkにないVALUATIONを追記。10 bulk dataset＋直近予定API snapshot＝11候補。実アカウントの権限確認は未完了。
- 現環境の環境変数・既知の認証設定を確認したが、J-Quants APIキーはない。ブラウザーでは利用者が安全な入力画面でGoogleを選択したが、認証遷移先が403 Forbiddenを返した。実契約の確認は未完了。GitHubの既存JQUANTS_API_KEYは、専用jobで存在を確認した。値は出していない。providerによる認証成功・契約確認は未実施。
- DATA_LOCATIONの2台帳、Sign・旧Sign・RNEGのsource binding、旧取得コード、既存source runのartifact metadataを確認。戦略コードはimportせず、本線入力を変更しない。
- 旧コードのlimiterはprocess内だけのため、本Workの共有limiterとは認定しない。全アカウント利用者の接続・固定予算は未成立。
- 11件の合成guard検証がローカル・ActionsでPASS。実ダウンローダのページング／転送障害／lease／CRC等の検証は未実施。

## 📊 実行量

|項目|実績|
|---|---:|
|取得候補dataset|11|
|照合した保存台帳|2|
|現物metadata確認済みartifact|64|
|artifactに記録された圧縮サイズ合計|4,147,979,834 bytes|
|元runの一覧にない旧cache artifact|3|
|今回RAW再利用hash確認|0|
|新規RAW保存／永続readback|0／0|
|provider API requests／署名URL発行|0／0|
|モデルfit／Capital Replay|0／0|
|本線job停止／本線branch書込み|0／0|

64件・4.15 GBはsource runのmetadata上の値であり、このWorkに原本を保存した値ではない。64件中、1件は選択済み派生subsetのexportである。既存ciphertextの復号・現bytes・native field set・source version・公開範囲は未確認であり、RAW_VERIFIEDには数えない。元runの一覧にない3件は旧L0および旧L1 shard0／1で、記録期限が既に経過した。A8 reuse archiveの許可済み日付コピーは残っており、旧原本が全部失われたとは判断しない。

## 🧱 取得を妨げる前提

|前提|状態|必要なもの|
|---|---|---|
|現契約・datasetごとの利用期限|実アカウント未確認|現在の契約状態と終了時刻の証拠|
|API認証|Actionsの既存secretあり・ローカルにはなし|既存secretを使う専用processで認証成功・契約を確認|
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

## ✅ GitHub実行と読み戻し

専用metadata preflight run `37412236265`、job `112103007955` がsuccess。既存secretの存在はtrue、provider呼出し0、RAW転送0。本線のcapital branch HEADは開始時の`a295df739a6810dd0081becd04a3380f6136b6ef`と同じ。既存Realtime job `37408601154`はin_progressを維持。このjobはmain branchの既存運用jobであり、Closed Sign V1を新規稼働させたものではない。

START commit `050b440447b42bcc9a5910424bed941d402f2e81`は29ファイルのactual GET body／Git blob／branch HEADが全件一致。最終checkpointも保存後に読み戻す。

## 🧱 実契約画面の最終確認

利用者のGoogle選択後、認証遷移先で403 Forbiddenを観測した。ログイン完了・現在の契約有効性は確認できていない。別方式へ自動変更せず、契約・期限を推測しない。APIキー値をチャットへ送る必要はない。既存Actions secretはそのまま再利用できる候補として記録した。

続行には、既存の本人専用永続保存先（具体的なpath／bucket、空き容量、閲覧制御と実行processからのアクセス）、現契約と期限の実確認、本線側の共有API予算／limiterとsnapshot reader固定を成立させる。専用branch・再開台帳は保存済みで、研究・取得processが無人で継続しているとは報告しない。
