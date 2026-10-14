# 新Selector V2 — 上昇継続型・3層選別設計

設計日: 2026-10-14 JST
設計ID: ARK_PREOPEN_SELECTOR_V2_TREND_CONTINUATION_DESIGN_20261014
状態: DESIGN_PROPOSAL / NOT_IMPLEMENTED / NOT_TRAINED / NOT_QUALITY_CERTIFIED
対象: Iam-2squared/ark-terminal の新V2設計のみ。

**これは設計書であり、追加学習・保護期間の開封・実運用を許可する実行precommitではない。** 第1・第2層を固定ルール、第3層を条件付き学習に分離する。V1の単純な係数調整や、結果を見ながら候補を増やす探索は行わない。

## 0. 保護対象と参照位置

GitHubで読み直したPR #593はOpen/Draft/未merge。V1 HEADは55085fa4f4487cea8dcb30ee2a1c3e668f691da6、Frozen baseは10c94c92c4bd2a59a22744667fd0210252602df4。本書は別branch research/preopen-selector-v2-design-20261014 に追加するだけで、V1 branch、PR #593の設定、旧Frozen No.1/No.1.1、State9原本、旧Selector/Entry/EXIT/Capital、PR #591、main、A～Eデータ保存先、口座、Excelを変更しない。

V1 model SHA256: e82279729b9ccc02fbcf7a1ffced7ade9057d8be41b058963dc4133e4ea19b48
V1 root computation SHA256: 3a2fb32dfad9e2ea4f9956038709f2a640a3380213f68ca7af8f1c9c621950ab
V1 original exact ledger SHA256: c89f75b30d19038cdc7de8d4d785ce9ce50af1c633c0ad1c6dc55ab2e1eaf6e1
V1 split SHA256: e18a181197927bed31b22fb376c42eb35fd0ed42dcabbbb88f7ffcc0b7208325

既存のMA4_EFFECTIVE_PRECOMMIT_20261013_V2.jsonの「V2」はV1内の特徴量方針改訂番号であり、本書の新Selector V2とは別identity。

## 1. V2が解く問題

目的は、単に下落しにくい銘柄を選ぶことではなく、**長中短期の上昇構造があり、直近の大きな損傷や容量不足がなく、翌日の寄り後に上昇機会が続く候補を選ぶこと**。

V1では既閲覧7営業日・105選出でHigh>=1%が34、>=3%が10、>=5%が2。Low<=-3%が5、<=-5%が0、前日売買代金LOW三分位が87。これは研究上の観測であって真の損失確率や執行損益の認証ではない。[S1]

V2は売買代金上位基準を超えることを主目的・主合格条件にしない。上昇機会の件数・率・日別供給、大きな逆行、選別で捨てた機会、約定容量の代理指標を同時に見る。

重要な限定: 「全時間軸が上昇している」は、今後も上がる証明ではない。下降・横ばいからの急反発や初動を今回の対象外にする、という戦略上の制約である。除外銘柄を『上がる確率0』『チャート的に上昇不可能』とは表現しない。

## 2. 全体構造

前提検査G0: 利用可能時刻・価格basis・市場/銘柄種別・必須履歴を確認
  -> 第1層G1: 長中短期の上昇構造を固定ルールで選ぶ
  -> 第2層G2: 前日暴落・履歴破損・参照資金に対する容量不足を固定ルールで除く
  -> 第3層M: G1/G2通過集合内で、上昇機会と大きな逆行の関係を学習する
  -> 確率の下限制約/上限制約と順位付け
  -> 朝08:50までに0～15銘柄の監視identityを固定
  -> 寄り後Entry/EXIT/現金集中・順次回転は別工程

第1・第2層は機械学習モデルにしない。理由は、明示的な適用対象と危険条件を学習結果で曖昧にしないため。第3層だけで予測の難しい『似た上昇構造から、さらに伸びるものと失敗するものの違い』を学ぶ。

各銘柄日は各層の判定、値、参照時刻、理由コードを持つ。最初の不通過理由だけでなく計算可能な全違反理由を記録し、層順序で原因が隠れないようにする。ルールを増やせば品質が上がるとは前提しない。

