# 第一層v3の入力案 — 購入前trajectoryと既知Selector候補の横断context

作成実時計: 2026-10-06 16:49:45 JST / 07:49:45 UTC。状態は**設計案**。fit0、教師符号参照0、Late成績参照0、閾値選択0、原本変更0。v2の未採用を変更する文書でも、v3の実行precommitでもない。

## 結論

次はモデル名を追加するより、購入前の経路情報を渡す構成を有限に比較する。最小案はA「32分の時系列trajectory」と、AへB「その時点までにSelectorが選んだ他銘柄の横断context」を加えた2表現。既存BASEを共通部分とし、Selector／Entry／EXIT、State9／Path、費用、教師を変更しない。

現在のP0は固定窓の要約で、strict窓が成立しない場合は正しくnullになる。current State／historyも現在状態と限られた履歴要約である。Aは観測済み各barの順序・形・値量・不在をそのまま別表現に残す。Bは単一銘柄の経路だけでは識別できない、その時点の既知候補群の共通変化を加える。欠測を修復したと称したり、Stateの意味を再定義したりしない。

## 調査で確認した供給範囲

価格値・教師を採点せず、時計・identity・member metadataだけを確認した。

| 対象 | 確認数 |
|---|---:|
| 凍結Entry | 1600 |
| 対象日 | 58 |
| 対象日のSelector event | 2900 |
| 対象日のSelector unique watch | 2155 |
| その2155 watchの保存RAW接続 | 2155／2155 |
| 各Entry時点で既にSelector選択済みの他銘柄 | 最小4・最大43 |
| 他銘柄poolの累計Entry×peer接続 | 31184 |
| 既知peerのRAW keyがすべて存在するEntry | 1600／1600 |

ここでのpoolは**既知Selector候補群**。市場全体、TOPIX、すべての同時点銘柄を代表するとは言わない。全量4931 watchを無条件に横断集計すると、将来初めてSelectorが選ぶ銘柄も混ざるので、その処理は禁止する。

## A：32分trajectory

**入力境界**は固定first_intent。対象銘柄の同一半場内で、intent直前から過去32個の予定regular minute slotを古い順に並べる。AM不足を前日で埋めず、PM不足を昼休み・AMで埋めない。32は結果を見る前に一つへ固定し、16／64等を追加比較しない。

各slotのRAWは`raw_start+1 <= intent`で確定足のみ。判断時刻と同じraw_startのOHLC／Volume／Valueは含めない。予定slotに行がなければ、各市場値はnull、observed flagは0。半場開始前のslotはnull、session-slot flagは0。架空bar、forward fill、OHLCVから推定したValueは作らない。slotを詰めてgapを消さない。

市場値は6系列、32slot。OHLCは**既存凍結normalizerの80／120両精度で一致したU座標**を使い、最後の確定barの同じC座標を引いて中心化する。元実装のraw float→JSON lexeme→Decimal、previous sourceのP_ref／U、1e-24座標quantizeを保存する。Volume／Valueはそれぞれ`log1p(native value)`。最後のCは既存Entry snapshotのintent直前barと同一identityで照合する。State9のU・profile・窓を変更せず、別のlog％やATRへ黙って切り替えない。M0／価格連続性が成立しない160 EntryではOHLC4系列はnull。Vo／Va・RAW観測flagは独立に保持し、Entryを除外しない。現在のformal StateがINITIALIZINGでも、元normalizerへ入った購入前bar座標を記録できる場合はtrajectoryとして保持する。formal primaryを新たに認定することはしない。

さらに32個のRAW観測flagと32個の同一半場slot flagを付ける。RAW観測flagはStateのcurrent_semantics_observedと区別する。数値は計256列。既存BASE151数値／15カテゴリと合わせて407数値／15カテゴリ。変換のmedian、scale、欠測indicatorは各FITだけで学習し、CAL／TESTから値を決めない。価格値そのもの・銘柄／日付identity・未来Entry／EXITは入力にしない。

opening mixed barについては凍結Stateのauction認定をそのまま使用し、新たにcontinuousと認定しない。trajectoryは正当な過去観測として残し、そのslotのauction statusを別途品質manifestへ残す。初回実装前に「mixed barも市場系列へ含める」を一つに固定する。判断前に初回観測がなければ将来のopening時刻を探さない。

前日依存が強いStateのSOURCE_UNAVAILABLEは既存BASEにそのまま残す。trajectoryでもM0を別方式で埋めない。既存1600のsource-connectedは1440／unavailable160で、これを価格系列の正当な可用性として記録する。価格basisとproviderは元RAWを維持する。前日との価格連続性が不明でも、その状況を隠してStateが正常と認定しない。

## B：同時点の既知Selector候補群context

