# Selector V2 接続実装の完了範囲

MODE Aを維持する。市場candidate / fit / 較正は0 / 0 / 0。数値案・教師・95列・順位式・品質目標は変更しない。

## 実装した経路

通常の `census / train / calibrate / predict / evaluate / restore-verify` が、独立のhost Authorityを経由して接続される。月次CSV.gzを承認済み日別sliceへ変換し、G0/G1/G2、登録95列、別読みの教師、2推定器、2温度、保存、候補固定、評価、復元へ進む。旧固定人工行列の専用guardは保持する。

`source_adapter.py` のsource profileは、正確なheader、RAW列、単位変換係数、日付、dated identity / 普通株区分、比較可能RAW suffix、null理由、解凍上限をprecommitへ固定する。元ファイルhash / bytes / 利用根拠 / 用途 / 保護 / 日付を最初のpayload open前に照合する。CSVの他日付は文字列として読み飛ばし、その価格・教師は数値化しない。元ordinalを別のprivate slice receiptへ保存する。未知の列名や調整済み価格への自動fallbackはない。

既存J-Quants原本に適用する具体的profileは未採用である。実際のheader / 単位 / dated分類 / corporate-action suffix / knownAtと当時版を承認済み調査で確認してから固定する。完全なdated identity表や比較可能性の根拠が供給されない場合は、最初の原本open前に停止する。元データの存在や保存hashを、この意味契約の確認と同一視しない。

主profileのoptional44列は `SOURCE_NOT_JOINED` を採用した固定経路としてNoneを保持する。実sourceとの44列joinは未検証・未採用であり、別sourceへ実行直前に差し替えない。95列自体を減らさない。

## ownerチャネルと復元の信頼境界

production CLIの入口は固定の `/etc/ark-selector-v2/owner-channel.json`。rootがowner原文・参照・日時・approval / precommit / manifestのpinを設置し、専用の非root workerは読み取るだけとする。親directoryを含むowner / permission / symlinkを検査する。CLI引数・環境変数・request内のtrueからこの設定を作れない。本WorkではこのOS設定も市場grantも設置していない。

生成artifactのpinは、source / outputから独立した0700のhost journalへexclusive保存し、次のprocessで読み直す。出力先のreceipt sidecarだけではpickleを信頼しない。START・candidate予約・各fit / calの開始記録を消さず、同じ工程の再試行・上書きを拒否する。journalを管理する専用workerのOS account自体と、そのcodeをownerが信頼する前提である。同じworker権限やroot自体を侵害した攻撃を防げるとは扱わない。

test-only workerは独立に固定factoryを再生成し、元byte pin・manifest・profile・precommitを照合してから通常CLIへAuthorityを渡す。任意の実rowをsyntheticと呼び替えて通せない。6工程は別PIDで動き、人工モデルの復元予測差0まで確認する。これは市場承認ではない。

## metadataで具体化した日付案

| role | 期間案 | 営業日数 |
|---|---|---:|
| 先行参照 | 2025-04-28〜2025-12-05 | 150 |
| FIT | 2025-12-08〜2026-06-08 | 120 |
| CAL | 2026-06-09〜2026-07-06 | 20 |
| VALIDATION | 2026-07-07〜2026-08-04 | 20 |
| FINAL | 2026-08-05〜2026-10-05 | 40 |

保存済みcalendar原本SHA256 `065b4c4ea902203325969c9855d749e81073737c229b69d1dadebe5f12de2cc5` のDate / HolDivだけをparseした。現物営業日はHolDiv=1/2、OSE祝日取引の3は含めない。根拠は公式 [休日区分](https://jpx-jquants.com/ja/spec/mkt-cal/holiday-division)。calendarは当時の訂正版識別やavailableAtを供給していないため、当時版を完全に再現したとはしない。

`INVENTORY_WINDOW_METADATA.json` に全350日、42元ファイルのidentity / SHA256 / bytes / 保存commit / blobとroleごとの日付対応を結合した。月次object-keyの期間が営業日を覆うという在庫候補であり、当該日の実record存在やV2再利用権を証明しない。市場価格の数値parseは0。

200研究日すべてと先行参照45日が既存protectedHoldoutに重なる。保護日を飛ばしたり古い期間へ自動fallbackしたりしていない。REPORT19とその他sealのexact対応、他研究の人間露出、V2用途別利用根拠も未解決である。これは市場を開始できない具体的な停止理由であり、追加の工学実装を市場計測済みと呼ぶ理由にはならない。

## 次に提示する承認

MODE Bは、上記候補の保護・露出・実record coverage・source契約・利用根拠を解決し、正確なFIT / CAL / HISTORYの用途別allowlistをownerが明示承認した後に限る。fitは0、VALIDATION / FINAL教師は未開封のまま、ゲート供給・FIT clean3/5上限・Risk / R0-Opportunity support・95列観測を調べる。

MODE CはMODE B PASS後の別承認である。全条件・全split・品質目標・source profile・code / config / schema / census / precommit hashと親承認を固定し、1 candidate / 2 fit / 2較正だけを許す。現在の「完了させて」はMODE Aの工学完成を指し、いずれの市場承認も作らない。

本番OS設置、実source profile採用、保護解除、実測性能、live認証は未完了である。承認パッケージに未解決を残すことが今回の停止地点であり、原本の再送は必要ない。