## 3. 時点・母集団・前提検査G0

Dは予測対象営業日、t=D-1は取引所calendar上の直前営業日。C_t/O_t/H_t/L_t/Va_tはtの調整前価格・円建て売買代金。X_DはDの08:50までに利用可能だった情報だけ。DのOpen/High/Low/Closeや寄り後Stateは教師・評価器のみに渡す。

対象はdated masterで確認した普通株・対象市場・現物・100株単位。V1との識別のため前日RAW終値>75円を初期案では維持する。今日のマスターで過去の銘柄を入れ直さず、現在の存続銘柄だけに限定しない。

日足独立SMA/EMAの期間は5/15/25/75のみ。第1層は説明が一意になるSMAで判定し、EMAと傾きの強さは第3層の説明変数として扱える。週/月独立MAを追加しない。MACD/RSI/ATR等の内部期間は独立MA期間と区別する。

MA75の前日差までに76営業日の比較可能な終値が必要。これは76日の教師を追加する意味ではない。欠測、営業日不整合、企業行動によるbasis不明はUNKNOWNとして別枠に落とす。株式分割等を架空の暴落にしない。未来の調整係数で過去系列を作り直さない。V1で許可された4日の日足履歴参照は元の許可範囲を保持し、そのまま教師や保護期間開放へ拡張しない。

## 4. 第1層G1: 上昇継続型への適用対象を固定

ユーザーの『全て下落/横ばいを落とす』だけでは上昇/下落混在が残る。本案は最後の要望『残った長中短期で上昇している候補』に合わせ、三軸すべてUPを主経路とする。混在はWAIT、三軸とも非上昇はREJECT、必要な値がなければUNKNOWN。WAITも当日の主経路には入れない。

S_n(t) = (C_t + ... + C_(t-n+1))/n
Delta_n(t) = S_n(t) - S_n(t-1)
UP_n(t) = [Delta_n(t)>0 AND C_t>S_n(t)]

| 時間軸 | UPの初期定義 |
|---|---|
| 長期 | UP_75 |
| 中期 | UP_25 AND UP_15 |
| 短期 | UP_5 |

G1 = UP_75 AND UP_25 AND UP_15 AND UP_5。
等号はUPに含めない。符号判定に丸めた表示値を使わない。小さな正傾きを強い上昇と呼ばず、傾き/ATRや高安構造は第3層で区別する。これらのルールはV2初期仮説であり、予測性能確認済みの条件ではない。

**全MAの完全な並び順S5>S15>S25>S75までは初期の必須条件にしない。** 三軸が上向いた初期の段階をさらに機械的に捨てることを避けるため。並び順や乖離の大きさは特徴量で持つ。

上昇/上昇/下落、上昇/横ばい/上昇などの混在を、候補不足という理由で主経路へ戻さない。底打ち反転型や横ばい上抜け型を対象にするなら、別の仮説と条件付き教師を持つ戦略を後で設計する。今回は分岐モデルを同時に大量学習しない。

## 5. 第2層G2: 平滑化に隠れる前日の損傷と容量

上昇MAが残っていても、前日の大陰線・ギャップダウン等を通過させない。MAは平滑化された情報なので、第1層と直近損傷の確認は異なる役割を持つ。

### 5.1 暴落判定の数値案

r_cc = 100*(C_t/C_(t-1)-1)
r_body = 100*(C_t/O_t-1)
r_gap = 100*(O_t/C_(t-1)-1)
z_loss = max(0, C_(t-1)-C_t)/ATR14_(t-1)

初期案は、r_cc<=-5% OR r_body<=-5% OR r_gap<=-5% OR z_loss>=3 のいずれかで除外する。ATRの分母には暴落当日tを入れない。基準のボラティリティが当日の急変で膨らみ、異常を通常に見せることを防ぐため。

