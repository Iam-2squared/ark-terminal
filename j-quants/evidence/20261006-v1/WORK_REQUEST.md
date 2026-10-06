# 📦 Ark Terminal — J-Quants RAW全量キャッシュ・本線並行Work V1

文書ID: `ARK_JQUANTS_RAW_CACHE_PARALLEL_V1_20261006`  
設計状態: `DESIGN_READY_NOT_EXECUTED`  
設計実時計JST: `2026-10-06T12:42:59+09:00`  
Repository: `Iam-2squared/ark-terminal`  
確認済み本線branch: `capital-main-reallocation-20261005`  
確認済みbasis HEAD: `50804746231fdb8ceade2b2ee40e7cfdc55e84c9`  
保存・実行用branch: `data/jquants-raw-cache-20261006-v1`

## 0. 🎯 依頼と最重要の訂正

**本線のSign研究・入力品質確認を停止させず、別Workで、契約上利用できるJ-Quants原データの保存・重複排除・完全性確認を進める。**

「全部」は、現在契約で利用できるデータセットについて、公開済みの最大取得期間・全対象銘柄・全取得対象ファイル／ページを意味する。J-Quants全プラン・未契約アドオン・過去の全訂正世代を意味しない。保存したものを全件学習に使う承認でもない。

**重要：解約前に取得すれば解約後も使える、という前の案は撤回する。** 公式FAQは、キャンセル／退会後の取得済みデータ利用を不可とし、削除を求めている。プラン変更前の上位プランデータにも利用停止・削除の説明がある。[O1]

したがって本Workは、**有効な利用権に連動した私的利用のRAWキャッシュ**を作る。無期限保管・解約後利用の抜け道を作らない。利用権のないデータを暗号化するだけで保管可能になったとは扱わない。

| 権限 | このWork |
|---|---|
| 現契約で許される取得・本人専用保存・構造検証 | 許可。有効期間と保存先を確認してから実施 |
| 既存キャッシュ・原本・取得コードの再利用 | 許可。元bytesと既存研究の意味を変えない |
| 本線jobの停止・キャンセル・共有入力差替え | 禁止 |
| キャンセル取り消し・契約更新・上位プラン購入・追加課金 | 禁止。ユーザー本人の別判断 |
| 解約適用後の対象データ利用 | 不可。関連利用を止め、削除要求を明示 |
| 既存ファイルの大量自動削除 | この指示書では未承認。対象一覧と削除手順を作り、所有者へ引き渡す |
| モデルfit・正負ラベル再生成・Capital Replay・注文 | この保存Workでは全て0 |

本線継続とは、現在の有効な承認・利用権の範囲で、既存スナップショットを使った仕事を進めること。CLOSEDのIndependent V1を勝手に再開したり、解約後もJ-Quantsデータで研究を続けたりする意味ではない。

## 1. ⏰ 契約画面・終了予定・実行時確認

ユーザー提供画像の表示値（アカウントへの実API確認ではない）：

| 契約 | 画面の月額税込 | 解約予定表示 |
|---|---:|---|
| Light | 1,650円 | 2026-10-06 19:02 |
| Tick + OhlcMin | 5,500円 | 2026-10-06 19:07 |

画像の端末時計7:48を現在時刻として使わない。実行開始時にUTC/JST実時計と契約状態を読み、実際の期限・timezoneを確認する。FAQ上、キャンセルは請求期間末に適用され、それまでは利用可能。ベース終了後のアドオンは自身のキャンセル適用日まで利用できる説明があるため、両者を分離して記録する。[O2]

暫定計画上は早い19:02を共通の警戒期限、18:52を保存確認の目標とする。これは10分の設計上の余裕で、公式の権限終了時刻ではない。アドオンの19:07を無条件に19:02へ書き換えない。反対に5分の差を利用して無許可取得を続けない。

`ENTITLEMENT_AND_RETENTION.json`に各datasetの `active_now / acquisition_allowed_until / use_allowed_until / retention_requires_active_license / renewal_confirmed / evidence` を保存。キャンセル継続中でも現在有効なら、現契約内のキャッシュ作業は進めてよい。契約を継続しない場合の「保存完了」は解約後の使用許可を意味しない。

