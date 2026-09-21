# 5-Minute State — 機械判定契約 v1

状態: **FROZEN_CANDIDATE / SYNTHETIC_TESTED / HUMAN_REVIEW_REQUIRED**
作業開始: 2026-09-21 16:04 JST。終了時刻は同ディレクトリのREPORT-ja.mdとCURRENT/WORK_LOGに記録する。
開始HEAD: `907f1016cd46dd784b2a7269aa10945e75e12543`。

## 0. 今回固定するものと限界

前回の`STATE_DEFINITION_v0.1.md`の意味・4時間軸・時刻契約を受けて、未固定だった機械判定を**単一v1候補**へ落とした。旧5+1ラベルもWork試作10bps/30bpsも使わない。実データの分類数、Entry損益、UNKNOWN率を一切見ずに固定した設計値であり、唯一の正解・最適な値ではない。

人間確認を受けるまでは正式採用・実市場正解表生成へ進まない。実データadapter、既存データのPIT admission検証、UI、注文・売買判断は本参照実装に含まない。検証対象は仕様を具体化した純粋関数であり、実市場のCausal Recognition成績を測定していない。

## 1. 表現と情報の時刻

- Directionは最新5予定取引分の終値対先頭始値の符号。UP / DOWN / UNCHANGED。「10bps未満だから横ばい」の閾値は使わない。大きさも数値で残す。
- StructureはUP / DOWN / RANGE、各scope・anchor付き。識別不足はnull＋理由で、RANGEへ強制しない。
- PhaseはPROGRESSION / CORRECTION / RECOVERY / BALANCE / RESTRUCTURINGの根拠付き集合。
- Breakout/Reclaimは水準ID付き価格イベント。CHOPは他のStateを消さない重複属性。
- 出力はTで初回、それ以降T+5k active minutes。内部で1m価格を走査しても最終Stateを毎分発行する設計ではない。
- `State(t)`はtで終わった過去5分と、tの構造。t以後の次5分や終日ラベルは別物。

## 2. スケールSを先に固定

**S = 実際の前営業日に完全観測した、非重複5分ブロックのTrue Range中央値（共通価格単位）**。

前営業日各continuous-sessionの予定stampを先頭から5個ずつ区切る。全5本が有効なブロックだけで算出。TRはmax(H-L, |H-直前block C|, |L-直前block C|)。直前blockが欠測、または昼休み・session切替なら、そのblockはH-Lのみとしgap価格をTRへ混ぜない。ブロック選択は予定時刻固定で、存在する5本を集め直さない。

最低6完全ブロック（30予定分分の観測）を必要とする。0 rangeも中央値に含める。6未満はSCALE_INSUFFICIENT、中央値0はSCALE_ZERO。日足ATR・別営業日・未来today rangeによるfallbackはしない。

Sはその銘柄の当日内で固定。価格が一律k倍ならSもk倍となる。同じSで前日終点の構造も再構成するが、これは**今日から見た前日context**であり、昨日の当時もこのSを知っていたとは主張しない。

根拠: 最新5分に対応する単位を過去のみから得る、銘柄固有の価格変動幅に比例させる、1〜2ブロックだけで基準を作らない、という設計目的。6ブロックで統計的に十分と実証したわけではない。疎い前日ではState項目の欠測が増える可能性を留保する。

## 3. Swing：終値の1S反転

1m終値列を使ったdirectional-changeとして固定する。OHLC内のHigh→Low順序を推測するpivot方式にはしない。高安値・wickは別descriptor/eventで捨てずに残す。

- 初期方向なし：running lowから終値が1S以上上がればLOWを確認。running highから1S以上下がればHIGHを確認。
- 上向き脚：終値最高点から1S以上下げた足でHIGH確定。下向き脚へ。
- 下向き脚：終値最低点から1S以上上げた足でLOW確定。上向き脚へ。
- 極値同値のtieは最初の時刻。境界1Sちょうどは成立。0.999Sは不成立。
- pivotの発生時刻effectiveAtと確認時刻confirmedAtを必ず別にする。確定pivotは書き換えない。
- 分足欠測・昼休み等の非連続区間をまたいで反転を数えない。

終値pivotはザラバ中の極値そのものではない。これを価格の本当の全Swingを捉える万能器と呼ばない。

## 4. Structureと失効

同一scale・連続segmentの直近交互4pivotにHigh2個・Low2個を求める。

| 条件 | 判定 | 保護水準 |
|---|---|---|
| H2>H1かつL2>L1 | UP_STRUCTURE | L2 |
| H2<H1かつL2<L1 | DOWN_STRUCTURE | H2 |
| それ以外 | 新規trend確定なし | 既存structureの失効判定は別に継続 |

高値だけ更新、または最新5分UPだけではUP_STRUCTUREにしない。高安同値はstrictな更新ではない。

UPは終値が保護Lowを**下回った**時点、DOWNは保護Highを**上回った**時点で失効。同値touchでは失効しない。新しく成立した同方向4pivotで保護水準を更新する。一度失効した同じpivot組合せから旧structureを再発行しない。