- -5%は既存の値幅評価と対応づけた絶対的損傷の初期線、3ATRは平常時との乖離の初期線。最適値でもユーザー承認済み値でもない。
- 2/3/4/5%や2/3/4ATRを全探索して最良成績を選ばない。所有者が採用する一案を教師開封・市場fitの前に固定する。
- ギャップ後に回復した銘柄も初期案では除外され得る。これは直近大変動回避という保守的な選択であり、回復局面のWinner取りこぼしを診断する。
- 単なる『昨日少し下がった』『ATRが高い』『既に大きく上昇した』だけでは独立の追加除外を作らない。第1層の適用条件と混同せず、残った過熱・価格構造を第3層へ渡す。
- 支持線の特徴を作る場合は過去だけの固定rolling安値/既に確定した構造に限定する。後日判明する中心化pivot、ZigZagの確定未来、未来足で補正された転換点は禁止。

### 5.2 流動性は予測順位ではなく容量の前提

A_refは研究用参照資金であり、実口座残高を読まない。初期案A_ref=1,000,000円。B20=min(Va_t, median(Va_(t-19)..Va_t))、A_ref/B20<=rho、初期案rho=0.01。参照100株原価100*C_t>A_refの場合もREFERENCE_CAPITAL_INSUFFICIENTとして候補外にする。

この1%基準は容量の保守的な代理条件であり、売買代金が大きい順に買う設計ではない。前日だけの出来高急増で通常の容量不足を隠さない。一方、日次売買代金が十分でも寄り後の板・spread・注文拘束・slippage・全量約定が確認されたわけではない。翌日の実価格と予定数量はEntryで再確認する。

B20<=0、必要な過去売買代金欠測、円単位不明はUNKNOWN。欠測を0流動性とすることも、未来Dの出来高で補うことも禁止。100万円/1%は参照設計案であり、採用承認前に運用容量認証には使わない。

## 6. 第3層の教師: 上昇機会と大きな逆行を分け、結合を学ぶ

### 6.1 主教師はOpen起点・同一日同一basis

U_D = 100*(H_D/O_D-1)
A_D = 100*(1-L_D/O_D)  （非負の逆行幅）

O_Dは当該銘柄の実際の初回約定の始値。09:00寄りと決めつけない。H/Lは同じ調整前日足の当日全session値。正しいOHLCでU>=0なのでHigh負がないことを安全性と呼ばない。

上昇区分Bは従来どおり6区分: [0,1), [1,2), [2,3), [3,4), [4,5), [5,infinity)。
逆行区分Rは3区分: R0=A<3、R1=3<=A<5、R2=A>=5。
R0は『安全』『損失ゼロ』ではなく、『始値に対する-3%以下の安値に触れなかった』という観測条件だけ。

当日無約定/始値未確認/壊れたOHLCはUNKNOWN。市場teacherではUNKNOWNを不上昇や安全に変換しない。選出後に判明したUNKNOWNは候補を差し替えず分母へ残す。

### 6.2 2推定器の条件付き分解

第3層は1つのcandidate bundleの中に、役割が違う2つの推定器を持つ。

1. Risk推定器: G0/G1/G2を通った**全ての教師known行**でP(R0,R1,R2 | X,G)を推定する。
2. Opportunity推定器: 同じ通過集合のうちR0だった教師行でP(B | X,G,R0)を推定する。R0の中の動かなかった例・小さな下落例も必ず含む。

q_k = P(R0 | X,G) * P(U>=k | X,G,R0), k=1..5。
これはP(U>=k AND A<3 | X,G)の条件付き分解。独立な上昇確率と下落確率を掛けるのではない。q_kを無条件のHigh到達確率とは表示しない。

Risk推定器は良い上昇構造から急落した失敗を学ぶ。Opportunity推定器は大きな逆行がなかった例の中で『伸びる/伸びない』を学ぶ。後者をR0へ絞ることは、明示した条件付き分布の教師定義であり、悪い教師を全体から消す操作ではない。R1/R2例はRisk推定器に残る。

| 当日の例 | rawの記述 | 主目的への扱い |
|---|---|---|
| U=0.4%, A=0.2% | 大きな逆行なし、上昇機会なし | 高評価する正例にはしない |
| U=3.8%, A=1.2% | +3%機会、大きな逆行なし | Clean Winner3 |
| U=6.0%, A=4.0% | 大Winnerと大きな逆行が同居 | raw大WinnerにもrawLoserにも計数。Clean Winnerにはしない |
| U=6.0%, A=1.4% | +5%機会、大きな逆行なし | Clean Big Winner5 |

