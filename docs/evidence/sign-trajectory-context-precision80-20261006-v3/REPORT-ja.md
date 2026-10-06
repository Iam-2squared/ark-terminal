# 🧪 第一層Sign v3：別入力の準備完了、学習・精度測定0

実時計JST 2026-10-06T17:07:55.679108+09:00 / UTC 2026-10-06T08:07:55.679108+00:00
Owner codex-root-sign-v3-input-preparation / branch research/sign-trajectory-context-precision80-20261006-v3 / basis HEAD 7b59965866f986a375ee431c02c42e35a6bc7b8a

80％目標は未完了。前のv2は20fitで全20組が未達（最大86/186＝46.24％）、候補採用0、後半確認0で不採用終了した。今回のWorkは異なる購入前情報を具体化した入力準備であり、新モデルfit・閾値選択・成績採点は0。

## 🔍 何を変えたか

窓の平均や現在Stateの要約に加え、判断直前32予定slotのOHLC／Volume／Valueの時間順とgapを渡す。価格座標は原State normalizerの80/120一致済みU座標を最後の確定closeで中心化する。State定義は変更しない。さらに、その時点までにSelectorが選んだ他銘柄だけの5/10分return分布と可用性を渡す。将来選ばれる銘柄を母集団へ入れない。

|入力・検算|実測|
|---|---:|
|対象Entry|1600／1600保持|
|元BASEとの同値照合|241600数値＋24000カテゴリ、不一致0|
|TRAJECTORY|407数値・15カテゴリ|
|TRAJECTORY＋既知peer context|423数値・15カテゴリ|
|32slot分母／同一半場eligible／観測|51200／47154／29161|
|価格basis不成立|160 Entry、価格はnull保持|
|凍結80/120正規化照合|22819価格、不一致0|
|既知peer link／fresh link|31184／25013|
|5分／10分strict return支持|10188／8302 link|
|判断後のsource時計|0|
|合成／実prefix＋peer集合不変テスト|8／5ケースPASS|
|市場モデルfit・閾値・精度測定|0／0／0|

slot不在をforward fillしない。半場を越えて埋めない。現在Stateが不成立でも原価格座標が利用できれば別表現として残し、Stateを新しく認定しない。元BASEの購入前P1score lineageを再利用し、行別市場データはprivate archiveだけに保存した。source guardを補強した技術再生成は元feature bytesと完全同値で、追加実験ではない。

## ▶ 次の一手とblocker

追加の未閲覧期間で固定Entryを生成するためのP1 F5推論用9ファイル（計10968190 bytes）が不足している。正規Freeze ZIPの所在をユーザーに確認済み。必要path／hash／サイズは[原資産一覧](audits/FRESH_FIXED_ENTRY_ASSET_READINESS-ja.md)に限定して記録した。既知ZIP／Actions metadataの探索は終了し、毎回再探索しない。

この入力を用いるモデルfamily・期間・教師・候補数・閾値・80％とPLUS保持率／支持条件・fit予算・終了条件を、別の有限研究として結果前に固定する。原モデルを勝手に再fitして代用せず、既存後続期間routingを確認する。既存Developmentを区切り直してFreshと呼ばず、閉じたv2へ候補を追加しない。

既存58日では実受信knownAtが不明で、完了足bar-end可用性の仮定を維持している。今回の時計監査はsource上の時計境界であり実受信証明ではない。Selector／Entry／EXIT/EOD、費用、State/Path定義は完全Freeze。教師は単位重みの費用後符号だけ。Capital・Rank再学習・実運用は0。

## 💾 保存

private repoの別branch research/sign-trajectory-v3-inputs-20261006 に入力・schema・source/code hash・テストをZIP保存し、actual GETで本文bytes・blob・HEADを検証した。private archive SHA5743b60241eb2aec20ba503307602758c8d5cd40d98a8e4e7640ce841d2a1899。本線のRAWsnapshot・private mainは差し替えていない。
