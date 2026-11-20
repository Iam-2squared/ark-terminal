# Phase57 J-Quants Historical / 1m Lineage Audit

調査完了。**日足は前方へ拡張候補あり。同じ1m API経路によるFIT38開始日前への追加は0 sessions。23,665,523行はJ-Quantsから直接取得した1分足（分類A）**。

確認HEAD: afb79b8319480b74b3ae63f6658aa8a7b20f1f6d。PR #587 Open/Draft、未merge。調査成果だけを新directoryへ追加。Dictionary/registry/Selector/Entry/EXIT/Prospectiveコード変更0、新規J-Quants request0、raw archive download/decryption0、REPORT19/Validation/OOS/Fresh payload read0。

## 1. 実日付

| 集合 | 開始 | 終了 | sessions |
|---|---|---|---:|
| FIT38 | 2024-09-17 | 2024-11-12 | 38 |
| QUALIFY19 | 2024-11-13 | 2024-12-09 | 19 |
| Dictionary v0 | 2024-09-17 | 2024-12-09 | 57 |
| REPORT19（metadataのみ） | 2024-12-10 | 2025-01-09 | 19 |

全session dateは02_dictionary_57_session_dates.json。正本は既存Dictionary protocolと監査inventory。REPORT19は今回一切追加開封していない。

## 2. 開始日前に保存済み／過去取得済みのもの

**日足5日分の保存記録あり**: 2024-09-09（warmup専用）、09-10、09-11、09-12、09-13。run34916384636のFORMAL_L0_*_CACHED記録とwhole-cache暗号化処理、再保管run34917676944に接続できる。日付別manifest hashは03に保存。今回rawを再開封していないため、この5日だけの現在の行数・銘柄数・raw file byte hashはUNKNOWN。09-10〜13はRESERVED扱いを維持し、5日全部が直ちにDictionary利用可能とはしない。

**1m4日分は過去取得したが、保存rawは確認できない**。2026-09-10の旧stage2 inventoryには2024-09-10〜13の取得日時、13/14/13/12ページ、normalized rows401,387/457,438/418,676/388,265、fingerprintが残る。ただし全てrawPersisted=false。旧run34464027367の13 metadata artifactsは2026-09-17期限でexpired=true。このfingerprintだけからrawは復元できない。

2026-09-15の保存用L1取得では同じ4日がHTTP400。旧9/10の成功と9/15の失敗は別取得日の記録であり矛盾しない。HTTP400の本文はclientが保存していないため、本文に書かれた具体的な契約境界は不明。現在の2年保管仕様と整合するが、400だけで原因を断定しない。

現在のL0/L1/L2/v2保存artifactはGitHub metadata上expired=false、主な複製のexpiryは2026-10-06。原L0は2026-09-22。exact timestamp/ID/digest/sizeは03/source_receiptsに固定。これはGitHub保管期限で、利用権の延長を意味しない。

探索範囲は現在repo、取得当時commit、旧研究のpinされたmetadata、特定取得run/artifact/log。外部PCのprivate cacheまで不存在を証明したものではない。Actions cache一覧APIはconnector非対応で取得不可。未調査cacheを「存在しない」とはしない。

## 3. 同じ経路で遡れる範囲

repoの2026-09-15スクリーンショット確認記録はLight + TICK_PLUS_OHLCMIN。日足5年、minute addon2年という仕様を公式資料でも再確認した。現在account/credentialへの照会は行っていない。記録上の終了予定はLight2026-10-06 19:02 JST、addon19:07 JST。

| Data type | Current source | Current earliest | Can extend earlier? | Earliest possible | Same schema? | Notes |
|---|---|---|---|---|---|---|
| Daily OHLC | /v2/equities/bars/daily | v0 2024-09-17／保存記録09-09 | 条件付き可 | Light5年の名目境界2021-09-19、暦上初日09-21 | 必須O/H/L/Cは同じ | 全response列の完全同一は保証しない |
| Daily Volume | 同上 | 同上 | 条件付き可 | 同上 | Vo | 過去の上場銘柄集合で取得 |
| Daily Trading Value | 同上 | 同上 | 条件付き可 | 同上 | Va | 価格×出来高の代理生成ではない |
| 1m OHLC | /v2/equities/bars/minute | 保存raw2024-09-17 | 開始日前は不可という仕様 | 現在2年の名目境界2024-09-19 | O/H/L/C | 実API境界は未probe |
| 1m Volume | 同上 | 同上 | 同上・追加0 | 同上 | Vo | raw4日復元源は未確認 |
| 1m Trading Value | 同上 | 同上 | 同上・追加0 | 同上 | Va | addonを上位base planにしても2年枠 |

「全JPX」は東証上場の現物cross-sectionという範囲なら対応。dateのみで銘柄指定せず取得する。地方単独上場・PTS・先物・指数は対象外。上場期間や約定有無による欠落があるため全銘柄×全minuteを保証しない。

