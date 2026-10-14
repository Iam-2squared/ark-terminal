# 新Selector V2 R1 — 工学契約

文書ID: ARK_SELECTOR_V2_WORK_DETAILED_DESIGN_20261014_R1
設計対象: ARK_PREOPEN_V2_TREND_CONTINUATION_CASCADE
実行範囲: MODE A / DESIGN_AND_ENGINEERING
到達点: ENGINEERING_READY / AWAITING_MARKET_APPROVAL

このrevisionは2026-10-14 JSTのowner指示を工学実装へ分解した単一案である。
parameters_adopted=false、market_numeric_read_allowed=false、market_fit_allowed=false。
市場研究の予算はcandidate0 / base fit0 / calibration0。人工試験のfitと分離する。
コード完成・人工試験成功は市場の予測品質、損失確率、流動性、実行能力の証拠ではない。

## 1. identityと保護範囲

最新確認した設計HEADは4b02c4eb6fed0b75bfc7a6e8afc49d7868696159。
V1 PR #593はOpen/Draft、HEAD55085fa4f4487cea8dcb30ee2a1c3e668f691da6。
V1/Frozen/main/PR #591、原本、A～E保存先、口座、Excelを変更しない。
V1直下Pythonは追加も禁止。全treeの許可外entry hashとV1直下全Python hashを比較する。
保護refの開始値と旧設計SHAはPROTECTED_SURFACE_BASELINE.jsonに保存した。
既存V2_DESIGN-ja.mdは変更せず、history/にbyte単位の同一コピーを保存した。
今回の追加精密化A1～A10はDESIGN_DELTA.jsonに分離する。
既存MA4_EFFECTIVE_PRECOMMIT_20261013_V2はV1内部改訂であり、ここでのV2とは別identity。

書込はこのdirectoryと新規専用workflowだけ。実装branchは別に作成し、
Draft PRの直接baseはV2設計branch。merge、Ready化、自動merge、force pushを行わない。

## 2. 時点・入力・正当なUNKNOWN

Dは公式exchange calendarの選出日、tは直前営業日。暦日から1日引かない。
主キー(session,canonical_symbol,market)。4文字英数字canonicalとRSS表記は別。
dated master・種別rule versionで国内普通株・Prime/Standard/Growth・現物100株を確認する。
末尾文字でETF等を判定しない。現在存続している銘柄だけを過去へ戻さない。

入力cutoffはDの08:50 JST。event/published/available/capturedを区別する。
SourceEvidenceの全18欄を必須型として固定し、available_atの最大値をfeatureへ継承する。
実受信、SCHEDULE_ASSUMED、SYNTHETICを別扱いにする。EOD保存時刻を場中受信へ戻さない。
RAW価格JPY、volume SHARES、turnover JPY。混在basis、不明units、不整合hashは停止。
将来訂正、当日OHLC/State、label/outcomeを入力やwatchlistへ混入させない。

全OHLC nullは検証済みNO_TRADE等のUNKNOWNとして扱う。部分null、bool、NaN/Infinity、
非正価格、H<max(O,C)、L>min(O,C)はDATA_INTEGRITY_ERROR。壊れた行を黙って捨てない。
masterやcalendar全体の欠落はDATA_BLOCKED。正しく0件ならNO_CANDIDATE。
分割等は比較可能RAW suffixを切り、境界以前を使わず履歴不足UNKNOWNにする。
未来調整係数、最新adjusted close、future interpolationを使わない。

## 3. G0/G1/G2

母集団はU_master→U_price(C_t>75)→U_G0→U_G1→U_G2→U_prob→S_final。
G0は77営業日の連続・比較可能RAW closesとTR用OHLC、必要activityを検査する。
追加任意特徴の履歴不足は当該列Noneであり、gateを緩めない。

S_n(t)=sum(C_(t-j),j=0..n-1)/n、n=5/15/25/75。
Delta_n=S_n(t)-S_n(t-1)=(C_t-C_(t-n))/n。
UP_n=[Delta_n>0] AND [C_t>S_n]。長UP=UP75、中UP=UP25 AND UP15、短UP=UP5。
全3軸UPだけPASS。0軸UPはREJECT、1～2軸UPはWAIT、必要履歴不明はUNKNOWN。
等号はUPではない。S5>S15>S25>S75の完全順序は条件にしない。
Fractionで平均差と端点差を独立検算し、float/表示丸め/epsilonで符号を変えない。
これはn日間ずっと上昇した証明ではなく、上昇継続型への戦略上の適用限定である。