### 6.3 教師の限界を残す

日足では高安の到達順は分からない。+5%後に-4%となったケースを『必ず先に負けた』とはしない。上の主教師は全sessionにわたる逆行を避ける保守的な機会目的で、Entry/EXIT付き利益の最適化ではない。

順序を知るには、別の実観測経路が必要。初版では、確認済み分足/Tickによる+1/+3/+5到達時刻、-3/-5との先後、09:30/11:00/13:00/14:00以後の残存機会、上ヒゲだけか継続したかを**補助診断**に限定する。同じ足で高安両方に触れたらAMBIGUOUS、経路が足りなければUNKNOWN。日足から先後を生成しない。

V1の後半診断では参照不足が多かった。時刻付き教師が十分あることを未確認のまま必須教師へ昇格させ、観測しやすい銘柄だけに偏らせない。将来のEntry開発では実行方針・参照時刻・コストを別契約にする。

## 7. 順位付け: 下がらないだけの銘柄を加点しない

p3 = P(R1)+P(R2)、p5=P(R2)。先に大きな逆行の上限と上昇機会の下限を検査し、その中で順位を作る。

確率条件の初期案: q1>=0.50、p3<=0.05、p5<=0.01。
これは所有者に提示する選別方針の案であり、推定確率が正確な保証・観測損失率の達成宣言・採用承認ではない。較正と採用領域のsupportが弱ければQUALITY_NOT_CERTIFIEDのまま停止する。

OpportunityScore = q1+q2+q3+q4+q5。
これは E[1(R0)*min(5,floor(U)) | X,G] に対応する『大きな逆行のない、到達した1%段階の数』の期待値。+1/+3/+5の機会を1/3/5として扱う離散効用であり、費用後EVではない。

- 下がらなかったが上がらなかった例には効用0。
- +3や+5に届く機会は、+1だけより多くの効用を持つ。
- 下落ペナルティ係数を結果に合わせて0.5/1/2等に変える方式は採用しない。
- 5%以上は既存評価の上限区分として飽和する。+20%を取れた架空利益の加点はしない。
- Score降順、同点ならq5降順、次にcanonical symbol昇順。母集団は寄り前の同一G2通過集合。
- 通過候補から最大15。2件なら2件、0件なら0件。閾値を下げて穴埋めしない。朝の銘柄identityを固定し、寄り後の急騰株を追加しない。
- スコア・q1..5・p3/p5・各層の理由・参照時刻・source/model/schema hashを候補出力へ保存。entryAllowed等は全false。

確率の大小だけで実行可能性は判断しない。未来の買付数量、寄り付きギャップ、実機遅延、売却不能は未解決の後工程。

## 8. 学習する『場所』=どの銘柄状態を、どの時期から学ぶか

### 8.1 銘柄状態

市場全体を無差別に1つの順位モデルへ入れない。各過去営業日の08:50を再現し、将来の結果を見る前にG0/G1/G2を適用した集合が第3層の学習対象。実運用想定とFIT/CAL/VALIDATION/REPORTで同じゲートを使う。

正例はその中で翌日伸びたケース。重要な負例は『同じように上向いていたのに翌日伸びない』『高値圏で失速』『寄り天』『前日の急騰を使い切る』『上昇期待があったのに大きく逆行』したケース。既に下降中だった分かりやすい負例だけで分類を楽にしない。

結果がWinnerの日だけ抜く、下落相場の日を結果から捨てる、上昇した銘柄だけを後からG1へ入れる、同一銘柄の未来成績で通過条件を変える、SMOTE等で架空の相場系列を作る行為は禁止。

G1/G2で除外した行は第3層の主学習には入れないが、固定後の除外機会監査用にidentityと理由を保持する。適用外の下降/横ばいへモデルの確率をそのまま外挿しない。

### 8.2 期間