公式根拠: [plan別保管期間](https://jpx-jquants.com/en/spec/data-spec)、[minute仕様](https://jpx-jquants.com/en/spec/eq-bars-minute)、[daily仕様](https://jpx-jquants.com/en/spec/eq-bars-daily)。個別契約の実API境界を確認したとの主張ではない。

## 4. 日数・request・容量の見積

2021-09-19の名目下限からFIT直前まで、土日・内閣府祝日・1/2・1/3・12/31を除いた計算は**733 sessions（2021-09-21〜2024-09-13）**。公式provider calendar未取得、特殊休場の独立照合未実施のため見積値。全候補日は09に保存。元資料は[内閣府祝日表](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html)、年末年始休業ルールは[JPX](https://www.jpx.co.jp/corporate/about-jpx/calendar/index.html)。予約・用途適格性を付与した日付一覧ではない。

保存済み日足5日を再利用すると新規daily728日。dated masterは4日保存記録なので追加729日。既存1ページ/日を仮定し、dailyのみ約728 requests、daily+master約1,457 requests。新規daily約320万行、現保存wrapper相当約1.72GB、daily+master約3.90GB。銘柄数・pagination・圧縮率の変動で実数は変わる。これは承認済みrequest budgetではない。

現Lightが継続有効ならこの日足履歴はプラン内の候補で、上位plan購入を前提としない。1m追加は0 requests/0 rows。同経路より古い有料候補は公式案内のDataCubeだが、具体的なproduct・最古日・同schema・価格は未確認、購入なし。

Dictionaryの日足部分は理論候補**57+733=790 sessions**。同じ日足+1mセットは**57 sessionsのまま**。保存5日だけなら日足観測日は62相当だがwarmup/RESERVEDを勝手に評価日へ昇格しない。新registry/適格性審査も今回行わず、実際の追加は0。

## 5. 23,665,523行のlineage

**A: J-Quantsから1m OHLCV/Trading Valueを直接取得**。URLは `https://api.jquants.com/v2/equities/bars/minute?date=YYYY-MM-DD`、続きは同じdateにpagination_key。

| 取得run | Dictionary採用日数 | raw rows | pages |
|---|---:|---:|---:|
| [34926225832 L1](https://github.com/Iam-2squared/ark-terminal/actions/runs/34926225832) | 16 | 6,618,801 | 208 |
| [34964031692 v2](https://github.com/Iam-2squared/ark-terminal/actions/runs/34964031692) | 20 | 7,962,081 | 250 |
| [34936002178 L2](https://github.com/Iam-2squared/ark-terminal/actions/runs/34936002178) | 21 | 9,084,641 | 288 |
| 合計 | 57 | 23,665,523 | 746 |

raw responseText → page SHA → aggregate SHA → minute-pages.json + minute manifest → tar/gzip/encrypted checkpoint → whitelist57 extraction → PIT recovery file hash pins → v0 collect。全57日で取得jobのrow/page数と既存raw監査inventoryが一致。取得当時のコードもrevision/hashで保存。

1行はprovider側で約定を集計した1分bar。Date/Time/Code/O/H/L/C/Vo/Va。TimeはJSTの分開始時刻、取得時刻ではない。Arkはtick requestや日足→synthetic1m生成をしていない。Arkによる集約は**その後の1m→5m**。OHLC集約・Vo/Va合計・cumulativeVWAPを作る。5本揃わない5mは欠測を補完しない。

重要な件数区別:23,665,523はprovider response全行の合計で、3856-code研究universeへ絞る前の数。3856は研究対象union。rawにはETF等の対象外商品も含まれる。全raw行が3856コードだけに属するとの意味ではない。

全date/file/aggregate hash、schema、page数、fetch日時は05/06。現在のrow原本を再開封せず、以前のhash検証済みinventoryと取得logを照合した監査であり、サーバー署名付き証明やhistorical knownAtの証明ではない。

## 6. 他の既存資産

Entry58（2025-10-09〜2026-01-07）、Block C10（2026-06-04〜06-17）、A30（06-18〜07-30）、B8（07-31〜08-12）、old20（08-13〜09-09）は全てFIT38開始後で、Dictionary57との日付重複0。旧研究のallocation/metadataで存在を確認するが、現時点の再利用可能な全銘柄rawはUNKNOWN。件数が一致する別2024 Developmentブロックと同一扱いしない。

REPORT19は現L2保存assetの残19日だが封印維持、拡張見積へ入れない。protected/reservedの重複flagsも維持。詳細10_dataset_overlap_map.json。

## 停止・引継ぎ

研究プログラムを変更せず、12指定Evidenceと補助receipt/hashを保存。検証はmetadataの整合性、57日row/page総和、PIT input hash、schema、日付の非重複、既存ファイル無変更。戦略テスト・回帰・CIの新規実測は対象外。

次の1工程は、日足だけの長期拡張を採用するかを判断し、採用する場合に現在の契約・境界・予約を確認した取得計画を別途固定すること。今回は取得せずSTOP。
