# 5-Minute Entry State Definition — Zero-Based Design v0.1

2026-09-21 JST | Phase57 LONG-only | PR #587
**DESIGN_DRAFT_COMPLETE / HUMAN_REVIEW_REQUIRED / NOT_LABEL_READY**

これは新しい設計提案であり、既存ソースから発見された分類結果ではない。今回の成果は仕様文書だけ。分類コード、Ground Truth、因果認識、Signal Stats、BUY/WAIT測定は作成・実行していない。個別銘柄への売買推奨でもない。

## 1. 問いと設計の単位

> Selectorが選んだOpportunityについて、5分ごとにBUY NOW / WAITを判断するために「現在の銘柄状況」をどう表すべきか。

Stateは銘柄に1日1個貼るPathではなく、`security × session × asOf × scope`の状況記述とする。Opportunityはその記述を参照する。重複Opportunityがあっても、同じscope・同じ時刻の市場状態は同じになるべきで、選出時刻・Selector価格からの距離は別Contextにする。全Opportunity IDは保持し、銘柄統合を理由に削除しない。

旧5+1、旧STEP 2、10bps/30bps試作品は正解・閾値・教師ラベルとして継承しない。似た言葉を使う場合も、以下の参照構造と境界から改めて定義する。

## 2. まず分ける6つの情報

| 層 | 答える問い | 提案 |
|---|---|---|
| Observation | 何を観測できたか | 入力別・項目別のcoverage、鮮度、未確定理由 |
| Direction | 最新5分はどちらへ動いたか | UP / DOWN / UNCHANGED、程度は数値で保持 |
| Structure | 何に対して上昇/下降/レンジか | UP_STRUCTURE / DOWN_STRUCTURE / RANGE_STRUCTURE、scopeとanchor必須 |
| Phase | その構造のどの局面か | PROGRESSION / CORRECTION / RECOVERY / BALANCE / RESTRUCTURING |
| Events & Attributes | 何を突破・回復したか、どう動いたか | 水準別cross/reclaim、choppiness、expansion等。重複保持 |
| Context | 前日・今週・今日との位置関係は | 4時間軸を分離。矛盾もそのまま保存 |

**「Stateを7択にする」案ではなく、3構造＋5局面＋方向＋属性を組み合わせる案。**
未識別は4番目の相場構造にせず、`identificationStatus`へ分離する。StructureとPhaseにはnullを許す。Direction=UPはUptrend確定を意味しない。値幅ゼロと低volatilityも同じ意味にしない。

## 3. 4時間軸の役割

| 入力 | 保存する情報 | Stateの意味への使い方 | 禁止する解釈 |
|---|---|---|---|
| D-5〜D-1 Daily | OHLC、出来高/売買代金、日足HH/HL/LH/LL、5営業日の位置・range・gap | 直近1週間の背景。日足の下降内で今日反発、等を残す | 日足が上なので今日の下落を自動的に押しと断定 |
| Previous Day observed 1m | 前日内のswing、前日高安、終盤の方向、終値位置、VWAP、時刻別活動量 | 引き継ぐ水準と前日構造を明示する | 昨日上昇→今日も上昇を自動継承 |
| Today Open→asOf | 観測済み当日構造、当日高安、swing、range、gap後の経路 | 現在のprimary scope。既に形成された水準・脚に対する位置 | 前日の重要水準を消す、終日高安を朝の既知水準に混入 |
| Latest five closed 1m | 5本のOHLCV/value、内部順序、終端方向、極値・活動量 | 今変化していること。5分足1本への集約だけでは終わらない | 最新5分が上なら必ずRecovery/Continuation |

前日フル1mとは「前営業日に保存された全観測分足」であり、全予定分の完全観測保証ではない。正式な前営業日をcalendarで選び、欠けたら古い別日を代用しない。
D-5〜D-1も正確な5営業日。D-6は5期間close-to-close計算等に必要なら別の任意入力とし、無いときに5営業日コンテキスト全体を捨てない。

日足context、前日context、当日structureが反対でも加点で一つに潰さない。例えば`daily=DOWN, previous_pm=DOWN, today=UP, direction5=DOWN`をそのまま表し、当日の上昇内の押しと日足逆行が併存する。

## 4. 時刻契約 — 今と次の5分を取り違えない

### 4.1 更新とラベルの対象

T=Selector選出時刻。Tで初回状況を評価する。T+5まで自動で待つ設計にはしない。以降はT+5k active minutesで評価を予定する。毎分足を受け取っても最終State更新周期を毎分に変更しない。

**State(t)の対象はtで終了した最新5予定取引分と、その時点までの構造。**
`NEXT_INTERVAL_STATE(t,t+5)`は将来5分の記述であり、State(t)とは別の予測対象。正解表で列を混ぜない。