V1はFIT30/較正10/Report7日、全て既閲覧Development。Sourceの行数が多くても独立した相場局面が増えたわけではない。V2のゲート後はさらにサンプルが減るため、必要なのは行の水増しではなく時期の広がりと失敗例のsupport。

保存メタデータには日足2021-10以後、分足2024-10以後などの広い期間が記録されているが、これは新V2で全期間を利用できる許可ではない。V1では76 Development identityからsealを考慮して57、source coverageを考慮して47に制限した。REPORT19等の保護は解除されていない。[S2][S3]

**初期の期間設計案**は、時間順にFIT120営業日 / CAL20 / VALIDATION20 / FINAL REPORT40。最初のFIT日より前のMA等の履歴は教師ではない参照範囲として別途束ねる。この日数は実験規模の初期案で、統計的十分性の保証ではない。

- 正式な開始日・終了日・全営業日allowlistは、現在の利用権・seal・過去露出・source coverageをmetadataで照合してから一度だけ定める。
- 許可範囲が足りなければ、その不足を示して承認を得る。既存の47日に無理やり4区分を詰め込まない。
- V1 Report7日はV2設計の動機として既に閲覧したDevelopment。再利用しても未見評価に戻らない。使うなら新しい露出台帳に役割変更を記載し、最終評価にはしない。
- 新しいFINAL REPORTはモデル・ゲート・閾値・列選択に使わない。新しいファイルコピーや別のsplit名でFresh扱いにしない。
- 期間は成績や『上昇相場だった日』で選ばない。あらかじめ許可されたcalendarの連続的な窓を使い、保護gap・source欠損の除外理由を固定する。地合い別の構成は報告し、不得意相場の日を評価から削除しない。

### 8.3 時系列分割と重み

単位は(session,symbol)、分割単位はsession。銘柄日をランダムに混ぜない。教師が当日終値までのsingle-sessionなら、次工程のcutoffより前に教師とsourceが利用可能だったことを確認する。複数日に及ぶ教師へ変更したら、情報区間の重複をpurgeする別契約が必要。過去lookbackが重なることと未来ラベル漏洩を混同しない。

日ごとのG2通過数をN_dとし、Risk推定器の初期sample weightは1/N_d。Opportunity推定器のR0行でも**元の1/N_dを保持**する。条件付き集合内だけで別の日均等重みに作り直して、上の確率積の対象分布を変えない。CALでも同じ母集団・重みの定義を使う。

class-weightの恣意的な増幅で大Winnerを増やし、その出力を自然な確率として扱わない。少数classがFIT/CALに欠ける、特定の1日/1銘柄へ極端に集中する場合はsupport不足を明記して止める。負例や失敗イベントを人工的に複製しない。

## 9. 特徴量方針と市場時間の整合

種類の異なる説明材料を使うが、V1の463列を目的の検討なしに丸ごと増量することを目標にしない。初版のfamilyと検証する理由を先に登録する。

| family | 役割・候補特徴 |
|---|---|
| 上昇構造の強さ | MA4の乖離/傾き/ATR正規化、既知高安の切上がり、5/15/25日の騰落、直近20/60日高値との距離 |
| 上昇の余地と過熱 | 過去上昇の進み方、上ヒゲ・終値位置、直近急騰幅、MAからの伸び、過去の抵抗水準。『高値だから必ず落ちる』とはしない |
| 参加の強さ | 前日出来高/売買代金の通常時比、価格と出来高の整合、VWAP位置、買付額に対する過去容量proxy |
| 前日場中構造 | 後場の持続、押し戻し、引け前ザラバの失速、VWAPとの距離、auction寄与を分離したactivity |
| 市場・業種 | 前日までの地合い/セクター相対強弱・breadth。15銘柄だけで全市場breadthを作らない |
| 企業・イベント | 公表済みの決算/予想修正/日程/valuationの整合した変化。単なる大量の財務原数値を意味のある教師数と呼ばない |
| 補助State/Tick | 意味と可用性が揃った観測のみ。正式State欠測をRANGEにせず、未知aggressor/板を捏造しない |