実行開始時に期限超過、401/403、契約終了が判明した対象は新規取得・利用を止める。他人のキー・別アカウント・Freeへの切替で対象権限を回避しない。契約継続の証拠が更新された場合だけ、そのdatasetの期限を更新する。

## 2. 📚 設計時に確認した公式仕様

以下は2026-10-06に確認した公開仕様。実行時の公式差分と実際の契約権限を最終照合する。古いV1や法人向けProの仕様を混ぜない。

| 項目 | 確認内容 |
|---|---|
| API | V2。APIキー認証。旧V1は2026-06-01終了との現行案内 [O3] |
| Light | 銘柄一覧・日足・財務情報・決算発表予定日・投資部門別・TOPIXは原則5年前まで。カレンダーは翌年末〜5年前。API専用の3/9月期決算予定は直近のみ [O4] |
| 分足 | 過去2年、APIとCSV。1分OHLC・出来高・売買代金。無約定の1分は行を返さない [O5] |
| ティック | 過去2年、**CSVのみ**。`/equities/trades`を普通の行取得APIとして呼ばない [O6] |
| Bulk | `GET /v2/bulk/list` → `GET /v2/bulk/get` → 署名付きURLからgzip本体 [O7][O8] |
| 署名URL | 有効期限5分、期限内にダウンロード完了。URLだけ集めても保存完了ではない [O8] |
| API頻度 | Light基本60 req/min。分足・ティックの専用APIは独立60 req/min。財務summary等にはendpoint制限もある [O9] |
| CSVの差 | CSVは調整済み株価を提供しない。日足APIの調整済み列とは同一ではない [O10][O11] |
| 当日分 | 分足・ティック・日足・TOPIXは16:30頃更新。日中リアルタイム配信と扱わない [O12] |

**無約定行の不在、短い観測窓、State未成立、特徴の適用外と、RAWの取得失敗は別。** 既報のG_PRICE欠測62.57%を「J-Quantsの原データが62.57%失われた」と読み替えない。保存を増やせばSign性能が改善するという保証は置かない。

## 3. 🔄 二つのWorkを隔離する

| 項目 | 本線 | 保存Work |
|---|---|---|
| 役割 | 既承認範囲のSign・入力品質確認 | 原本収集・キャッシュ・整合性・coverage |
| 入力 | hash固定済みの旧snapshot | 別rootの新RAW cache |
| 書込み | 本線自身の範囲 | 専用branch・専用directory・専用job |
| 新データの受渡し | 検証済みmanifestを明示採用してから | 完了したpartitionだけ公開。自動接続0 |
| API | 本線が承認済み取得を行う場合だけ | 同一アカウントの共有limiter経由 |

専用worktree／process／出力rootを使う。原本の再取得版で既存ファイルを上書きしない。研究の途中でglobが新データを拾わないよう、**本線には明示的なsnapshot IDとファイルallowlist**を渡す。

保存Workのconcurrency groupは本線とは別、`cancel-in-progress=false`。本線を止めてrunner枠を空けない。共有CPU・RAM・diskに圧迫が出たら、保存側の展開・検証workerを減らす。本線の保存途中ファイルを読まない。

RAW取得の完了を本線全体の待ち条件にしない。ただし新RAWが必要な工程だけは、そのpartitionの検証完了を待つ。進行中の本線へ「保存中のファイル」を渡すことは最速化ではない。

## 4. 🗂️ 既存保存物を先に再利用する

最初に `REUSE_INVENTORY.jsonl` を作る。全履歴を何度も検索するのではなく、既存manifestから必要な参照だけ辿る。

開始時の確認対象：

- 現行 `docs/evidence/independent-entry-exit-sign-20261006-v1/` のsource／dataset記録とprivate再現パック。V1は完了・不採用を保持。
- 旧Sign-only／RNEGのSOURCE_BINDING・原ZIP・runtime依存。そこにある「抽出済み候補行」は全市場RAWと同一ではない。
- Project／Libraryの `DATA_LOCATION_INDEX_UPDATED(1).csv`。保存済みActions artifact ID・hash・expiry・暗号化状態がある。**METADATA_ONLYを保存実体ありと数えない。**
- 旧DictionaryのDaily／Minute取得manifest、ローカルcache、本人管理ストレージ、既存取得script・workflow。
- 9月の引継ぎには57session／746pages／23,665,523分足行やDaily733sessionの記録があるが、現在の全量保存を証明する値ではない。対象範囲・期限・現bytesを照合して使う。[P1][P2]