例: 10:05のStateならbar-start表記では10:00,10:01,10:02,10:03,10:04の5本を使う。10:05開始足はまだ対象外。bar-end表記のproviderでは対応するend時刻へ明示変換する。
T+0でもT以前の5本を使えるなら評価する。09:00等で当日分が足りない場合は前日contextだけを表示できるが、昨日の5本を「最新当日5分」に接ぎ足さない。

### 4.2 予定取引分と観測本数は別

5分は「5本データが来るまで」ではなく、calendar上の5 active minutes。2本欠けても次checkpointを後ろにずらさない。`expected=5, observed=3`を保持する。

昼休みをactive minutesに数えない。跨ぐ場合は区間をsegment分割し、ギャップを連続1分リターンにしない。contiguousな5本が必要な項目はnullにするが、checkpoint行や前後contextは残す。
例えば11:28から5 active minutes後は12:33となり得る。2分＋3分の跨ぎは5本連続のmicro-pathではない。12:30に前場最後のStateを現在Stateとして再発行しない。再表示するなら`stale=true, lastEvaluatedAt`必須。

引け前も「残り30分以上」「選出後20本以上」の一律Gateを持ち込まない。14:30、15:00も最新5分と参照構造が観測できれば対象。将来確認用の足が無ければ、その確認だけCENSOREDにする。

現行の通常例では15:25までのザラバと15:30の引け板寄せを区別する。15:25〜15:30を普通の5本の無約定足やレンジとして捏造しない。session日付ごとの制度を使い、古いsessionへ現在の時刻を遡及適用しない。[S2][E1][E2]

### 4.3 確定と入手可能時刻

`barStart < t`だけで、本当にその時点で入手できたことまで証明したとは言わない。保存データのtimestamp convention、bar終了、revision、knownAt/receivedAt、provider仕様を別々に記録する。
Historical再構成とclean PITは別。仕様上のclosed時刻と実受信時刻が同じ保証はない。今回その実装・検証は行わない。

## 5. Direction — 単純な事実と意味を分ける

同一segment内の完全な5本を`(O_i,H_i,L_i,C_i,V_i,A_i), i=1..5`とする。
`netReturnPct = 100*(C_5/O_1-1)`。

Directionは正の価格比較でUP、負でDOWN、同値でUNCHANGEDとする提案。これは符号記述であり「有意なトレンド」「買い好機」の判定ではない。FLATを微小値幅の任意閾値で代用しない。
価格の同値比較はproviderのdecimal precisionと正規化basisに従う。市場ノイズ幅や銘柄ごとの呼値と、計算機の丸め誤差を混同しない。

TURNING_UP/TURNING_DOWNはDirectionの排他選択肢ではなく、順序のある転換イベントへ分離する。上昇終端でも途中で下げて戻した可能性があるため、`netDirection`と`turnEvents[]`の両方を保存する。
5本の終値差は4個で、ゼロ差を除いた符号反転は最大3回。始値から最初の終値の変化を足した別指標と混同しない。旧10本用の反転回数条件を5本へコピーしない。

## 6. Structure — 基準なしの「上昇」をなくす

`swing`は価格の脚を区切る高値/安値、`anchor`はどの脚・水準を参照するかの明示記録。単に隣接する1m高値が上がった事実と、structural swingの切り上がりは別のdescriptorにする。

| Structure候補 | 自然言語定義 | 機械化に必要な証拠 | 否定・不足の場合 |
|---|---|---|---|
| UP_STRUCTURE | 同じscopeの構造的高値・安値が切り上がり、保護する安値がまだ破られていない | 同一scaleの交互pivot列、比較したhigh/low pairs、protectedLow、判定時点 | 高値だけ更新では足りない。支持安値破れは旧上昇を無条件維持しない |
| DOWN_STRUCTURE | 構造的高値・安値が切り下がり、保護する高値がまだ上抜かれていない | 同一scaleのpivot列、high/low pairs、protectedHigh | 陰線1本や最新5分DOWNだけで確定しない |
| RANGE_STRUCTURE | 特定の上下境界の内側にとどまる均衡構造で、片方向のstructural progressionが確認されない | window開始、固定したupper/lower、複数接触と滞在、幅・効率 | UP/DOWN不成立の全件をRANGEに入れない |

同一scope・同一scaleで上昇と下降の両方を同時確定しない。複数scaleの結果が異なるなら別scopeとして保持する。Todayの局所反発と前日下降は矛盾ではない。
`structure.status`はIDENTIFIED / AMBIGUOUS / UNRESOLVED / NOT_OBSERVABLE。何にでも名前を付けるためにUNRESOLVEDをRANGEへ変換しない。