r_cc=100*(C_t/C_(t-1)-1)、r_body=100*(C_t/O_t-1)、r_gap=100*(O_t/C_(t-1)-1)。
いずれか<=-5%、またはmax(0,C_(t-1)-C_t)>=3*ATR_preなら損傷除外。
ATR_preはt-75..t-1の75 TR。TR=max(H-L,|H-prevC|,|L-prevC|)。
最初14 TRの平均seed、後続61 TRを(13*ATR+TR)/14更新。暴落当日tを含めない。
最初TRのprevC=t-76を要するので77 closes。定常無限履歴Wilderと同一とは主張しない。
ATR=0・下落0はz=0、ATR=0・正下落はATR_ZERO_WITH_POSITIVE_DROPで除外、z=None。
負ATRはERROR。小陰線は単独の新除外にしない。gap=-5%から回復してもGAP_DAMAGE。

参照cashは1,000,000 JPY、B20=min(Va_t,median(Va_(t-19)..Va_t))。
B20>0かつ100*A_ref<=B20、100*C_t<=A_ref。中央値は20営業日、偶数中央2値の平均。
0は確認済み実際の0、source未接続はNone。単日急増で通常容量不足を隠さない。
first reason順はDATA_ERROR→UNKNOWN→PRICE/LOT→CC→BODY→GAP→ATR→CAPACITY。
all reasonsとfirst reasonの両方を保存する。
板厚・spread・拘束額・impact・全量約定を認証するgateではない。

## 4. 教師と2推定器

LABEL_CONTRACT.jsonのRAW・同市場・全session教師だけを使用する。
U=100*(H_D/O_D-1)、A=100*(1-L_D/O_D)、Cret=100*(C_D/O_D-1)。
Oは実際の初回約定。09:00寄りや最初取得価格への代替を捏造しない。
B0..B5は[0,1),[1,2),[2,3),[3,4),[4,5),[5,∞)。
R0=A<3、R1=3<=A<5、R2=A>=5。厳密cross multiplicationで計数する。
rawWinner_k=[U>=k]、rawLoser_j=[A>=j]、cleanWinner_k=[U>=k AND A<3]。
utility=sum(cleanWinner1..5)。R0/B0も効用0の学習行として残す。
R0はSAFEではない。High/Low順序、約定利益、瞬間Highの持続は日足から推定しない。

RiskはG2通過known全行の3class、OpportunityはそのR0 subsetの6class。
R1/R2負例はRiskから消さない。Gで除外した行やTop15だけの学習を行わない。
a_r=P(R=r|X,G,K=1)、b_b=P(B=b|X,G,K=1,R=0)。
q_k=a0*sum(b_k..b5)、p3=a1+a2、p5=a2。
独立性の仮定による積ではなく条件付き分解。二つの近似推定器の積の校正は保証しない。
q/pは教師観測known条件付き。UNKNOWNを隠さず全出力conditionalOnOutcomeKnown=true。
確率和・包含の許容はfloat64絶対1e-12。選出閾値にはこの許容を転用しない。
classes_で0..2/0..5の順序を検証し、未確認配列位置を使わない。

## 5. 重み・列・学習・較正

Ndはlabelを見る前の全G2件数。known集合でc=knownN/sum(1/Nd)を1回計算。
Risk weight=c/Nd、Opportunityにも同じ重みを継承。CALは別共通c。
R0日数による再均等化、class_weight、SMOTE、Winner複製を行わない。
float64/native NaN。各推定器のFITだけで全欠測/定数列を除外し、別used-column hash。
CAL/FINALで列を選び直さない。FIT観測/CAL全欠測ならfit0でsupport shift停止。

学習器は2本のHistGradientBoostingClassifier、固定設定はPARAM_PROPOSAL/model.pyで照合する。
lr=.05、leaves15、iter120、minleaf40、L2=10、bins255、max_features1、seed20261014。
early_stopping=false、warm_start=false、categorical_features=None、class_weight=None。
120*(3+6)=1080 treesを実際の内部tree数と照合する。CPU/threads1、依存は固定lock。
全class support、CAL入力support、schema、メモリを最初のfit前に検査する。

各モデル温度1個。z=log(max(p,1e-15))、softmax(beta*z)、beta∈[.05,20]。
CAL共通weightのmulticlass NLLをbounded一次元optimizerで最小化する。
maxiter200/xatol1e-8。固定3点の平坦性検査を含む全目的関数評価数を記録する。
非有限、非収束、平坦、bound付近(距離1e-6)はCALIBRATION_REVIEW_REQUIRED。
bound距離1e-6は数値収束の工学guard提案で、採用済み市場閾値とはしない。
T=1 fallback、追加estimator fit、他方式比較、qの事後fitを行わない。
MODE Aの動作する学習wrapperは固定factory入力だけ。realをSYNTHETICへ付け替えても
factory再生成fingerprint照合で拒否する。市場入力でsyntheticモデルを使うことも拒否する。

## 6. V2_CORE95