失効後、新structure未成立ならRESTRUCTURING。前日下降と当日上昇は別scopeで併存可能。同一scopeの上下を無理に同時確定しない。

## 5. Range：肯定的な条件で認める

最新30連続有効1mを6個の5分blockへ分け、全条件を要求する。

1. envelope幅が0より大きく2S以下。
2. 終値path効率が1/3以下。終値完全不変で分母0の場合は効率をnull保持し、この条件だけは通過可能。ただしOHLC幅0のflatlineはRangeにしない。
3. 上端から0.25S内への接触を2個以上の異なる5分blockで観測。
4. 下端から0.25S内への接触も2個以上の異なるblockで観測。

候補を見つけた時刻に上下境界を固定する。終値が外側へ出たらRANGE_CLOSE_EXIT。次の値動きを取り込んで境界を都合よく拡げない。

local Rangeは有効なUP/DOWN構造に重なってよい。その場合は上位trendを消さずlocalRange別列で残す。trendがなく有効RangeのみならRANGE_STRUCTURE＋BALANCE。Range退出だけでUP/DOWN構造成立とはしない。

検出は連続segmentの観測開始から5本ごとの内部境界で行う。欠測後は新segmentで再起算するが、Opportunityの5取引分評価gridは動かさない。tがその境界でない場合、新Rangeを突然作らず直近までのactive Rangeを使う。

設計値の意味: 30分=6評価周期、1/3効率=総移動のうち純進行が小さい、複数block接触=一度のwickだけを均衡と呼ばない。これらは事前設計の定義であって市場で最良と選んだ値ではない。

## 6. PhaseとRecovery episode

構造的な現在脚は、最後に確認したLOWからその価格より上にいるならUP、HIGHから下にいるならDOWN。pivot価格そのものにいる場合は脚方向未確定。最新5分方向はこの脚と違ってもよい。

- 有効UPのUP脚／有効DOWNのDOWN脚はPROGRESSION。ただしUPで回復episode途中ならRECOVERYを優先表記し、単純な継続へ潰さない。
- 有効UPのDOWN脚はCORRECTION（押し）。有効DOWNのUP脚はCORRECTION（反発）。
- 新しい隣接HIGH→LOWの確定close-pivot組を下降episode H→Lとし、固有IDを与える。
- 上向き脚でL<C<HならRECOVERY。回復率=(C-L)/(H-L)を保存。
- C>=HならRECOVERY_COMPLETE。C<LならRECOVERY_INVALIDATED。判定後のepisodeを毎回最安値で採り直さない。
- 回復完了は当該下落分の回収だけで、UP_STRUCTURE確定ではない。
- DOWN_STRUCTURE内の反発かつ下落episode回復ならCORRECTION＋RECOVERYを併記。
- Range内均衡ならBALANCE。構造失効後ならRESTRUCTURING。局面が定義できなくてもDirection等の事実は残す。

今の押しが将来失敗しても「元から押しではなかった」と成功例だけに遡及改変しない。逆に、反転幅がまだ1Sに達していない小さな逆行を、構造的な新しい脚と決めつけない。

## 7. CHOP・拡大・活動量

最新5本内の**隣接終値差**の非ゼロ符号反転を使う。差は4個なので反転最大3回。始値→最初の終値を反転数へ混ぜない。

CHOPPINESSタグは、反転2回以上、効率<=1/3、OHLC envelope>=0.5Sの全てを満たす場合。方向や構造、Recoveryタグは削除しない。

直前5分とのenvelope比、出来高比、売買代金比は1.5以上をEXPANSION、2/3以下をCOMPRESSION。それ以外はタグなし。比率は全て残す。前窓欠測・境界跨ぎ・分母0はnull。レンジ拡大を注文フローの証明とは呼ばない。

これらは1つの明示された定義候補。二値タグなしでも連続descriptorは保持される。

## 8. Breakout / Reclaim / VWAP

前日official Daily高安終値、前日observed分足高安、当日対象窓以前の高安、localRange上下限、structuralSwing水準を区別する。対象窓より前に水準を固定し、ID・source scopeを保存する。

素crossは `previousClose <= level < currentClose`（上）、`previousClose >= level > currentClose`（下）。固定bps bufferは設けない。ノイズを除いた重要crossを検証済みという意味ではない。

同一連続segment内で以前にその側の終値が存在した後の再crossならRECLAIMも付ける。ギャップをまたぐcrossや過去不明のreclaimは作らない。High/Lowだけが水準を越えたらWICK、close crossとは別。同一足で上下を跨ぐ順序は不明のまま。

cross後の最初の2予定closeがその側を維持したかを別確認タグとする。足不在は失敗でなく観測不足、引け打切りはRIGHT_CENSORED、昼休み跨ぎはSESSION_BOUNDARY。

VWAPはsum(value)/sum(volume)。集計対象・単位の一致が前提。完全観測prefixのみで動的VWAPの前/後値に対するcrossを作り、`movingReference=true`を保存する。部分観測値はobservedVWAPとして表示できるが完全VWAPとしてcross判定しない。Close×Volume補完なし。

