# 🧭 保存済みJ-Quants由来RAWの復元・購入前入力監査

実時計JST: 2026-10-06T14:26:13.056764+09:00  
実時計UTC: 2026-10-06T05:26:13.056764+00:00  
対象Repo: Iam-2squared/ark-terminal  
公開原本のbasis HEAD: a295df739a6810dd0081becd04a3380f6136b6ef  
RAW exportのbasis HEAD: ad47e8242f340d7519f71bc96d02a0f906055e1c  
実行owner: Codex / frozen_asset_recovery subagent

## ✅ 結論・前回からの差

GitHub Actions run 37091120832の保存済みDevelopment source artifactを復元し、ZIP digest、各member hash、および凍結FIRST ENTRYの原本source_inputsとの一致を確認した。gh run downloadのAzure redirect Forbiddenによる失敗履歴は残し、MCP artifact download経由で復元できたことを別記録として保持する。

新しいprovider取得、教師作成、fit、閾値選択、Capital Replayは0。正式Entry/EXITや元snapshotは変更していない。geometry/canonical/substrateの混合bodyは開封していない。保護commonHoldout244日・excluded243日の市場bodyも0。

## 📊 母集団と集計

保存RAWは4931 watch／133 Development日。正式SESSION_SPLITの58日に絞ると2155 watch／Selector 2900 eventsとなり、正式原本receiptに一致する。全4931 watchのsourceHashが、その日の元minute-wrapper source ledger hashに一致する。

| 指標 | 分子／分母 | 意味 |
|---|---:|---|
| Selector後の観測decision coverage | 223940／377450 = 59.33% | 予定watch-decision rowsに対する実観測。Entry1600の分母ではない |
| strict5分窓成立 | 135826／223940 = 60.65% | 実観測watch-decision endpointにおける窓 |
| strict10分窓成立 | 106296／223940 = 47.47% | 同上 |
| strict20分窓成立 | 81560／223940 = 36.42% | 同上 |
| 累積VWAP coverage80%以上 | 144256／223940 = 64.42% | frozen VWAP成立条件のcoverage部分 |

当日RAW398050足、前日RAW313642足を点検し、無効OHLC/Volume/Value、重複・逆順、日付の取引時刻外の足は0。当日regular source密度は394536／700375 = 56.33%、前日は310455／700375 = 44.33%。これは2155 watchごとの予定足数を合計した分母で、銘柄全市場の取得coverageではない。

正規watch-gridのsupportはFULL218／PARTIAL1929／Selector後観測無し8。予定377450／観測223940／欠測153510とともに、正式PERSISTENT_GRID_RECEIPTへ完全一致する。当日・前日の配列自体は全watchに存在し、前日はterminalのみでregular足がないケースもある。

## 🔍 接続可否と未確定原因

RAW schemaは [raw-start JST分, Open, High, Low, Close, Volume, Value] の7列。公開missingness_reasons.pyへ列変換なしで接続できる。58日から固定規則で116 watchを選び、336 endpoint×6特徴=2016 null guardを独立の時刻presence計算と照合し一致した。この検算は保存特徴量セルの再計算・学習ではない。

判断境界はraw-start+1分の確定足時刻。extractorはraw-start>=cutoffの足のH/L/C/Volume/Valueを読む前に除外する。historical actual arrivalはUNKNOWNで、元のbar-end可用仮定を実受信時刻の認証とは呼ばない。

窓不足、予定観測欠落、昼休み／半日セッション境界、前日同時刻窓不足は説明可能なnull guard。しかし、実際のSign Entry1600のG_PRICE欠測原因は未確定。元Sign snapshot・Entry identity/first-intentとの照合前なので、これを取得失敗・join故障・修復効果と断定しない。

このartifactには正式corrected P1_Q70 FIRST_ENTRY1600、EXIT v3 trade原本、.npy/.npzのP0/P1 matrix、既存State9/Path trace、正確なdecimal source-token basisは含まれない。数値RAWだけから固定decimal State9を再生成して同一traceと扱わない。

## ▶ 次の方針・最小修正案

保存済み26MB Independent Sign bundle、または同等の正式原本群を復元し、正規hashを照合する。正式Entry1600のfirst-intent／identityと元snapshotに、この同一RAWをsidecarとして接続する。元データと原snapshotを保存したまま、購入前prefixと保存セルを照合して、修復可能なjoin／extractorの不整合だけを切り分ける。

RAWの追加partitionが必要な箇所だけ、元wrapper・ページ終端・response hash・可用時点を確認して受け渡す。監査後に有限Sign設計を事前固定し、PLUS/MINUS分類の性能だけで比較する。今回の集計だけで新fitや品質による後付け採用群を開始しない。

## 💾 成果物

- RESTORED_RAW_COVERAGE_AUDIT.json: 原本source hash、母集団、watch-gridとstrict窓集計。
- NULL_GUARD_ADAPTER_AUDIT.json: direct schema接続と2016件の有限独立照合。
- RAW_BAR_DENSITY_SUPPLEMENT.json: 日付別予定calendarに沿う当日／前日の足密度。
- audit_recovered_source.py / audit_null_guard_adapter.py: outcomeを読まない監査コード。

市場価格行はprivate保存先のみ。報告に価格行・教師・API key・署名URLを含めない。