pivot抽出scale、確認条件、equal-high/low tie handling、range期間と接触条件はSection 13のparameter lockが必要。v0.1は意味と必要証拠を定義した案で、数値未固定のまま分類実行してはならない。

## 7. Phase — 構造内の位置と順序

| Phase候補 | 意味 | 必要な前提・境界 |
|---|---|---|
| PROGRESSION | 既存構造の方向へ進行し、対向脚の回復途中という説明ではない | structure方向、直近完了脚、現在脚の向き、更新した構造水準 |
| CORRECTION | 既存構造と逆方向に進むが、その構造のinvalidation水準は未突破 | 有効な親structure、開始極値、対向脚、invalidation水準 |
| RECOVERY | 識別済みの対向脚・下落episodeを、その後の上方向移動が取り戻している | episode開始高値、後の安値、その後の回復という順序と回復対象ID |
| BALANCE | 既存range内で均衡を保ち、方向脚への移行が確認されていない | RANGE_STRUCTUREとその境界。小さなnetReturnだけでは不可 |
| RESTRUCTURING | 旧構造を壊す境界突破はあるが、次の構造を成立させる証拠は揃わない | 旧structure ID、失効水準、break event、新構造の未充足条件 |

### 7.1 人間向けの読み方

| 組合せ/状態 | 表示例 |
|---|---|
| UP_STRUCTURE + PROGRESSION | 上昇継続 |
| UP_STRUCTURE + CORRECTION | 上昇構造内の押し |
| DOWN_STRUCTURE + PROGRESSION | 下落継続・弱さ優勢 |
| DOWN_STRUCTURE + CORRECTION | 下落構造内の反発 |
| 識別済み下落episode + RECOVERY | 下落分の回復中（親構造は別表示） |
| RANGE_STRUCTURE + BALANCE | レンジ内均衡 |
| 旧構造invalidation + RESTRUCTURING | 構造移行中 |

Recoveryとdowntrend内の反発は同義ではないが、同時に真になり得る。親structureがDOWNで下落脚を取り戻している場合は`DOWN / {CORRECTION, RECOVERY}`を許す。phaseは根拠付き集合で、都合の良い1ラベルへ圧縮しない。

### 7.2 押し・回復・再上昇の境界

上昇→下落を全てPullbackと呼ばない。親UP_STRUCTUREと保護安値が必要。これが無ければDOWNという観測事実と未識別のphaseを残す。

Pullbackは「後で必ず回復する下落」と定義しない。途中で失敗しても、当時の押しの記述を成功例だけに書き換えない。後で支持安値を失った時点からRESTRUCTURINGへ移る。

下降episodeの開始高値Hから安値Lを経て現在価格Cに戻る場合、`recoveredFraction=(C-L)/(H-L)`を保存する。H=Lなら未定義。1超や0未満を黙ってclipしない。Lは最新窓の都合の良い最安値を毎回採り直すのではなく、episode IDと更新理由を持つ。

CがHを回復したら「当該episodeの価格回復完了」。それだけで上昇トレンド確定ではない。続く構造的HH/HLと親structureを別に確認する。回復途中、回復完了、構造回復は別列。

## 8. Events / Attributes — Breakoutを何でも同じにしない

Breakoutは「何%上がったか」ではなく「何を上抜いたか」。参照水準を事前のprice pathから固定し、水準ID・scope・設定時刻・price basisを保存する。

| 参照水準 | 別名で保持する理由 |
|---|---|
| PREVIOUS_DAY_HIGH / LOW / CLOSE | 前営業日の水準。official daily値とobserved minute extremaは出所を分ける |
| PREVIOUS_DAY_SWING_HIGH / LOW | 前日内の構造的水準。終盤か全日かも明示 |
| TODAY_PRIOR_HIGH / LOW | 対象区間より前の当日極値。対象区間自身を含む最終高安を使わない |
| LOCAL_RANGE_UPPER / LOWER | 固定windowと境界を持つrangeの上限/下限 |
| STRUCTURAL_SWING_HIGH / LOW | 当日の構造水準。pivot確認時刻を別に記録 |
| VWAP_REFERENCE | 固定水準でなく時刻付き系列。VWAP自身の移動によるcrossも区別 |

同一1mでHigh>levelだがClose<=levelならWICK_TOUCH/REJECTION候補。Closeが内側から外側へ移ったCLOSE_CROSSとは区別する。`previousClose <= level < currentClose`は素の上方crossの定義候補で、bufferや継続確認付きの「有意なBreakout」は別契約にする。

水準を下回った後に戻すRECLAIMと、未突破上限を初めて抜くBREAKOUTを履歴で区別する。後の定着・失敗は将来確認タグであり、現在crossの有無を書き換えない。