各itemを `RAW_VERIFIED / NORMALIZED_ONLY / FILTERED_SUBSET_ONLY / METADATA_ONLY / ENCRYPTED_ACCESS_UNVERIFIED / EXPIRED_OR_MISSING / HASH_MISMATCH` に分ける。銘柄単位の抽出cache、5分集約、正負teacherを1分RAWの代用にしない。

旧artifactは期限切れ前の本人専用保存先への移送を優先。生データが公開artifactになる場合は使わない。既存の暗号鍵をログやチャットへ出さず、正常な復号可否と利用権を確認する。過去runを再実行するより、同じartifact bytesの再取得を優先する。

同一dataset・期間・取得条件・field set・source versionの完全なbytesをhashで確認できればprovider再取得を省略する。名前・行数・日付が同じだけでは同等性を認定しない。providerが訂正した新versionは別objectとして保存し、旧versionを最新に見せない。

## 5. 📦 取得対象レジストリと「全量」の分母

最初に公式仕様とアカウント権限から `DATASET_REGISTRY.json` を固定する。以下9種類が画面のLight＋Tick/OhlcMinに対応する初期リスト。別アドオンが画面に見えるだけでは契約中としない。

| dataset | bulk endpoint値 | 基本経路 |
|---|---|---|
| MINUTE | `/equities/bars/minute` | 全権限範囲CSV。穴のみ日付指定API |
| TICK | `/equities/trades` | 全権限範囲CSVのみ |
| DAILY | `/equities/bars/daily` | CSV＋CSVにないAPI列の必要補足 |
| DATED_MASTER | `/equities/master` | CSV／必要日付API |
| FIN_SUMMARY | `/fins/summary` | CSV／最新未収録分API |
| EARNINGS_DATE | `/fins/earnings-date` | CSV／最新未収録分API |
| INVESTOR_TYPES | `/equities/investor-types` | CSV／最新未収録分API |
| TOPIX | `/indices/bars/daily/topix` | CSV／最新未収録分API |
| CALENDAR | `/markets/calendar` | endpoint指定で最新1ファイル、必要ならAPI |

加えてAPI専用の `/v2/equities/earnings-calendar` は、仕様どおり直近snapshotだけ保存する。過去5年の全予定履歴をこのendpointから復元できると扱わない。[O4][O7]

Premium／Standard専用データ、TDnet、EDINET等を勝手に購入しない。開始時の公式・契約照合で新たに現契約内と判明したdatasetは、根拠付きregistry追記を行い取得対象にできる。未契約なら `NOT_ENTITLED` で分母外として別表にする。

`/bulk/list?endpoint=...` を使い、権限範囲内のKey・Size・LastModifiedを全件保存。日付だけの一括listingではカレンダーが返らないので別取得する。実レスポンスがpagingを持つなら全ページを追い、持たない仕様なら架空のpageを作らない。[O7][O13]

分母は (A) 開始listingで固定した全ファイル／期間、(B) 開始後に公開・訂正された差分を別管理。画面の5年／2年だけから厳密な最古日を捏造しない。実際のearliest/latestと不足区間を出す。現在上場銘柄だけを起点にせず、日付時点の銘柄・上場廃止等も原本範囲で残す。

## 6. ⚡ 取得順序：小さい基礎データも確保し、分足・ティックを並行

取得前に、保存先容量・各fileのSize・残り時間・実測帯域から見積もる。時間不足でも対象を黙って縮めない。

**初動**：契約／保存先／元cacheを照合し、全datasetのlistingとカレンダーを確保する。全過去cacheの精査が終わるまで、新規であることが明らかなpartitionの取得を待たせない。

**並列キュー**：

