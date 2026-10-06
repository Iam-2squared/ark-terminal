# 🔒 第一層Sign 有限研究の事前固定

実時計JST 2026-10-06T16:42:54.592123+09:00 / UTC 2026-10-06T07:42:54.592123+00:00。Owner codex-root-sign-prebuy-v2。学習0・新成績閲覧0の時点で固定する。

目的は固定Entry→固定EXIT/EODの費用後符号を予測し、通過群の既知PLUS率80％以上を確認すること。全件見送りで達成扱いにしない。PLUS保持率25％以上、既知通過50件以上、通過8日以上、既知通過割合10〜80％も必要。ZERO／UNKNOWNは正負採点から分離し、通過件数を報告する。

|固定項目|内容|
|---|---|
|対象|固定Fill1600 Entry。判断後の旧Capital execution_eligibleで除外しない|
|入力時刻|最初のBUY_INTENT。判断前の完了足だけ|
|BASE|151数値・15カテゴリ：元P0、凍結State9と履歴、購入前P1 score／閾値／margin|
|BASE_STRUCTURE|191数値・22カテゴリ：判断前Path／構造を追加|
|モデル|Logistic C=.1、HGB depth3／leaves7／100iter。各表現と組合せ4候補|
|閾値|前5日CALのscore quantile .50/.60/.70/.80/.85、linear方式|
|学習|過去FITだけで前処理／fit。各モデルのCALは同一FITモデル、再fit0|
|Discovery|既存時系列B1〜5、4候補×5q。最大20fitで20組を比較|
|候補固定|CAL資格3block以上＋Discovery合否を満たす中でPLUS保持率最大、次にprecision、固定順|
|確認|選んだモデル／qをGitHub保存・actual GET後、B6〜8のみ最大3fit|
|未達時|同じ評価期間に候補やseedを増やさず有限構成を終了。後半を開けない場合も明記|

CAL資格はPLUS率80％、PLUS保持率25％、既知通過20件、通過3日。個々の確認blockでCAL資格が未達でも、固定qのtauを適用し、結果を診断として記録する。後半結果に合わせて見送り規則を追加しない。

31件の次の通常足で約定できなかったfirst-intentはUNKNOWN／未予測・未評価として別記する。固定Fill1600の精度を全1631first-intentの精度と呼ばない。旧1578 populationからの変更と新Entry ID hashは結果前に固定済み。

有効実行計画の上限は23fit（Discovery20＋確認3）。総ledger ceiling33の未使用10枠は自動追加実験に使わない。モデル・特徴・閾値・合否に利益額や資産額を入れず、全て単位重みの符号教師を用いる。

既存Developmentは過去に繰返し閲覧済みでFresh／独立OOSではない。実受信knownAtは不明で、足終了時の可用性を仮定する。原本teacher hash・P1正式監査を再利用し、元EXIT全行・full P1 gridを再実行したとは主張しない。Selector／Entry／EXIT、State／Path定義は完全Freeze。Capital、Stage2、実運用は開始しない。詳細hash・全8日時分割・全パラメータはFINITE_RESEARCH_CONTRACT.jsonを正とする。