CHOPPINESSは方向転換回数、進行効率、振幅等を示す重複可能属性。上昇しながら往復もあり得る。CHOPを優先してRecovery/Breakoutを消さない。
VOLATILITY_EXPANSION / COMPRESSION、ACTIVITY_EXPANSION / CONTRACTION、HIGHER_LOW / LOWER_HIGH、GAP/RECESS_GAP等も別軸。二値閾値が未固定なら連続descriptorを残し、タグを勝手に確定しない。

## 9. 計算可能にするdescriptor契約

| Descriptor | 定義・注意 |
|---|---|
| net return | 5本のC_last/O_first-1。close-to-closeは前checkpoint価格との別列 |
| envelope | max(H)-min(L)、基準価格で正規化。missingなら観測下限としての範囲と明示 |
| adjacent HH/HL/LH/LL | 隣接1mの高安比較。structural pivot比較とは別 |
| close-path efficiency | abs(C_last-O_first)/(abs(C_first-O_first)+sum(abs(diff(C))))。分母0はNO_MOVEMENTとしnull。High/Low内の全往復を再現した指標ではない |
| raw direction changes | 同一連続segment内の終値差の非ゼロ符号反転。gapを跨がない |
| realized volatility | 連続1mのlog-close差の標準偏差等。窓長とddof固定が必要。5本だけの値を銘柄の長期volと呼ばない |
| drawdown/recovery | 必ずどのpeak/low/episodeからかを指定。10分窓の極値と前日構造極値を混同しない |
| volume/value | 同じ長さ・対象時刻の前window/前日window比とraw値。分母0・欠測はnull |
| VWAP | 同じ対象集合のsum(tradingValue)/sum(volume)、単位の一致必須。全日VWAPと部分観測VWAPを別名にする。欠測VaをClose×Volumeで埋めない |
| reference distance | pct(C/reference-1)。どのscopeのどの水準か、設定/確認時刻を持つ |
| normalized movement | abs(move)/S。S>0、Sの推定窓・利用可能時刻を保存。future全日rangeをNOW側Sに使わない |

OHLCVだけで板の厚さ・買い手の意図・注文フローを観測したことにはしない。出来高/売買代金は価格変化に伴う活動量の記述で、売買方向の因果証明ではない。

## 10. Multi-label / Transition / 継承

各タグに`scope, anchorId, evidenceIds, effectiveAt, confirmedAt, knowledgeCutoff`を付ける。
異なるscopeの上向き/下向きは共存可能。同一scaleのStructure矛盾はIDENTIFIEDにせずAMBIGUOUS。同一episodeのCORRECTIONとRECOVERYは「親構造と逆方向の反発、かつ先行下落分を回復」のように意味が両立する場合に限り併存する。

Transitionは連続checkpointの同じscope・anchor系統を比較する。ラベル集合が変わっただけで経済的転換を断定しない。anchor失効、parent更新、イベント時刻、added/removed tags、same-bar/gap ambiguityを記録する。
5分内で複数変化があれば`withinWindowEvents`に順序を保存する。State(t)は窓の終端状況、窓の最頻Stateではない。観測の切れ目で直前Stateを現在確定値としてforward-fillしない。

前日情報はcontextとして読み込み、当日local episodeはsessionでリセットする。前日水準は参照可能だが、overnight gapを連続1m returnに含めない。昼休み後も前場の構造はcontextとして保存し、gap後にinvalidation水準を再確認する。休憩自体を値動きの反転と数えない。

## 11. Observationと「分からない」の契約

| ケース | 記録 | できること/できないこと |
|---|---|---|
| 全予定5本が有効 | windowStatus=COMPLETE | 5分内部descriptorを計算可能。ただしsemantic Stateの確定とは別 |
| 1〜4本のみ | windowStatus=PARTIAL | 観測値・観測範囲は保持。欠けた分の形や反転を断定しない |
| 0本/無効OHLC | UNAVAILABLE/INVALID | 該当項目null、理由付き。旧Stateで埋めない |
| 前日不在 | PREVIOUS_CONTEXT_UNAVAILABLE | 当日Directionまで一緒に無効にしない |
| daily一部欠測 | DAILY_CONTEXT_PARTIAL | ある日付の情報は保持。5日完全要件の計算だけnull |
| 比較basis不明 | PRICE_BASIS_UNVERIFIED | 前日/日足を跨ぐ水準比較を止める。調整済/未調整を混ぜない |
| 同一足内順序不明 | ORDER_AMBIGUOUS | 価格のHigh/Low値は保持、Low→Highだったと断定しない |
| 十分観測したが定義不足 | UNRESOLVED_DEFINITION | OTHER_OBSERVED_PATTERN＋descriptor。分類できた数には含めない |
| 複数の意味が両立 | 複数タグ | UNKNOWN扱いにしない |