1. Q_SMALL：カレンダー、dated master、日足、財務、決算予定、投資部門別、TOPIX。小さいmetadata・基礎ファイルを早期に確保する。
2. Q_MINUTE：過去2年の取得可能な全市場1分足。既存研究範囲とその前日依存の不足partitionを先行、その後は未取得の古い側から。
3. Q_TICK：過去2年の取得可能な全市場ティック。MINUTEと同時に開始し、巨大tickが他の全queueを占拠しない。

MINUTEを全件取り切るまでTICKを開始しない、という直列化は禁止。どのqueueも飢餓状態にしない。結果PLUS／MINUSや利益を見て取得順を選ばない。

サイズ・通信量が期限を超える場合は `PARTIAL_EXPECTED` と不足見込みを直ちに記録する。契約を勝手に継続せず、取得可能な原本を順次保存。すべて終わらなくても、既完了object・再開cursor・残taskを失わない。

16:30頃の当日分公開後、実際のlisting／API更新を確認して追加する。財務は18:00頃速報・24:30頃確報の案内があるため、今夜の期限後にしか出ない確報を未取得エラーやゼロ件成功にしない。[O12]

## 7. 🌐 ダウンロード実装契約

既存取得コードが正確に対応していればreuse。不足分だけ専用moduleへ追加する。上流戦略codeをimportしない。

### Bulk優先

`bulk/list → object選定 → workerに空きができた時だけbulk/get → 直ちに署名URLからstream → hash／検査 → commit`。

署名URLは5分以内の取得完了が必要なので先行大量発行しない。API keyは `api.jquants.com` 宛ての正規headerにのみ渡し、署名URL先のstorage hostへ転送しない。HTTPSとproviderが発行したhostを検証し、redirectで認証headerを漏らさない。URL全文をログ・GitHub・manifestへ出さない。[O8]

巨大fileをmemoryへ全展開しない。元 `.csv.gz` bytesを保存する。転送時のgzip content-encodingとファイル自体のgzipを混同しない。`Content-Length`、listing Size、ETag、LastModifiedは保存するが、ETagをSHA256とみなさない。

### APIで補う部分

分足／日足は日付指定の全銘柄取得を基本とし、全日付×全銘柄の無駄な総当たりを避ける。`pagination_key`がなくなるまで同じqueryを継続。空dataでも次tokenがあるなら完了にしない。token反復・同ページ再受信を検出する。[O5][O9][O11]

API JSONは元bodyをそのまま圧縮保存し、編集・丸め・列削除をしない。schema revisionを保持。CSVだけでは提供されない調整済み日足は、既存API原本をreuseし、未保存field群を日付APIで補足する。調整前CSVしかない状態を「APIの全列まで保存済み」としない。[O10][O11]

**Tickの行取得APIや日付指定JSON fallbackは作らない。** CSVが取れないならそのobjectをBLOCKEDとして残す。[O6]

### 共有rate limit

1アカウント／1制限domainで1つの共有limiterを使う。workerごとに上限を与えない。公式60 req/minに対する初期運用上限は54 req/min（設計上の余裕）。domain未確定なら全取得を一つの54 req/minにまとめる。本線の承認済みAPI利用も含める。

独立アドオン枠は公式の適用endpointと実行環境を確認したときだけ分離。`bulk/list/get`を根拠なく別枠にしない。複数キーで制限回避しない。共通limiterに接続できない場合は本線利用者と固定予算を合意し、全体が上限以下と証明できるまで並列APIを増やさない。[O9]

転送workerは初期2、上限4。CPU検査workerは初期1。これは研究用の実装設定で、API公式推奨値ではない。I/O測定に基づく増減のみ許可し、主研究のjobをkillしない。

### 障害処理

429はRetry-Afterがあれば従う。なければ指数backoff＋jitter。連続429／アクセス遮断なら制限domain全体を少なくとも5分cooldownし、直ちに叩き続けない。[O9]

5xx／通信障害は各taskで初回＋最大3回retry。全URL再発行も同じattempt台帳に数える。署名URL期限切れは契約が有効な間だけ再取得。401/403は認証・権限・storage署名失効を分け、認証確認はboundedにする。権限終了後のリトライは禁止。

