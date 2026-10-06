# 🔎 第一層Sign：購入前入力の監査完了、学習前

実時計JST: 2026-10-06T16:39:05.708346+09:00 / UTC: 2026-10-06T07:39:05.708346+00:00

原本をprivate repoから復元し、固定Entryの判断時刻までのState／Path再生を完了した。新しい市場学習・閾値選択・80％判定はまだ実行していない。

|監査|結果|
|---|---:|
|引継ぎZIP内のprivateファイルhash|520/520一致|
|元P0のEntry単位hash|1600/1600一致|
|旧eligible群G_PRICE欠測セル|104655/167268、全て既存null guardと一致|
|同じ判断時刻の旧State照合|981 Entry、10551セル、不一致0|
|凍結正規化80/120精度照合|59113価格、不一致0|
|判断時刻より後の新State step|0|
|新モデルfit|0|

旧compact Stateには判断後の値がある597/1578件が含まれるため、凍結kernelを購入前まで再生した。欠測は元の窓・gap・昼休み条件で説明でき、データ取得失敗や修復効果とは断定しない。欠測を消すための上流変更は行わない。

次は価格・出来高・State9・履歴と既存P1購入前scoreを使うBASE、および判断前Path／構造情報を加えた表現を比較する。候補・時系列分割・閾値quantile・PLUS保持率・通過件数・終了条件をGitHubへ固定してから有限学習を行う。通過群PLUS率80％以上を主条件とする。

判断後のCapital購入条件を混ぜないため、主研究は固定Fill1600 Entryとし、旧execution_eligible1578は診断だけに残す。判断後に約定できなかった31 first-intentはUNKNOWN／未評価として別記する。

既存58日Developmentは過去に閲覧済み。Fresh/OOSとは呼ばない。歴史データの実受信knownAtは不明で、完了足のbar-end可用性を仮定する研究である。固定EXIT教師とP1 producerの原本hash・正式監査を再利用し、native EXIT全再生や元P1 full-gridの再実行を完了扱いしない。Selector／Entry／EXIT変更、Capital Replay、Stage2学習、実注文は0。