missing rowだけからNO_TRADE/HALT/PROVIDER_LOSSを断定しない。根拠が無ければUNRESOLVED_SOURCE_CAUSE。confirmed no-tradeも捏造OHLC足にはしない。
未知を減らす方針は「根拠付きで説明可能な項目を増やす」。UNKNOWNの名前を変えただけで分類率向上と呼ばない。分母は全予定checkpoint、完全観測subset、意味を判定できるsubsetを別々に報告する。

## 12. Future-assisted reference labels — 次工程の契約案

**実測価格は事実だが、Stateは定義に依存する注釈。未来を見れば唯一絶対の正解になるわけではない。**
「正解表」というUI名を使っても、内部には`definitionVersion`付きのreference labelsとして保存する。

同じcheckpointについて次を分離する。

| 列/集合 | 内容 | 後の因果側の入力可否 |
|---|---|---|
| observedFactsAtT | t以前の観測・純粋descriptor | provenance要件を満たすものだけ可 |
| oracleStateAtT | 前後の経路でpivot/episodeを確定し、t時点の構造を振り返る | 入力禁止、教師/比較対象専用 |
| futureConfirmation | いつ何を見て解釈を確定したか、future horizon、右端打切り | 入力禁止 |
| nextIntervalDescription | t以降の次5分の方向/出来事 | 別予測対象。oracleStateAtTと取り違えない |

oracle pivotは`effectiveAt`と`confirmedAt`を必ず分ける。10:10が後で底と判明しても10:10時点で既知だったことにしない。因果出力はその時点で書き込み後immutableとし、future suffixで書き換わらないことを後Gateで検証する。

未来確認の最大horizonとconfirmation条件をlabel生成前に固定する。銘柄ごとに成功するまで先を延ばしたり、朝だけ長いfutureを許して引け前と同条件と呼んだりしない。同日内で制限し、翌日情報で救済しない。
引け付近は未来確認だけRIGHT_CENSOREDとなり得る。その場合でも直接観測したDirectionやcross等を消さず、State全体を一律不明にしない。

同一1mのHigh/Low順序・欠測内部の経路は、後続足を見ても確定しない場合がある。意味的な妥当性は独立レビュー用の例・反例で確認する。自己実装したルール同士が一致しただけでState理解100%と呼ばない。

**現在状態の認識と、その後の上昇予測は別の評価。**
旧全日Recovery predicateを全checkpointへ貼り、朝のRECOVERY認識と比較する方法は新設計では使わない。[S4]

## 13. 閾値・parameter lock — まだ市場分類をしてはいけない理由

| ID | 必要な決定 | 今回の提案/根拠候補 | 状態 |
|---|---|---|---|
| P0 | 更新周期・窓の向き | 5 active minutes、tで終了した最新5予定分、Tで初回評価 | USER_DIRECTION / 本仕様で明文化 |
| P1 | Direction符号 | UP/DOWN/UNCHANGEDの価格比較。固定bpsでノイズを消さない | PROPOSED |
| P2 | structural swing scale | 符号反転だけを大きなswingと同一視しない。過去基準vol/range尺度Sとq_swing*S、呼値・precisionを区別 | OPEN |
| P3 | UP/DOWN成立・失効 | 同一scaleの複数pivot比較、protected swingとcross確認方式 | 概念規則提案、機械的lockはOPEN |
| P4 | RANGE成立 | window/固定境界、接触・滞在、正規化rangeとefficiency。trend不成立の補集合は禁止 | OPEN |
| P5 | 意味的cross/定着 | 素crossは記録。有意crossのbuffer、close維持時間は別定義 | 素cross提案、追加確認OPEN |
| P6 | chop/expansionタグ | まず連続値。二値化の必要性・閾値は別に固定。10/30bpsを無断継承しない | OPEN |
| P7 | oracle確認期限 | 固定最大future horizon＋same-session censor。成功まで可変延長しない | OPEN |
| P8 | 対象calendar・価格basis | 保存contractと公式制度を照合。corporate action/単位/knownAtの品質契約 | 意味固定、データ別検証は未実施 |

固定価格率には比較の容易さ、vol正規化には銘柄差を表す利点がある一方、scale推定が疎い場合の不安定性がある。これらは設計上のtrade-offであり、有効性の測定結果ではない。Sの出所・sample数・as-of・下限処理を定義せずにATRやσという名前だけで解決したことにしない。