Range再開は正式な対応と同一object versionを確認できた場合だけ。未確認なら新しい有効URLでそのfileを先頭から取り直し、壊れた.partialを完成品と連結しない。API cursorが無効になった場合も当該queryだけを再走行し、旧pagesを保持して別attemptにする。

## 8. 💾 保存先・原本不変性・再開

RAWはユーザー本人の利用権と閲覧制御を満たす保存先に限定。public GitHub、公開release、公開CI artifact、第三者向けアプリserverへ置かない。privateという名前だけで閲覧制限があると判断しない。[O1]

新しい有料ストレージを契約しない。本人管理の既存永続disk／承認済みストレージが見つからなければ `BLOCKED_DURABLE_DESTINATION` とし、必要な保存先を明示する。消える可能性のあるWork sandboxだけを永続保存成功に数えない。

次は論理構成例。実パスは `STORAGE_BINDING.json` で解決し、存在しないパスを既存保存先として報告しない。

```text
PRIVATE_CACHE_ROOT/
  objects/sha256/<hash>.csv.gz | .json.gz
  manifests/<snapshot_id>.jsonl
  state/task-ledger.sqlite
  receipts/downloads.jsonl
  quarantine/
  sealed/<partition>/
```

原本はsource versionごとのimmutable object。ただし**immutableは利用権終了時の削除義務に優先しない**。解約後も消せないObject Lock／永久WORMを設定しない。

object単位で `.partial → bytes/hash/format検査 → atomic rename → 永続保存先の再読取検証 → ledger VERIFIED`。永続側への転送前に元を削除しない。disk不足なら新transferを控え、保存済みを失わない。

各task IDはdataset＋Key／query＋source version。DBのunique制約／leaseで二重取得を防ぐ。クラッシュから再開してVERIFIEDを飛ばし、IN_PROGRESSだけをlease回収する。保存先が複数ある場合はコピー先も利用権台帳と削除対象台帳に入れる。

source原取得日時と今回の再取得日時、データDate、公開時刻、LastModifiedを別にする。今取得した過去データへ昔の `knownAt` を作らない。現在の調整済み株価を過去に既知だったPIT値と認定しない。

## 9. 🔐 未閲覧・Holdoutを保存と分析で分離

過去のExposure／Common Holdout／REPORT／Validation／OOS用途を変更しない。[P2]

全量取得は、未閲覧期間についても**custodianによる不透明bytesの保存と構造検査**まで。価格チャート、統計分布、銘柄選別、State実行、Entry/EXIT、正負labelを作らない。研究プロセスからsealed rootを読めないようにする。

transport/hash確認、schema/行数/日付/code coverage確認、内容閲覧、outcome生成を別counterにする。元契約が価格bodyの機械処理自体を開封に数えるなら、その厳しい定義を維持し、当該partitionはbytes/hashまでとする。保管しただけでFreshとして新認定しない。

今回のダウンロード担当が将来価格本文を閲覧した場合は、その事実をExposureへ記録し、未見へ戻さない。sealedに送ったという名前だけでは独立性の証明にならない。

## 10. 🔍 完全性とcoverage：取得欠落を約定不在と混同しない

検査は二段階に分け、巨大データの解析でダウンロードを止めない。

**A. transfer検査（即時）**：HTTP成功、Key／version／size、stream完了、SHA256、gzip CRC、JSON／CSV構造、永久先readback。CSVの全展開が重い場合はstreamする。hashだけの完了とschemaまでの完了を別statusにする。

**B. coverage検査（取得と並行／後続）**：dataset×date×code×取得file／pageの範囲と整合を確認。契約外・未公開・非営業日・無取引・未取得・page途中・schema異常を別reasonにする。行数0により「休場」「無約定」を断定しない。

分足の無約定分はprovider仕様上行がない。完整なday取得とlisting／daily等の整合根拠なしに、任意の欠落minuteをNO_TRADEへ変換しない。既存特徴のwarmup不足・applicability-nullも原データ欠損とは別。

tickは同一時刻・価格・数量でも別約定の場合がある。適切なprovider ID／系列定義がないまま、その組だけで重複削除しない。RAW行はすべて保存し、二重ページ除去は取得台帳側で扱う。