名称・順序・算式・units・source route・lookback・式versionはFEATURE_REGISTRY.json。
A:MA20、B:価格25、C:容量6、D:分足12、E:市場8、F:企業8、G:Tick7、H:State9、合計95。
日次独立MA期間は5/15/25/75。MACD内部12/26/9は独立MA列ではない。
EMA/MACDは直近比較可能150 closes、先頭n SMA seed。signalは最初9有効MACD平均。
RSIは直近75リターン、先頭14上げ/下げ平均seed。上げ下げ0=50、下げ0=100、上げ0=0。
SMA75 slopeHには90 closes、up_fraction3には78 closesが必要でgate77と区別する。
過去高安の基準はtを除く。未来pivot、centered rolling、ZigZagを使わない。
source未接続はNone/理由付き。profileを削減した別candidateに自動fallbackしない。

前日分足はauctionとcontinuousを分離。参照価格は参照時刻までの観測だけ。
1M closeの実約定時刻は捏造せず[start,end]のage区間の古い側<=300秒で検査する。
午後efficiencyはcontinuous_endまで確定した最後の1分連続segmentだけ、2足未満はNone。
H=L足をclose_location平均から除き有効Nを残す。欠落と確認済み無約定を分ける。
Tickは時間→source ordinal順。TransactionId/ordinalを保持、同時刻同価格同量をdedupeしない。
集約record countを個別注文数と呼ばない。窓完全性と受信した一部を区別する。
完全窓・0取引ならcount/volume=0、VWAP/return等None。障害ならcountもNone。

continuous_endは2024-11-01以前15:00、11-05以後15:25。auctionは15:00/15:30。
後者15:25～15:30は非約定受付。Tick窓[start,end)、auctionを除く。
工学窓1/5/15/30/60を検査し、主profileへは30だけを登録する。
RSS最大300本の表示は前日全Tick保存の証明にならない。今回RSS/Excel実機は操作しない。

peerはdated masterで固定、known/expectedを保存しcoverage<90%で該当context None。
財務は年度/四半期・連結・通貨・units・前年同期間を照合、同時刻別文書は曖昧ならNone。
訂正を元公表日に戻さない。valuation更新時刻とROE比率→%を明示する。
Stateはformal observedだけone-hot。非観測をRANGE/carryへ補完しない。
市場Stateを接続する前に既存RC2 rules/profile/normalizerの正確なhashをowner-approved
source routeへ束ねる。未確認Dictionary、上流の新fit、後日のlineageを使わない。

## 7. 選出・評価

q1>=.50、p3<=.05、p5<=.01。比較は表示前finite float64、等号PASS、穴埋めなし。
Score=sum(q1..q5)、Score降順→q5降順→canonical昇順、最大15、0件を許す。
Scoreはclean到達1%段階数の期待効用であり、連続リターン・費用後EVではない。
unknown labelの判明後に差し替えない。input/model/schema/hash driftは再fitで回復しない。

評価は6上昇bucket/exact0内数/UNKNOWN、raw/clean1..5、Low1/2/3/5、Close signed1%。
known率、全選出下限率、LoserのUNKNOWN最悪上限率を分ける。0/0はNone/N/A。
候補0日も全calendar営業日分母に残す。候補日率・Winner日率・日別tail/集中を残す。
GateRetention/ModelCapture/EndToEndCapture(k1/3/5)の分母集合を固定し、分母0=N/A。
G0以前の機会損失、排他的first reasonと重複all reasonsの除外機会を別表にする。
Top1/3/5/15は固定診断であり、最良Kへ変更しない。
path補助は確認済み経路のみ。同足上下hitはAMBIGUOUS、参照足の過去Highを再利用しない。

点目標案: raw1全選出下限>=50%、clean3>=1件/日、clean5>=.5件/日、
Low3最悪上限<=5%、Low5<=1%、UNKNOWN<=1%。候補日率は診断のまま固定する案。
VALIDATION全条件成立だけFINAL開封へ進める。不達FAIL/不能NOT_ESTABLISHEDでは未開封停止。
40日でclean3>=40、clean5>=20でも真の1%tail/将来利益を自動認証しない。
営業日cluster/circular moving block5日/draws5000/seed20261014、2.5/97.5記述区間。
分母0 draw数を残し0へ置換しない。観測Loser0の[0,0]を真のrisk0とはしない。
Risk NLL/R0 Opportunity NLL/q/p Brier/NLL、固定q10bin/risk7binをraw/較正後で診断する。
G2 known全体と選出known、weighted対象とunweighted選出を混同しない。
small binはINSUFFICIENT_SUPPORT。CAL自身の改善を独立証明と呼ばない。
V1再fit、旧7日と新40日の件数差を改善差と呼ぶことを禁止する。

## 8. 市場実行前の必須停止条件

