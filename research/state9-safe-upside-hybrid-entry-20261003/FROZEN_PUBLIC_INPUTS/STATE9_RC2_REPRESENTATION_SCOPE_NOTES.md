# 🏷️ Representation scope裁定

裁定: **EXPLANATORY_SCOPE_SUFFICIENT_NO_SEMANTIC_REVISION**。固定意味の説明で閉じ、名称から通常語の余分な含意を持ち込まない。名称の自然さが検証完了したという裁定ではない。

| ラベル/表示 | 固定された現在意味 | 含めない意味 | 説明で閉じるか |
|---|---|---|---|
| SHARP_RISE / SHARP_DROP | local方向に沿う6実連続Close（5区間）のnet≥5U、TV>0、効率≥0.8。RISE/DROP側の写像でfast=true | 絶対severity、異常性、滑らかな単調増減、未来持続性、M0/U尺度の最適性 | Yes。有限窓・normalized Uのfast条件として表示。PULLBACK/REBOUND/Stop/Rangeをfastで上書きしない |
| RISE_STOP / DROP_STOP | local UP/DOWNで進捗clockと固定3OHLC等のStop条件を満たす | 天井/底、反転確定、取引所halt、長期trendの終結、安全性 | Yes。「局所進捗停止」。認定足count=1とprogress_atを分離する |
| REBOUND / PULLBACK | LIVE local UP/context DOWN、LIVE local DOWN/context UPという現在関係 | 持続性、回復保証、健全な押し、浅さ/深さ、安全性、売買適格性 | Yes。local/contextの関係名として示す。Stop優先、基準破壊を別途明示 |
| RANGE | Frozen A/B/C/Dと共通guardで成立した固定帯。確認Close退出が未成立 | 単なる見た目の横ばい、Closeが常に物理[L,H]内、ヒゲ順序の往復 | Yes。物理帯と±0.5U確認退出帯を分ける。C017の物理High外buffer内のCloseも矛盾ではない |
| RISE / DROP | 他activity/反対context/fast写像に該当しないLIVEの保持local脚 | FULL全体のbull/bear trend、最新1分の必ず同方向の値動き、breakout成功、未来継続 | Yes。local脚とcontext、direction_basisを表示する。Range後context NONEも許す |
| null / carried / initializing | current_semantics_observed=false。表示履歴・初期アンカー・品質/初期化状態は観測済み9Stateではない | 第10State、現在も同じ市場意味を観測したとの主張 | Yes。正式Primary/nullと履歴表示Primaryを分離し、basis/observed_atを併記する |

名称だけの単独表示を承認しない。Primary、activity、basis、current_semantics_observed、observed_atは一体で扱う。context/local/direction_basis、fast窓、Rangeの物理帯と確認帯、Stopの認定時刻/countを必要に応じて近傍表示する。これは今後の表示に求めるscopeで、UI実装済みという意味ではない。

## 旧10本帯guardの懸念の裁定

RC2のS01/S03は窓の長さ・共通抑止を明記するが、旧帯確認幅の式をそこで全文再掲していない。これだけを新しい境界選択の許可にしない。

既存RC1原本 `Ark_State9_Semantic_Contract_v2_RC1_20260930(1).txt` §8.2は、直前10本の旧High/Low帯をCloseが **δ_break以上** 突き抜けると抑止、と明記する。同原本の固定profile δ_break=0.5Uを維持する。凍結済みRC2 candidate/api.pyおよびindependent/api.pyは、旧帯High+0.5以上／Low−0.5以下の同じ境界を実装し、source snapshotへのhash照合も一致した。kernelのRange成立判定も同じ固定profileを用いる。

よって、物理Highをわずかに超えただけで抑止する新規strict-physical-boundary規則を採らない。これは市場結果後の式の追加・閾値変更ではなく、既存原本の参照不足を出典で閉じたもの。C017の旧帯Highと等しいCloseはどちらの読みにも帯内なので、同caseの一致だけでguard全境界が検証済みとはしない。全境界の新規テストは0。

未解決Primary境界矛盾: **0（保存Evidenceと固定文書の今回検査範囲）**。不明な広域trend目的や市場性能への適合性は評価していない。