日足調整前と分足を照合する場合、対象市場・通常取引／auction・時刻・企業行動・丸め・provider定義が一致する範囲だけ。差があれば記録し、どちらかを補完・修正して一致させない。

7/11・7/14のような既存未解決日も、今回のRAWがあったというだけで旧欠落理由を確定しない。新cacheの有無と旧取得／抽出経路の証拠を分離して、本線に受渡す。

## 11. 📏 完了の定義・権利期限

| status | 意味 |
|---|---|
| `CACHE_COMPLETE_ACTIVE_LICENSE` | 固定した全取得対象が現権限内で保存・必要検証済み。全native fieldの不足0。利用権は現在有効 |
| `RAW_OBJECTS_COMPLETE_FIELD_GAPS` | bulk等の予定objectは揃ったがAPI専用field／最新差分等が不足 |
| `CACHE_PARTIAL` | 未取得・未検証・未永続化が残る。件数・bytes・期間を提示 |
| `CACHE_BLOCKED_AUTH_OR_STORAGE` | 認証・権限・正当な保存先が未成立 |
| `LICENSE_ENDED_USE_STOPPED` | 利用権終了。取得・関連データ利用停止、provider削除要求への対応が必要 |
| `RETENTION_ACTION_REQUIRED` | 残るコピー／バックアップ／加工データの処理を所有者が確認する必要がある |

**有限のキャッシュ完了と無期限の保持権は別。** `retention_after_cancellation=NOT_PERMITTED_PER_FAQ` を常に出す。契約継続なら、期限の再確認とキャッシュ継続が可能。終了なら該当RAWおよびコピー等の削除対象を明示し、ユーザー承認済み手続きで削除・証跡化する。キーや元研究を巻き込む無差別削除は禁止。

モデルや派生物の権利が不明な場合、「生RAWではないから利用可能」と判断しない。対象と不明点を権利確認リストへ残す。保存済みの非データコード・設計文書・安全なhash台帳は、削除対象データと区別する。

継続取得をこのチャットが無人で実行しているように報告しない。実際に起動・owner／PID／job IDを確認できた処理だけRUNNINGとする。この依頼時点の成果物は指示書であり、データ保存の実績ではない。

## 12. 🧪 最小テストと独立検算

市場outcomeを使わず次を合成fixtureで確認する。

- ページ複数／空ページ＋次token／tokenループ／HTTP200 error body／同page retry。
- gzip切断／CRC不一致／partial rename前停止／移送後hash不一致／disk不足。
- 署名URL期限切れ／署名URLへのAPI key非送信／ログのsecret redaction。
- 複数worker・別Workの共有rate limit／lease競合／本線job非cancel。
- 解約適用後のfetch/read拒否／更新証拠なしの期限延長拒否。
- snapshot固定readerが新partial・新versionを勝手に読まない。

独立検算は主manifest集計をそのまま信じず、固定listingと検証済みobject台帳から、対象総数・取得済み・再利用・不足・bytesを再計算する。raw SHA256は新規全object、既存reuseは信頼済み証跡と現bytesを照合。巨大fileの未完了検証はpendingを明示し、0件にしない。

## 13. 📊 最終報告に必須の表

| dataset | 契約内範囲 | 対象object | 既存reuse | 新保存 | 不足 | 圧縮bytes | 検証 | 利用期限 |
|---|---|---:|---:|---:|---:|---:|---|---|

併せて、provider requests・signed URL発行・転送bytes・実測速度・429・retry・圧縮／検証待ち・永続readback数を出す。listing対象objectの保存率と、実際のdate/code coverage、API field coverageを別表示する。

完了報告は「どこへ、何を、何bytes保存したか」「残りは何か」「解約後利用不可」「本線へ何を渡してよいか」で読める形にする。G_PRICEの欠測解消率やSign改善率はこのWorkでは測定しない。

## 14. 💾 GitHub保存・本線への引継ぎ

public GitHubにはコード・設計・集計・hash・coverage・期限管理だけを保存し、RAW／行別価格／API key／署名URL／復号鍵は保存しない。既存repoに混在が見つかっても本Workで再公開しない。