MODE BにはV2用途、reuse根拠、正確なFIT/CAL/reference allowlistsのowner承認が必要。
MODE Cには全200営業日、source/権利/露出manifest、数値/95列/教師/品質/依存hash、
candidate1 / fit2 / calibration2を束ねた実行precommitとowner原文承認が必要。
JSONへtrueを書くだけでは無効。独立control planeにpinされたowner原文・親承認・
precommit hash、日時、用途、manifest、candidate identityを検証する。現在pinsは空。

期間案120 FIT / 20 CAL / 20 VALIDATION / 40 FINAL。最大150 reference sessionsを別用途へ。
metadataで連続windowを列挙し承認範囲の最も後ろを一つ選ぶ。protected gapを飛ばさない。
V1の47日/旧4日history例外/既露出7日を新V2へ移転しない。
保存coverageと用途承認は別。現時点のV2許可0日、200日分の正式承認が不足している。
正確な200日windowはNOT_ESTABLISHED、架空の日付や許可を埋めない。
露出は新コピーでFreshに戻らない。後続日の因果的history参照とteacher開封を区別する。

FIT known>=5000、R0>=3000、各class100行/10日/20銘柄。
CAL各class20行/5日/10銘柄。G2後UNKNOWN率<=1%。
不足classを統合、複製、別期間追加しない。CAL成績で閾値を選ばない。
FIT oracle Upper_k=sum(min(15,cleanWinner_k日件数))/全FIT日数。
Upper3<1、Upper5<.5ならfit0停止。上回っても達成可能性の証明ではない。
class/schema/CAL観測shift/sourcehash/メモリ/教師成熟・時系列境界を最初のfit前に検査する。

## 9. 実行分離・台帳・保存・公開

state machineはadmission.pyの単方向遷移。MODE AからFITへ飛び越さない。
VALIDATION失敗後はFINALへ進めない。承認を自己生成しない。
実験台帳は排他的予約・hash chain・START記録。開始したfitは失敗しても予算消費。
run directoryはexist_ok=False、再試行・台帳削除・既存成果上書きなし。
synthetic E2Eも学習/forecast/evaluationをspawn別processにし、
forecastへlabel descriptorを渡さず、全watchlist保存後だけ評価processを起動する。
市場研究では20/40日をそれぞれ全固定→開封、同一モデル維持・再fit0。
追加学習、列/重み/seed/教師/phase/期間変更は新candidate設計承認へ戻る。

保存はtemp→fsync→atomic no-replace publication。通常renameによる上書きを避ける。
restoreは全entry hash/サイズ/重複/path traversal/symlinkを先に検査する。
未信頼pickleはhash一致だけでloadしない。自作producerの独立receipt pinが必要。
MODE Aは自作synthetic artifactだけをproducer→親control plane→別forecastへ渡す。
市場モデル/原本/行/候補/小セルは公開しない。publicはコード・契約・hash・非復元receipt。
small cellが他セルとの差から復元できるpartitionは全体とtotalを抑制する。
全11 execution/entry/production flagsはheader/itemともfalse。欠落もERROR。
orders/paper/provider new requests/main merge/force pushは0。

## 10. CLIと受入証跡

metadata-audit / synthetic-test / census / train / calibrate / predict /
evaluate / restore-verify / public-auditを登録した。bypass flagを作らない。
MODE Aの外部census/train/calibrate/predict/evaluate/restore-verifyはrequestファイルを
開く前にAWAITING_MARKET_APPROVAL。自作restoreはsynthetic-testで実行する。
権限のない市場source adapter/モデルtrust control-planeを勝手に接続しない。
metadata-auditはmetadata専用schema、日付/用途/サイズ/hash/rights referenceだけを扱う。
metadata申告をowner承認済みとは出力しない。

専用CIはV2 branch pushとV2設計baseのDraft PRだけ、contents:read、
persist-credentials:false、原本/Secretsなし。V1のfixture/期待値を編集しない。
Python cache/typecheck cacheはcheckout外へ置く。syntax/type/V2試験/V1回帰/E2E/保護監査を実行。
受入は最新HEADの専用run、event、job、decoded logへ結合する。別workflow成功は流用しない。

## 11. 根拠・未確認事項

数値・95列・gate・2モデル・期間・目標はowner提示の採用前案。実測優位性は未証明。
公式仕様の参照(2026-10-14): JPX
https://www.jpx.co.jp/corporate/news/monthly-headline/202411.html
HGB API
https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html
calibration
https://scikit-learn.org/1.8/modules/calibration.html
RSS仕様は添付公式機能一覧のRssTickList表示1～300と照合。
これらは取引時間/APIの根拠であり、本候補の利益や統計品質の証明ではない。
市場gate計測、teacher support、fit/CAL/VALIDATION/FINAL、daily live parityは未実施。
CURRENT_STATUS、METADATA_AUDIT、BLOCKERS_AND_NEXT_ACTIONとWORK_COMPLETIONで区別する。
