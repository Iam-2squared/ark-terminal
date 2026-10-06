# 📊 第一層Sign v2：80％未達、候補採用0

実時計JST 2026-10-06T16:56:12.894034+09:00 / UTC 2026-10-06T07:56:12.894034+00:00。Owner codex-root-sign-prebuy-v2。Branch research/sign-prebuy-quality-precision80-20261006-v2。Basis HEAD 9b75882957fa897c5df016ac5ddcb368602ccedc。

原本をprivate repoから復元し、判断前に切った価格・State9・Path・構造入力で有限学習20fitを完了した。通過群PLUS率は38.89〜46.24％。80％には届かず、採用候補0。後半確認はfit0・採点0で閉じた。独立検算19342項目は不一致0。

前回との差は、原本未取得のblocker解消、1600 P0 hash照合、旧fill時点Stateから正規BUY_INTENT再生への接続、欠測原因監査、新モデル20fit、全不採用結果の保存である。性能改善を確認したとは記録しない。

## 🔍 主な実測

対象は2025-06-27〜2025-08-05の25 sessions、固定Fill670 Entry。PLUS295、MINUS361、UNKNOWN14、ZERO0。符号既知656件の全候補PLUS率は295/656＝44.97％。旧Capital execution_eligibleは購入判断後の条件なので主研究の除外gateに使わない。

|項目|分子／分母|率・実行量|
|---|---:|---:|
|全20組中の記述用最大PLUS率（BASE_HGB、q=.70）|86/186|46.24%|
|同組のPLUS保持率|86/295|29.15%|
|同組のMINUS除去率|261/361|72.30%|
|同組の通過後MINUS率|100/186|53.76%|
|同組の通過UNKNOWN|5/191全通過件|2.62％|
|事前固定したCAL資格を満たす候補pair|0/20|採用0|
|新モデルfit／前処理fit|20/20|再fit・retry0|
|後半確認fit／採点|0/0|未実行|

最大率の組は失敗結果を説明するための記述診断であり、採用モデルではない。80％判定は符号既知PLUS/MINUS通過群を分母にする。通過UNKNOWNやZEROをPLUS／MINUSへ置換しない。全first-intent1631件の精度とは呼ばない。次通常足でFillできなかった31件はUNKNOWN／未予測・未評価で別保持する。

## 🧮 分類と購入通過を区別

上記の記述用BASE_HGBについて、符号分類（score>=.5）と通過判定（CAL q=.70）を別々に示す。scoreは未校正。

|実際|予測PLUS|予測MINUS|
|---|---:|---:|
|PLUS|77|218|
|MINUS|105|256|

|実際|通過|見送り|
|---|---:|---:|
|PLUS|86|209|
|MINUS|100|261|

## 📈 全事前固定候補

[実測グラフ](results/DISCOVERY_PLUS_PRECISION.svg)

|入力／モデル|CAL q|通過PLUS/既知通過|PLUS率|PLUS保持|合格CAL block|
|---|---:|---:|---:|---:|---:|
|BASE_LOGISTIC|0.50|124/269|46.10%|42.03%|0/5|
|BASE_LOGISTIC|0.60|98/216|45.37%|33.22%|0/5|
|BASE_LOGISTIC|0.70|78/181|43.09%|26.44%|0/5|
|BASE_LOGISTIC|0.80|49/123|39.84%|16.61%|0/5|
|BASE_LOGISTIC|0.85|42/104|40.38%|14.24%|0/5|
|BASE_HGB|0.50|162/353|45.89%|54.92%|0/5|
|BASE_HGB|0.60|119/274|43.43%|40.34%|0/5|
|BASE_HGB|0.70|86/186|46.24%|29.15%|0/5|
|BASE_HGB|0.80|51/120|42.50%|17.29%|0/5|
|BASE_HGB|0.85|44/99|44.44%|14.92%|0/5|
|BASE_STRUCTURE_LOGISTIC|0.50|127/288|44.10%|43.05%|0/5|
|BASE_STRUCTURE_LOGISTIC|0.60|98/227|43.17%|33.22%|0/5|
|BASE_STRUCTURE_LOGISTIC|0.70|81/181|44.75%|27.46%|0/5|
|BASE_STRUCTURE_LOGISTIC|0.80|59/131|45.04%|20.00%|0/5|
|BASE_STRUCTURE_LOGISTIC|0.85|45/105|42.86%|15.25%|0/5|
|BASE_STRUCTURE_HGB|0.50|154/342|45.03%|52.20%|0/5|
|BASE_STRUCTURE_HGB|0.60|116/272|42.65%|39.32%|0/5|
|BASE_STRUCTURE_HGB|0.70|86/208|41.35%|29.15%|0/5|
|BASE_STRUCTURE_HGB|0.80|49/126|38.89%|16.61%|0/5|
|BASE_STRUCTURE_HGB|0.85|40/101|39.60%|13.56%|0/5|

## 🔒 入力・検算・保存

P0原本hashは1600/1600一致。旧eligible1578のG_PRICE欠測104655/167268セルは全て既存null guardと一致し、欠測をデータ未取得や性能原因と断定しない。同時刻の旧State981 Entry、10551項目で不一致0。原State正規化80/120精度59113価格で一致。全1600を保持し、State unavailable160や未成立状態を欠測・カテゴリとして残した。

前処理はFITだけ、CALには同じFITモデル、教師はcutoff前に成熟した固定EXIT/EOD費用後符号だけ。unit class/sample weights、額・R・最終資産を学習・選定に使わない。予測保存後にDiscoveryを採点した。検算は模型hash・FIT-only前処理・保存予測・CALtau・時系列境界・混同行列を確認。B1CALの新規符号decodeは行わず保存件数の算術を確認した。詳細限界は独立監査に記録した。

privateモデル／入力／予測ZIPは ark-capital-private- の別branchへ保存し、actual GETで全bytes・blob・HEADを検証した。mainは変更しない。RAWや行別市場入力はpublicへ置かない。

## ▶ 次の方針と未完了

80％目標は未完了。このv2構成は事前条件に従って不採用終了し、後から閾値・seed・候補を加えない。次は過去32予定slotの凍結正規化価格経路／出来高・売買代金と、Selectorでその時点に既知の他銘柄contextを別入力として具体化する。準備中は新fit0。

追加の未閲覧期間で固定Entryを評価するには、P1 F5推論用の9原資産（計10968190 bytes）が不足する。正規Freeze ZIPの保存先をユーザーへ確認済みで、原モデルを再fitして代用しない。入手後も既存の後続期間routing規約を確認し、別有限Workの入力・分割・モデル・閾値・予算・停止条件を結果前に固定する。詳細はaudits/FRESH_FIXED_ENTRY_ASSET_READINESS-ja.md。

既存Developmentは閲覧済みでFresh/OOSではない。実受信knownAtは不明で、完了足のbar-end可用性を仮定した研究。native EXIT全行・元P1full-gridを今回再実行したとは記録しない。保護partition・Capital・Stage2・実注文・本番反映は0。