専用branchと `docs/evidence/jquants-raw-cache-parallel-20261006-v1/` を使う。本線branchには小さな並行Work pointerだけをappend-only追加してよい。本線CURRENT_STATEや既存REPORTを更新しない。force push・main merge・他writer上書き0。

START、契約／保存先固定、listing／reuse確定、主要dataset完了、最終のcheckpointで、実時計JST、basis HEAD、owner、現在地、完了、未実行、blocker、数値、次方針を保存。各commit後にactual GETで本文／blob／HEAD確認。毎fileごとのGit commitは不要。

必須成果物：
`WORK_REQUEST.md / DESIGN_CONFIG.json / OFFICIAL_SPEC_SOURCES.json / ENTITLEMENT_AND_RETENTION.json / STORAGE_BINDING.json / PARALLEL_WORK_CONTRACT.json / DATASET_REGISTRY.json / REUSE_INVENTORY.jsonl / TARGET_LISTING_MANIFEST.jsonl / TASK_LEDGER / DOWNLOAD_RECEIPTS / COVERAGE_REPORT / FIELD_COVERAGE / EXPOSURE_TRANSFER_LOG / INDEPENDENT_STORAGE_AUDIT / CURRENT_STATE.json / REPORT-ja.md / DELIVERY_RECEIPT.json`。

本線への引継ぎは `READY_PARTITION_MANIFEST.json` と旧新version差分・合法利用範囲・as-of限界だけ。新RAWでSelector／Entry／EXIT／State／既存Rankを再計算しない。元のラベル・分割・Gateはそのまま。

## 15. 📎 根拠と未確認事項

公式資料は `OFFICIAL_SPEC_SOURCES.json` にURL・確認日・採用内容を記録する。実行時に差分があればversionを追記し、既存記録を上書きしない。

[O1] J-Quants Help「利用目的・ライセンス」：私的利用、第三者開示、解約・退会・プラン変更後の扱い。  
[O2] Help「プラン・変更・キャンセルと退会」：請求期間末まで利用可、ベース／アドオンの終了。  
[O3] API Reference「J-Quants APIについて」／Quickstart：V2・キー認証。  
[O4] 「契約ごとに利用可能なAPIとデータ格納期間」。  
[O5] 「株価分足(/equities/bars/minute)」。  
[O6] 「株価ティック(/equities/trades)」。  
[O7] 「ダウンロード可能ファイル一覧(/bulk/list)」。  
[O8] 「ファイルダウンロード用URL取得(/bulk/get)」。  
[O9] 「レートリミットについて」。  
[O10] 「ファイルダウンロード」。  
[O11] 「株価四本値(/equities/bars/daily)」。  
[O12] 「提供データの更新タイミング」。  
[O13] 「指定可能なエンドポイント一覧」。  
[P1] Project「Dictionary → Chart-aware Entry/EXIT 今後方針保存版」2026-09-19および9/20引継ぎ：旧cacheの存在と所在探索の手掛かりのみ。現在の契約範囲や全量保存を証明しない。  
[P2] `DATA_LOCATION_INDEX_UPDATED(1).csv` と旧Exposure台帳：管理記録と現bytesを区別する。古い戦略再設計指示は本Workへ継承しない。

未確認：実行環境のAPIキー有無・実アカウント権限・更新予定変更、現在の全cache実体／容量／永続保存先、取得総量／所要時間、全量完了の可否。本書ではこれらを確認済みにしない。

## ▶ Workへの開始指示

**本線は停止せず、このJ-Quants RAWキャッシュWorkを別branch・別processで開始してください。** まず利用権・現契約・永続保存先と既存cacheを確認し、取得可能な全dataset／全期間のlistingを固定してください。Bulk CSVを優先し、分足・ティック・Light基礎データを飢餓なく並行取得、既存完全原本は再利用してください。共有rate limit、期限、再開台帳、hash、coverage、永続readbackまでまとめて完了してください。

解約後も使うための退避とは扱わず、キャンセル取り消し・追加課金・公開RAW保存・契約終了後利用は行わないでください。Selector／Entry／EXIT・本線snapshotは変更せず、学習／ReplayはこのWorkでは0。全量未達なら不足を隠さず保存し、現状・方針・実時計をGitHubへ残して読み戻してください。

END_OF_WORK_REQUEST