列名・式・単位・lookback・source・publication/knownAt・欠測理由・code hashを列ごとに登録する。全欠測/定数除外はFITだけ。性能を見た列追加/除外、Reportの欠測率を見た列選択変更は禁止。Source未確認のfamilyを学習当日に無言で外すfallbackも作らない。最初の市場fit前に実際に使うprofileを固定する。

V1の短期Tickはauction close直後基準。[S4] 2024-11-05から15:25～15:30の非約定時間と15:30板寄せが導入された。[E1] 同じ1分/5分という名前でも、引け直後から遡ると市場制度の前後で意味が変わる。

**V2の設計変更:** 短期のザラバTick窓は日付別のcontinuous closeを基準にし、窓は[continuous_close-w, continuous_close)とする。板寄せは別のfeature familyへ分離。分足も同じ市場phaseを守る。時間窓を変えるのはV2の新仕様であってV1の原本/教師/結果を修正する理由にしない。

厳密なphaseが判別できない境界レコードはUNKNOWN。ザラバ終端参照価格が観測できない場合に板寄せ価格で置換しない。実取引ゼロ、価格変化不足、source未接続、時計phase不整合を別の欠測理由とする。16:30保存のEOD原本を15:25に実受信したログへ変換しない。次の朝の特徴として使うための公開・利用可能時刻確認は別途保持する。

この変更で成績が改善したという実測はまだない。学習の前に2024-11-05前後の人工例と許可済み範囲で、同じ名前の列が同じ量を表すことを検証する。

## 10. 有限の学習計画

現在の市場fit予算は0。本案を採用し、利用データ・列profile・数値条件・品質基準が承認された後の計画は以下の1candidateだけ。

| 対象 | 計画 |
|---|---|
| G0/G1/G2 | 学習0、固定ルールと人工テスト |
| Risk | HGBの3class推定器1回fit |
| Opportunity | HGBの6class条件付き推定器1回fit |
| CAL | 各推定器に1個の温度パラメータT>0を別CAL期間で推定、計2回 |
| VALIDATION | 較正・閾値変更なしで1回評価、失敗なら停止 |
| FINAL REPORT | VALIDATION通過後、同一modelで1回評価、再fitなし |
| 追加探索 | 初回candidate内では0。モデルfamily探索・seed巡回・層閾値grid・繰返し再学習なし |

学習器設定の初期案はV1と同じHGB lr=.05/max_leaf_nodes=15/max_iter=120/min_samples_leaf=40/L2=10/early_stopping=False、固定seed20261014。理由は、まず適用対象・教師・目的の変更を検査し、アルゴリズム探索まで同時に増やさないため。旧モデルの重みは流用しない。

2回fitは2本の小さい木という意味ではない。multiclass HGBはclassごとに木を持つため、実際の木数・RAM・CPU時間を別に記録する。[E2]

温度較正はsoftmax出力p_jに対してp'_j proportional to p_j^(1/T)、TをCALのmulticlass log lossで推定する。各推定器のclassの和を1に保ち、q_kは同じ条件付き分布の累積和から得る。V1の独立累積headをmin-envelopeで整える方式とは別identity。基礎推定器FITとCALを分ける必要がある。[E3]

同じCALで学習した較正曲線を独立な精度証明にしない。VALIDATION/FINAL REPORTでBrier/log loss/事前固定bin/採用領域のsupportを測る。較正に通れば予測品質が高い、とは扱わない。

工学障害は停止原因と試行台帳を保存する。結果を見た教師変更や窓変更を『バグ修正だから同じcandidate』と扱わない。変更が予測に影響するなら別の事前承認と試行identityが必要。多くの設定を試すこと自体がバックテストの過適合を招き得る点を実験台帳で管理する。[E4]

## 11. 評価: 層で除外した機会まで数える

### 11.1 層別に検査する

固定FINAL REPORTでは、モデル・全監視候補を先に固定してから各層の結果を評価する。除外集合の教師は監査用で、同じFINAL REPORTのゲート調整へ戻さない。

各層でeligible/pass/reject/WAIT/UNKNOWN、raw Winner1/3/5の残存数、Clean Winner1/3/5の残存数、raw Loser3/5の除外数を出す。