**数値が必要な箇所を未固定のまま実装者に任せて全件labelを作らない。**
次のDレビューで1つの再現可能なparameter/algorithm契約を作り、値・根拠・定義バージョンを固定する。候補探索や市場結果による調整をするなら別途人間承認が必要。Ground Truth、BUY収益、Unknown最小化を見てパラメータを選ばない。

## 14. Signalとの将来接続

SignalはStateを理解する材料にも、BUY/WAITへ直接入る情報にもなり得る。Stateだけを見てSignalを消す、またはSignalが出ただけでBUYとする設計ではない。

新Stateラベルを既存Signalのtrigger丸写しで作らない。後のState×Signal評価が同じ条件の再発見になるため、構造からの記述と6 Signalのイベント値は別に保存する。

同じ5分内に起きたSignalを使ってStateを決め、同じSignalがそのStateを説明したと重複計上しない。将来S Gateでは`stateBeforeEvent`と`stateAfterEvent`、情報重複、State-only対State+Signal、利用時刻を固定する。Signalの寿命・5分内で無効化されたイベント・複数Signal競合も、そのGateの課題として残す。

この仕様はSignalの使用時刻を毎分BUYへ変更する許可ではない。ユーザーの5分再評価周期を維持し、その間のclosed 1mイベントは後で集約する案。実際のtiming/fallback/fill/retryはE Gateで決め、既存Entryは変更しない。
Signalなし=候補廃棄にはしない。予定fallback BUY attemptの具体時刻は今回決めない。

## 15. 例・反例 — 全て模式例で実測ではない

| ケース | 正しく残す記述 | 避ける分類 |
|---|---|---|
| 前日上昇、当日HH/HL、最新5分下落、支持安値未突破 | direction=DOWN、today UP、CORRECTION、previous UP | 最新5分が下なので全体DOWN確定 |
| 前日下降、当日LH/LL、最新5分上昇、構造高値未回復 | direction=UP、today DOWN、CORRECTION、回復episodeがあればRECOVERYも | 反発=上昇トレンド復帰 |
| 日足下降、前日下降、当日構造高値突破後HH/HL形成 | daily/previous DOWN、today UP、変更イベント | 上位時間軸と違うのでUNKNOWN |
| 上昇しながら何度も往復 | UP direction＋UP structureの証拠＋choppiness | 全てCHOPに置換 |
| 前日高値をwickで越えたが終値は内側 | PDH WICK_TOUCH、close cross=false | Breakout成功 |
| 5分の始終値同値だが大きく上下 | UNCHANGED＋大きいenvelope/choppiness descriptor | 無値動き/低volatility |
| 15:00〜15:05が完全観測、15:05以後が確認期限未満 | 15:05の事実は記述、future確認はCENSORED | 終日30分不足で全State不能 |
| 前日データ欠測、当日5本は有効 | local directionは記述、previous status不足 | Opportunity全体削除 |
| 同一1mで上限/下限を両方超える | 両水準touch＋ORDER_AMBIGUOUS | 都合の良い順序を選択 |

模式的な一連の流れ:
`UP構造 / PROGRESSION → DOWN方向 / CORRECTION → UP方向 / RECOVERY → 回復完了イベント → UP構造 / PROGRESSION`
この後に失敗しても過去全区間を失敗ラベルへ遡及置換しない。実数値チャートは今回は生成していない。

## 16. レコード設計案

| フィールド群 | 必須内容 |
|---|---|
| identity | opportunityId, securityId/provenance, session, selectorAt, asOf, gridId, definitionVersion |
| time | windowStart/windowEnd, barTimestampConvention, expectedStamps, observedStamps, segments, closedThrough, availableThrough |
| observation | latest5/previous/daily/today別status, reasonCodes, priceBasis, source hashes |
| context | daily5, previousDay, today、各scopeのsource/effective/confirmed時刻、相互の方向矛盾 |
| structure | scope, value or null, identificationStatus, swingScaleId, pivotIds, protectedLevelId |
| phase | tags[], episodeId, startPeak/low, recoveredFraction, invalidationEvidence |
| events | type, levelId, eventAt, confirmedAt, before/after State, ambiguity |
| descriptors | raw数値、正規化値、分母/scale provenance、欠測理由 |
| referenceLabel | observedFactsAtT, oracleStateAtT, futureConfirmation、参照・因果を分離 |
| lineage | parentStateId, added/removedTags, supersedesVersion, reviewer status |

今はレコード形式の設計のみ。実データレコード、学習schema、labelerは未生成。StateオブジェクトにはBUY/SELL/利益の正解を入れない。

## 17. Definition Gateの完了条件と次作業

今回達成したのは、4時間軸、Direction/Structure/Phase、イベントと属性、時刻、境界、未知、Future区別、Signal接続、parameter未決事項を文書にしたこと。