参照実装は汎用`level_events`で全静的水準型を扱え、`assemble`には前日official/observedとtoday-priorの配線を備える。Swing/Range水準を次工程adapterで渡す場合もsetAtとscopeを必須にする。旧6 Signalのtrigger評価は行っていない。

## 9. Four-scopeの配線

- Dailyは正確なD-5..D-1、全lag個別status、OHLC/Vo/Va、高安比較、5日方向・幅を保持。D-6必須化なし。逆方向の日足を加点/減点で当日の状態に上書きしない。
- 前日observed全1m、前日終点のstructure・pivot、最後の30予定分の方向（欠測ならPARTIAL）、observed高安/VWAP、coverageを保持。翌日のためのcontextであり、昨日の当時の予測ではない。
- Today Open→tのstructure・events・観測高安/VWAPとLatest5のdirection/descriptorを別に保持。
- security、実際の前営業日、price basisが一致しなければcross-day比較やSを使わない。Daily action未検証も同様。最新5分単独の価格記述まで全部破棄しない。

runtimeのprovider変換とknownAt証明は次工程のInput Admission責任。本コードへ値を渡しただけでclean PIT証明完了とはならない。

## 10. Missing・recess・引け

calendarのregular bar-end列を外部から明示注入する。コードに現在の取引時刻や祝日をハードコードしない。
T+0を保持し、後続5予定取引分ごとのendへ進む。足がない分も予定取引分として数え、待って5本揃った時刻へずらさない。5分未満の最後のtailは別に保存し、完全5分を偽造しない。

昼休みを取引分に数えず、欠測と区別。micro指標とpivotは連続segmentでreset。既知の休憩では前場のstructure水準をcontextとして保持し、再開後終値で失効を確認する。予定足欠測を跨ぐ場合は現structureを確定値として継承しない。

bar-end=currentが無ければCURRENT_BAR_UNAVAILABLE。新Stateを古いStateでfillしない。前日不足・意味未識別・同一足順序不明は別理由。UNKNOWNの名称変更だけで認識率が向上したと呼ばない。

## 11. Future reference contract

**未来確認期限=同日内の次10 active minutes（2評価周期）**の1案で固定。旧30分Gateの継承でも、最適horizonの実測選択でもない。

`reference_at`はt+10までの同一session観測でpivotを確認し、effectiveAt<=tのpivotだけをtの構造へ戻して利用。futureの価格そのものやt後発生pivotを「現在の値動き」として混ぜない。prefix観測値、oracle解釈、future確認情報を分離する。

close-pivotの順序は一意だが、OHLC内の順序は別問題で不明を保持。欠測/休憩跨ぎのpivotを作らない。t+10以後のsuffixを変えてもlabelは変わらない。因果側snapshotはtより未来のbarを拒否し、未来suffixに依存しない。

終端で10分揃わなければfuture窓のみRIGHT_CENSORED。それでもtの最新5分Directionや確定済み構造・crossを消さない。future窓完全観測と意味の唯一正解性も別。`WINDOW_OBSERVED`は全State正解保証ではない。

10分で確認されない長い転換は限界として残す。適用後に未知が多くてもhorizonやSを結果に合わせて変更しない。

## 12. 数値選択の一覧

|項目|v1候補|
|---|---|
|更新周期/最新窓|5 active minutes / closed 1m×5|
|S最低標本|前日完全5分block×6|
|Swing反転|1S、終値、以上で成立|
|構造比較|直近4交互pivot、HH/HLまたはLH/LL|
|Range|30連続1m、幅<=2S、効率<=1/3、各端2block接触、帯0.25S|
|CHOP|終値方向反転>=2、効率<=1/3、幅>=0.5S|
|拡大/縮小|1.5倍以上 / 2/3以下|
|Recovery完了|episode開始H以上、ただしUP構造確定とは別|
|cross確認|次2連続予定close、順序/欠測区別|
|future上限|同日次10 active minutes|

固定bpsをなくしても自由度が消えるわけではない。ここに列挙した選択は全てTrial Ledgerの1候補として扱う。実市場成績によるsweepは0。

## 13. 検証・停止

`reference.py` / `test_reference.py` / `verify.py`はこのdirだけで完結するstd-libraryの参照コード。旧research modulesをimportしない。自動取得、学習、注文、batch市場再分類CLIはない。

`source-lock.json`で仕様/contract/参照/テスト/verifierをSHA-256固定する。再検証は `python verify.py --output <新しい空path>`。既存outputは上書き拒否。合成testと固定fixture出力を2回実行し、manifest一致を確認する。

合成PASSは「選んだ定義がこの例/反例で実装通り動く」証拠。実市場の分類率や利益の証拠ではない。人間確認後の別Gate Gで初めて実データのcoverage、分類割合、代表例、未識別reasonを測る。

今回ここでSTOP。正解表を作らず、State候補の採用・G開始は人間判断。Frozen Selector、旧Evidence、Signal、Entry/EXIT、Dictionary、保護データ、Capitalを変更しない。Safety9項目false。正式自動昇格なし。