- Gate retention_k = G2まで残ったClean Winner_k / G0母集団のClean Winner_k。
- Model capture_k = 最終選出Clean Winner_k / G2母集団のClean Winner_k。
- End-to-end capture_k = 最終選出Clean Winner_k / G0母集団のClean Winner_k。

分母0はN/A。最初の2層だけで大Winnerをほとんど消しているなら、第3層を何回も学習しても取り戻せない。混在/横ばいを排除する戦略の機会費用を明示する。

### 11.2 候補数を絞るだけの見かけの改善を防ぐ

selectedN、knownN、UNKNOWN、候補0日を残し、raw/Cleanの両方で+1/+2/+3/+4/+5の件数・全選出分母率・known分母率・1営業日当たり件数・1件以上候補を得た日率を表示。-1/-2/-3/-5、Close、最悪日、実約定未測定も併記。

固定Top1/3/5/15 prefixは診断のみで、見てから最良Kを選ばない。ゲート不通過を15件に補充しない。候補1件を当てるだけで高率を出し、他の日の上昇機会を失う設計を無条件にPASSにしない。

比較はV1の不変出力と、同じG2集合からの無作為期待値等の内部検算を補助に使えるが、売買代金上位基準超えを目的にしない。V1が新しい評価期間へ因果的に適用できないときは、古い7日成績を新期間の同条件比較へ流用しない。

### 11.3 品質基準の初期提案

以下は、採用前に所有者と固定する要求水準の案。最適化で発見した閾値や達成済み成績ではない。

- 全選出分母のraw Winner1>=50%。大きな逆行なしのClean Winner3/5は件数と日別供給が必要。
- 全REPORT営業日当たりClean Winner3>=1件、Clean Big Winner5>=0.5件を初期目標案とする。候補0日も分母に含める。
- raw Loser3<=5%、raw Loser5<=1%を初期上限案とする。UNKNOWNで率が薄まらないようknown分母率と欠測率も必須。
- これらの点推定だけでは品質認証しない。日をclusterとし、連続日の依存を考慮した固定5営業日block bootstrap、地合い別・流動性別・時期別のsupportを出す。稀な-5%について数値的証拠が足りなければNOT_CERTIFIED。
- 校正済み予測p3/p5の上限と、実測Loser率の上限は別検査。40日REPORTでも真の1%tailを認証できるとは仮定しない。
- 表面的な的中率が高くても、ゲートの機会喪失・日別供給・採用領域の較正が不十分なら、総合品質合格にはしない。

最終的な許容損失・必要機会数はユーザーの要求で決める。評価結果に合わせて要求水準を引き下げない。パラメータの採用承認前はmarket_fit_allowed=falseを維持する。

## 12. 実装順序と受入条件

1. メタデータのみのデータ利用/露出/期間allowlist照合。日時を決めずに全5年をfitしない。
2. G0/G1/G2と教師計算の純粋関数、人工境界テスト、層別理由台帳を実装する。まだ市場fit0。
3. 承認したDevelopment範囲でゲート後の母集団規模・FIT/CALのclass support・特徴の意味/欠測を確認する。FINAL REPORTラベルは開かない。
4. ルール、数値条件、特徴量profile、period allowlist、モデル設定、candidate budget、品質基準を実行precommitに固定する。
5. 1candidateの2推定器fit・2較正。全工程のcode/schema/source/hash、依存ライブラリ、RAM/時間、試行台帳を保存。
6. VALIDATIONで一度評価。失敗ならFAIL保存、FINAL REPORT未開封のまま停止。成績に合わせた同一candidate内の調整はしない。
7. 同一モデルを信頼済みhashから再ロードし、FINAL REPORTの監視候補を全て固定してから評価。第三者監査でないものはそう明記。
8. 研究実装完了、予測品質判定、RSS入力供給、Entry/EXIT/Capital、実運用認証を分離して引き渡す。

## 13. 必須テスト（実装時、今回未実行）