**D全体のfreezeはまだ。** D freezeには人間による意味の承認、P2〜P8等の必要な機械的契約固定、synthetic例/反例による仕様整合の検証、label生成用contract hashが必要。今回synthetic engineを実装/実行したとは主張しない。

次は人間がこの設計案を確認する。承認された範囲でD内の未固定項目を詰めるだけで、Gの正解表生成へ自動進行しない。

`D Definition → G Future reference table → C Causal Recognition → S State×Signal → E BUY/WAIT → 必要時Learning`

## 18. Safety / Source separation

Frozen Selector、既存Entry/EXIT/Capital、旧Evidence、mainは変更禁止。今回文書追加だけ。市場データ再測定0、Ground Truth生成0、trainingなし、Signal評価なし、Dictionaryなし、新規provider取得0、protected data開封0。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false

本文[S1]〜[S4]はSOURCE_AUDIT_2026-09-21.mdの読取ソースを参照。[E1][E2]はJPX公式の制度資料。提案したState構造・Phase・parameter案は新設計であって、JPXや旧コードが推奨・実証したものではない。


## 19. Mechanical Parameter Lock v0.2 — Swing / Structure / Phase

Status: **PROPOSED_MECHANICAL_LOCK / SYNTHETIC_TEST_REQUIRED / NO_MARKET_LABELS_YET**

This section converts the conceptual definition into one deterministic mechanical contract. It is still a proposal until synthetic tests pass and the human accepts it.

### 19.1 Causal scale S(t)

For every scope and asOf t, define a causal movement scale:

- Preferred intraday scale: median of valid absolute 1m log returns over the previous observed trading session, multiplied by current reference price.
- Fallback when previous-day minute history is insufficient: median absolute 1m log return from Today Open->t when at least 30 contiguous valid returns exist.
- Final fallback: D-5..D-1 median daily true range divided by sqrt(N_active_minutes) only for normalization diagnostics, not for pivot confirmation.
- If no intraday scale is available, structural swing/phase identification is NOT_OBSERVABLE rather than silently using a fixed bps threshold.

Record S source, sampleN, asOf, and whether it is fallback. Never estimate S using future rows or the current five-minute future suffix.

### 19.2 Swing pivot confirmation

Use a directional-change pivot process, not adjacent-bar HH/LL noise.

Let qSwing = 3.0 and threshold = qSwing * S(t), with a floor of 2 valid ticks at the pivot price.

Process each contiguous regular-session segment in chronological order:
1. Start from the first valid close as current extreme.
2. In an upswing, keep updating the highest observed High and its timestamp.
3. Confirm SWING_HIGH when a later observed Low is at least threshold below that extreme.
4. In a downswing, keep updating the lowest observed Low.
5. Confirm SWING_LOW when a later observed High is at least threshold above that extreme.
6. effectiveAt = extreme bar timestamp; confirmedAt = first later bar proving the threshold reversal.
7. Equal highs/lows: keep the earliest extreme timestamp and latest equal-price touch separately; confirmation compares price, not touch count.
8. Missing/lunch/session gap ends the current confirmation segment. Do not use a post-gap price to prove an intrasegment reversal.
9. A pivot may be recognized retrospectively in Future reference labels from effectiveAt, but causal recognition may only use it from confirmedAt.

No fixed 10bps/30bps swing threshold is inherited.

### 19.3 UP / DOWN Structure

Use confirmed pivots on one swingScaleId.

UP_STRUCTURE requires, in order:
- at least two confirmed SWING_HIGH and two confirmed SWING_LOW pivots,
- latest confirmed high > prior confirmed high,
- latest confirmed low > prior confirmed low,
- protectedLow = latest confirmed SWING_LOW that preceded the latest structural high,
- no later observed close below protectedLow.

DOWN_STRUCTURE is symmetric:
- latest confirmed high < prior high,
- latest confirmed low < prior low,
- protectedHigh = latest confirmed SWING_HIGH that preceded the latest structural low,
- no later observed close above protectedHigh.

If both directional tests would appear true because scopes/scales differ, keep them under separate scope/scale records. Under identical scope+scale, return AMBIGUOUS rather than both.

Structure invalidation occurs on a close beyond the protected level. A wick-only violation is an event but does not invalidate structure by itself.

### 19.4 RANGE_STRUCTURE

A range is not the complement of trend.

Range candidate requires:
- at least 20 active minutes of same-segment history,
- at least 3 confirmed alternating pivots after the candidate begins,
- upper/lower boundary defined by the max/min of those confirmed pivots,
- normalized width (upper-lower)/S(t) finite,
- close-path efficiency over the candidate <= 0.35,
- no two consecutive closes beyond the same boundary.