Aへ横断の16数値を加える。各Entryのpoolは、同じ日の`decisionTimestamp <= first_intent_timestamp`かつ`decisionPriceAvailableAtJst <= first_intent_timestamp`のSelector eventから、symbolをuniqueにした集合。対象自身を除く。現在時刻より後のfirst selection・refresh・当該銘柄のEntry／EXIT結果は参照しない。

同時計のSelector eventを使用できる根拠は、凍結Entry自身が同時計までのselection／refreshを利用する既存順序契約である。ただし実受信時計はUNKNOWN。event-orderが原本と矛盾する場合は同時計eventを後付け認定せず、接続不能として報告する。

各peerの市場値は同じ`raw_start+1 <= target intent` prefixから取得。末尾の確定barがintentから5分以内で、同一半場かつ非auctionの場合だけfresh peerとする。5分はSelectorの既存freshness範囲を使うcontext定義として固定し、緩和しない。peerをpoolから削除せず、known pool数とfresh支持数を別々に残す。

peerの5分・10分returnは凍結P0と同じstrict contiguous close-lag条件で算出。以下の16列へ固定する。

| 列 | 分母／対象 |
|---|---|
| known peer数、fresh peer数、fresh比率、fresh bar age中央値 | unique known pool。age中央値はfresh支持群 |
| 各5分／10分のvalid peer数、valid比率 | known pool数を分母に使用 |
| 各5分／10分の正return peer比率、中央値、25％点、75％点 | valid peer数を分母に使用。ゼロを正へ入れない |

valid支持が0なら該当分布値はnull、valid数0・比率0を残す。Entry自体を見送り母集団へ移す処理ではない。系列の不在を無約定・取得失敗に分類しない。mean／medianへmissingをゼロとして足さない。

A＋Bは423数値／15カテゴリ。これは将来Winner Rankの学習でもCapital接続でもない。score／損益額によるpeer重み付けは行わない。元の全4931 RAW watchのうち、当該intentまでにSelectorで知られていないwatchは市場値まで読まない。

## 共通の教師・分割・有限比較

教師は現行固定Entry→EXIT/EODの既存費用後PLUS／MINUSのみ、1Entry＝1単位。ZERO／UNKNOWNは別枠。既存teacher SHAとmaturityを維持し、金額・Rの大小・Winner強度を教師、重み、選択規則へ混ぜない。

v2で使った時系列8blockとDiscovery／確認用Lateの用途を維持する。FIT前処理・P1 producerの教師成熟・CAL閾値決定・TESTの全境界を引き継ぐ。DevelopmentをFresh／独立OOSへ改名しない。今回の設計調査では教師符号・Late結果を読まない。

最小の新Work候補は4構成だけ：A＋固定Logistic、A＋固定HGB、A＋B＋固定Logistic、A＋B＋固定HGB。model設定、seed、quantile5点、合否、fit ceiling、終了条件はv3開始前に固定する。名前だけの再試行ではなく、Aの192市場値＋64欠測／時計flag、Bの16横断情報が増えることを変更点として説明する。v2保存予測は比較参考に再利用し、baselineを再fitしない。

合否は事前のPLUS通過率80％に加え、PLUS保持率、通過件数・日数、通過率の最低支持条件を維持する。極少数の通過で80％だけを作らない。Discovery全構成が未達なら、Late採点・Capital・新seed追加・window追加へ進まず、そのWorkを未達として閉じる。結果を見てA／Bの定義や主構成を差し替えない。

## 実装前に固定する証拠と残る限界

必要な元データは保存済みのEntry1600 metadata、正規P0／RC2 sidecar、RAW、Selector events、exact previous basis source、固定normalizer／RC2 source・profile、教師のmetadata receipt。価格trajectoryは原kernelへの入力tokenを購入前prefixだけで記録し、新しいState定義や全日後処理から生成しない。新provider取得はこの最小案には不要。正式な開発開始時に、各source／code／schema SHA、first-intent join、slot数、auction扱い、peer支持分母を固定する。切り出しは市場値を読む前に時計で行う。

固定原本：RAW `28a7d3faadda1e677a45cf6c7290bb99e4986c3e026da6746a9f3c04883a9c86`、Selector `1c8fabdd930ee21d55c064d779721f6854e0bb2db9abc5d94c3d991950bb82cb`、Entry `e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb`、v2 input `bf3b77b48c18d218ae9c3d77f5f7c11991359ce6a332de000c950df2c496d52e`。

実受信knownAt、historical日次admissionのPIT、providerの過去訂正version保存は未認定。履歴bar-endの可用仮定を実受信検証と混同しない。既知Selector群の横断contextはこの選択群の研究に限り、市場全体を知っていたとは認定しない。全matrix／EXIT native sourceがこのbundleにない既存監査限界も維持する。

本書は設計案だけ。新fit実行、閾値決定、Late採点、Capital、第2層は未実行。v3の有限契約と入力検算・GitHub actual GET固定が完了するまで実行解禁しない。