- 全軸下降/横ばいREJECT、混在WAIT、全UPでも暴落ならREJECT、完全なMA並び順は要求しない。
- MA75傾きの76営業日境界、等号と小数、未来足を毒化しても当該日のgate/featureが不変。
- 株式分割・価格basis不明を暴落ラベルへ誤分類しない。翌日の暴落は過去gateへ入らない。
- -5%/3ATRの境界、ATR分母からtを除く、volume/turnoverの単位・欠測・一時スパイク。
- 第3層の学習集合と予測集合に同一Gを適用。失敗例がRisk教師に残る。R0条件付きOpportunityにも不上昇例が残る。
- UNKNOWN教師のmask、3class/6class整合、q1>=q2>=...>=q5、p5<=p3、0<=q_k<=P(R0)<=1。
- 条件付き重みは元の1/N_dを保持。CALはFITと別、FINAL REPORTのdescriptorはFIT/CAL processへ渡さない。
- 2024-11-05前後のザラバ窓同義性、auction分離、同時刻Tickのidentity保持、足内先後はAMBIGUOUS。
- 0～15件・同点規則・寄り後差し替え禁止、空候補receipt、変更された候補hash拒否。
- V1/Frozenのbyte hash不変、V2から注文/Excel/口座writeに到達する経路なし。

## 14. 今回の実施範囲

行ったこと: V1のGitHub PR/有効precommit/データsplitと保存範囲metadata/Tick計算基準を読取り、公式資料を参照し、新V2の設計書を独立branchへ追加。
行っていないこと: V2コード実装、モデルload、private原本の数値開封、ゲート実測、FIT/CAL/VALIDATION/REPORT、市場provider要求、V1/Frozen変更、実注文、paper、実機RSS接続、自動昇格。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
productionReady=false
entryAllowed=false
market_fit_allowed=false
implementation_started=false
parameters_adopted=false
new_period_allowlist_approved=false
main_merge=0
force_push=0
provider_new_acquisition_requests=0

## 15. 根拠と提案の区別

[S1] V1のGitHub実測資料: PR #593、WORK_HANDOFF_MA4_20261014-ja.md、MODEL_AND_INPUT_MANIFEST_PUBLIC.json、REPORT_AGGREGATE.json。参照HEADは本書0節の値。文書内の歴史的『未fit』状態と最新の完了状態を区別する。
[S2] 同HEAD research/independent-long-selector-20261012-v1/SESSION_SPLIT_SUMMARY.json。76/57/47 identity、元seal、完成30/10/7の追記を参照。
[S3] 同HEAD research/independent-long-selector-20261012-v1/GITHUB_DATA_SOURCES.json。保存期間のmetadataであり、現在の利用権や新期間開封の承認ではない。
[S4] 同HEAD research/independent-long-selector-20261012-v1/preopen_history_features.py のprior_tick_features: auction_close基準。
[S5] 同HEAD MA4_EFFECTIVE_PRECOMMIT_20261013_V2.json、EFFECTIVE_FEATURE_POLICY.json。MA4等の既存ユーザー方針。

[E1] JPX『JPXマンスリー・ヘッドライン 2024年11月』: https://www.jpx.co.jp/corporate/news/monthly-headline/202411.html （2026-10-14参照）。2024-11-05の制度変更と15:25～15:30非約定時間。
[E2] scikit-learn 1.8 HistGradientBoostingClassifier公式仕様: https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html （2026-10-14参照）。multiclass log loss/softmax、classごとの木。既存環境を自動upgradeする意味ではない。
[E3] scikit-learn公式Probability calibration: https://scikit-learn.org/stable/modules/calibration.html （2026-10-14参照）。基礎fitとcalibrationの分離。温度較正の具体的実装と依存版はV2の工学契約で固定する。
[E4] Bailey, Borwein, Lopez de Prado, Zhu, The Probability of Backtest Overfitting (2015): https://papers.ssrn.com/abstract=2326253 （2026-10-14参照）。本書の3層gateや数値閾値の有効性を証明する文献ではない。

**3層構造、具体的なUP定義、暴落/容量の数値案、条件付き2推定器、Score、120/20/20/40日、品質目標は本書の新しい設計提案であり、上記資料がV2の利益や優位性を実証したわけではない。**