To avoid arbitrary absolute-bps range labeling, do not impose an additional fixed width cap in v0.2. Width is retained as a descriptor. RANGE_STRUCTURE is identified only when the alternating-pivot and low-efficiency conditions are satisfied.

Candidate ends when:
- structure breakout is confirmed by two consecutive closes beyond a boundary, or
- a new UP/DOWN structure is confirmed on the same scale.

### 19.5 Phase mechanics

PROGRESSION:
- parent structure identified,
- latest five-minute netDirection matches parent structure direction,
- no currently active opposite corrective episode requiring RECOVERY.

CORRECTION:
- parent UP_STRUCTURE with latest netDirection DOWN, or parent DOWN_STRUCTURE with latest netDirection UP,
- protected level not invalidated.

RECOVERY:
- an explicit opposite-direction episode exists with startExtreme H/L and subsequent opposite extreme,
- current five-minute direction moves back toward the episode start,
- recoveredFraction > 0 and is increasing versus the previous checkpoint,
- recovery remains active until recoveredFraction >= 1.0 or a newer structural episode supersedes it.
- Recovery does not imply parent structure restoration.

BALANCE:
- RANGE_STRUCTURE identified and no confirmed boundary-break event active.

RESTRUCTURING:
- prior structure invalidated by close beyond protected level,
- new opposite UP/DOWN structure not yet confirmed.

Multiple phase tags are allowed only when their semantics are compatible and they reference explicit parent/episode IDs.

### 19.6 Breakout / Reclaim mechanics

For every pre-existing level ID:
- WICK_TOUCH_UP: High > level and Close <= level.
- CLOSE_CROSS_UP: previous valid Close <= level and current Close > level.
- CLOSE_CROSS_DOWN symmetric.
- BREAKOUT_UP event = CLOSE_CROSS_UP for a resistance-class level.
- RECLAIM_UP event = CLOSE_CROSS_UP after the same level was previously observed above price and later lost/below.
- HOLD_CONFIRMED_UP = two consecutive closes > level after the cross.
- FAILURE_UP = any later close <= level before HOLD_CONFIRMED_UP.

The raw cross event exists immediately at its bar. HOLD_CONFIRMED/FAILURE are later evaluator facts and must not rewrite the original cross timestamp.

### 19.7 Choppiness / expansion attributes

Keep continuous descriptors primary:
- directionChanges5,
- closePathEfficiency5,
- envelopeToScale5 = (maxH-minL)/S(t),
- realizedVol5,
- activity ratios.

CHOPPINESS binary tag in v0.2:
- directionChanges5 >= 2,
- closePathEfficiency5 <= 0.35,
- envelopeToScale5 >= 2.0.

VOLATILITY_EXPANSION tag:
- realizedVol5 >= 1.5 * median realizedVol5 of the previous six complete five-minute windows.

VOLATILITY_COMPRESSION:
- realizedVol5 <= 0.67 * that causal baseline.

If baseline windows are insufficient, tag is null and the raw descriptor remains.

### 19.8 Future reference confirmation horizon

For Future-assisted reference labels only:
- fixed maximum future confirmation horizon = 15 active trading minutes after the checkpoint,
- same session only,
- never cross overnight,
- lunch recess does not count toward 15 active minutes but breaks intrasegment continuity,
- if session end arrives earlier, mark RIGHT_CENSORED,
- do not extend horizon until a desired label becomes confirmable.

This 15-minute horizon is for confirming pivots/episode interpretation, not for scoring future return and not for causal input.

### 19.9 Synthetic acceptance tests required before Freeze

At minimum:
1. clean rising HH/HL => UP_STRUCTURE,
2. clean falling LH/LL => DOWN_STRUCTURE,
3. uptrend + five-minute decline above protectedLow => CORRECTION,
4. correction then rebound => RECOVERY,
5. close below protectedLow => RESTRUCTURING,
6. alternating pivots + low efficiency => RANGE/BALANCE,
7. wick-only level breach => no structure invalidation,
8. close cross + second close => BREAKOUT + HOLD_CONFIRMED,
9. cross then close back => FAILURE,
10. missing minute => no synthetic continuity,
11. lunch gap => no cross-gap pivot confirmation,
12. same-price highs => deterministic tie handling,
13. insufficient previous scale => NOT_OBSERVABLE, no fixed-bps fallback,
14. right-edge confirmation shortage => RIGHT_CENSORED,
15. causal suffix mutation after t cannot alter observedFactsAtT.

Freeze is allowed only after all synthetic tests pass and a contract hash is saved. No market outcome, BUY performance, or Unknown-rate optimization may modify these parameters after the test run begins.
