# 🚀 Ark Terminal — Capital V5.1 一括Work指示書
## 評価器修正 → V5再baseline → R5/R10診断 → 最大1候補のV5.1 → 最終資産比較

文書ID: ARK_CAPITAL_V51_RESET20_R5R10_WORK_V1_20261006
作成実時計JST: 2026-10-06T00:28:30+09:00
状態: WORK_INSTRUCTION_READY / この指示書による実験は未実行
Repository: Iam-2squared/ark-terminal
継続先branch: capital-main-reallocation-20261005
作成時actual GETで確認したHEAD: a35399fc27dd8cc67751aadd21d690ba92aefe5b

## 0. 🎯 依頼・到達目標・今回の権限

この指示書に従い、次の作業を同じWork内でまとめて実施してください。

「有限のsession coverage監査」と「100万円reset評価器」を整え、Frozen V5を再測定する。
同時に、既存のEntry→High U5/U10を保持したまま、Entry→固定EXIT・約定契約の費用込みreturnによるR5/R10を評価専用として追加する。
既存scoreとV5の資金・数量・枠の流れを診断し、条件が整えばCapital変更を最大1候補に絞って事前固定・実装・評価する。
最遠の到達点は、同一reset評価器によるV5対V5.1の最終資産比較・独立会計検算・GitHub保存まで。

工程が区切れただけでSTOPしたり、通常の実装・import・保存・テスト修復で逐次承認を求めたりしない。
ただし、根拠不足を埋めてV5.1を必ず作る指示ではない。未決事項を勝手に「既に固定済み」と見なさない。
対象外のモデル学習・上流戦略変更・新データ購入・保護期間開封・実売買には進まない。

本書は最新のユーザー合意を具体化した新しい作業範囲である。以下の運用条件・status・予算は本書で定めるもので、過去研究が承認・達成済みの条件ではない。
旧NEXT_WORKのread-only限定、旧「slot intelligenceだけ」、旧「U5 miss全件を最初から再分解」は、この作業範囲に置き換える。旧結果そのものは上書きしない。
本書の作成・保存と、Workによる実験開始・完了は別に記録する。

最上位目的:
    初期cash 1,000,000円・保有0 → 20 sessions → 最終資産を約2,000,000円へ近づける。
中心となる比較量は20-session最終資産の中央値。平均・最小・最大・2倍到達数/率も必ず併記する。
R5/R10、U5/U10、AUC、Loser件数、利用率が改善しても、最終資産が改善しなければCapital改善とはしない。

### 今回対応する問題

| 問題 | このWorkの対応 |
|---|---|
| P0: 月次目的と評価器の不一致 | session coverageと毎窓100万円resetを直す |
| P1: 損失取引へ資金を投入しすぎる | Loserへの投下額・損益・拘束を調べる |
| P2: 固定戦略で利益化する候補を取り逃す | R5/R10の存在数・購入/非購入・阻害条件を調べる |
| P3: 利益になる取引へ十分配分できない | 購入可否から整数数量までの接続を修正候補にする |

P1～P3は同じCapital問題として扱う。ただし新candidateでは主要な変更機構を1つに絞る。
「R5予測モデルの新規学習」を先に始めるのではなく、ラベル整合性・V5の捕捉状況・既存scoreの分離情報を先に確認する。

## 1. 🔒 変更しないもの／変更できるもの

完全凍結: Selector・Entry・EXITのmodel、feature定義、閾値、ルール、対象選定、時刻、identity。
旧V5のpolicy・code・結果も比較原本として読み取り専用にする。V5.1は別ID・別ファイルで実装する。

| 項目 | 固定する内容 |
|---|---|
| 売買制約 | LONG現物cash-only、MAX3、100株単位。借入・信用・SHORT・追加資金なし |
| 約定・費用 | 正本のBUY/SELL、価格source、利用可能時刻、EOD処理、Entry cutoffを継承 |
| 保有後 | 早売り・部分売却・置換売却・買い増しを追加しない |
| Entry機会 | 過去に見送ったEntryを復活させない。新たな再Entryルールを作らない |
| 凍結Expert | pP/MOVE_P5、MOVE_U2、MOVE_U3、MRETの既存score・model・参照分布を保持 |
| データ | 既存の許可済みDevelopmentのみ。未確定到着時刻をverifiedへ格上げしない |
| 過去の負の結果 | V4 cutoff、V9 I1/I2、V11R1 M1/M2、最新Reserve閉鎖を保持 |

変更候補にできるのはCapital内部の「購入可否と数量の接続」「target budget」「Capitalの配分cap」「初回/追加lot配分」のうち、診断で根拠が得られた主要機構。
Capital内部のcapは変更候補にできるが、MAX3・最低lot・cash上限・流動性/約定制約は緩めない。
単に旧Reserveを緩める、4LOWを3LOW/ORにする、S_ONLYを再試行する、といった閉鎖済み案の焼き直しは禁止。

今回の独立reset評価は、新しい初期条件の測定である。旧指示の「V5再Replay不要」は、同じ旧38-session chainの無目的な再実行を避ける趣旨として扱い、今回必要なreset評価を禁止する条件にしない。

## 2. 📚 原本確認と重複回避 — 最初に一度だけ

開始時にbranchの最新HEAD・既存の作業記録をactual GETし、同じWorkが既に実行されていれば結果をreuseして未完了部分から再開する。
以下の保存先を起点に必要ファイルだけ回収する。repo全履歴・全実験の再監査は行わない。

A. 最新引き継ぎ・方針:
    docs/evidence/capital-main-reallocation-20261005-v1/
    checkpoints/P1_HANDOFF_COMPLETE.json
    HANDOFF_REPORT-ja.md
    NEXT_WORK-ja.md
    SOURCE_BINDING_CHECK.json
    WORK_STATUS_LOG.jsonl

B. V5正本:
    commit 710656491be06235901b45c50a8b5cbd714ba4eb
    research/capital-v5-max3-slot-intelligence-20261004-v1/
    docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/
    replay.py、execution.py、allocation.py、slot_policy.py、ARRIVAL_TABLE.json等。

C. 正式入力binding・閉鎖:
    commit 220e0d8863978f5d82d0d83189d473252efda146
    docs/evidence/capital-v5-reserve-past-qualified-20261005-v1/INPUT_BINDING.json
    同directoryのCLOSURE.json

D. 添付pack:
    Ark_Terminal_NEW_CHAT_HANDOFF_MAIN_CAPITAL_2X_20261005(1).zip
    Ark_Capital_v9_Quality_Aware_MAX3_Integration_20261005_PRIVATE(1).zip
    Ark_Capital_v11R1_Numeric_Cert_Recovery_20261005_PRIVATE(1).zip
    同内容のnested packがあれば重複展開・再取得をしない。

過去の/workspace/scratch/...は所在ヒントであり、現環境に存在するパスとして使わない。
manifestから現実のローカルpath・member・hash・列・単位を解決する。存在しないファイル名や列を推測しない。
既に認証された同一内容のmodel/OFF/AUC/元bootstrapをやり直さない。差分の入力bindingと新しい評価経路だけ検証する。
V11のI2参照値にある既知の出典差は、今回再利用しないなら再調査で時間を使わない。

### 凍結authorityの照合起点

Selector: FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75
Selector freeze commit: 06e19ef9cd4fca99840487404ccb38a182b9bd2f
Entry freeze: 4a2d6f35946b16820a13449a9288a6685a5c283c
EXIT v3: c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad
EXIT正式receipt: 1ecbcc43f75279fa302f19fd896add2aac15b537

参照元はP1_HANDOFF_COMPLETE.json。より新しい記録があれば、その正当な継承関係を確認する。別戦略へ勝手に切り替えない。

## 3. 📅 Session Coverage Audit — 欠落を0%で埋めない

前チャットからの受領事項:
    all58はCORE_RUNTIME_CAUSALに存在するsessionの集合から生成。
    先頭20をwarmup、残り38をOOF評価。
    2025-07-11・2025-07-14がruntime/session universeに存在しない理由は未証明。

照合用hash（受領値。Work内で実物と照合してからverifiedとする）:
    CORE_RUNTIME_CAUSAL.jsonl.gz:
    827abcf716c9203a70bc766783948a6be3cee3428abf6a772d1c3495096fd197
    SESSION_SPLIT.json:
    e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274

作業は既存の対象期間と当該2日を中心に限定する。
保存済み市場calendar → source取得/coverage → 上流処理完了receipt → runtime生成/除外 → splitの順に辿り、各日を分類する。
calendarは価格・Entry行の有無から逆算しない。必要な営業日確認だけは公式calendarの照会可。新しい市場価格取得・有料API取得は不可。

| status | 証拠と取扱い |
|---|---|
| MARKET_CLOSED | calendarの根拠あり。営業日として数えない |
| COMPLETE_ZERO_ENTRY | 上流入力/処理が完全で、凍結Entryが0件と証明。評価日は残し、cashを維持 |
| COMPLETE_WITH_CANDIDATES | 正当な固定候補stream・時点情報・実行sourceがある |
| SOURCE_MISSING | 入力source不足が証明された |
| PIPELINE_OMISSION | sourceはあるが処理・出力欠落が証明された |
| UNKNOWN_REASON | 理由未証明。無取引・0%・休場とはしない |

「runtimeに行がない」だけではCOMPLETE_ZERO_ENTRYとしない。Entry0がV5のfunded0を意味するだけなのか、上流全候補0なのかも区別する。
既存の欠けていたartifactを発見した場合は、その同一性・時点・利用権を検証して別版manifestへ回収してよい。
新しい上流候補の再生成・再学習が必要なら、その工程は本書の自動実行対象外。欠落原本と必要範囲を明示し、他の作業を続ける。
calendar上の空白をまたいで「次に存在する20日」を20連続営業日と呼ばない。

旧all58/warmup20/OOF38・8 blockの学習分割は上書きしない。calendarを補った後に先頭20を取り直し、model割当やtraining時点まで変えてはいけない。

調査済みpath・結論・不足原本を一度記録したら、同じ検索を反復しない。理由未解決でも、評価器実装・ラベル契約・既知範囲の診断は並行継続する。

## 4. 💴 RESET20評価器 — 戦略ではなく評価条件を正す

### 4.1 結果の種類を分ける

| モード | 内容 | 位置付け |
|---|---|---|
| LEGACY_NORMALIZED20 | 保存38-session chainの区間倍率を100万円へ換算 | 旧比較値。再計算不要 |
| RESET20_CASH1M | 各windowを本当にcash100万円・保有0から再生 | 新評価器 |

RESET20の各windowにcalendar_contiguous、coverage_complete、execution_completeを別々に記録する。
主評価のwindow manifestは、元OOF評価範囲に対応する正規のcalendarから、20営業日が期間内に収まる全開始日を機械的に列挙して、candidate損益を見る前に固定する。
coverage不明を含むwindowも予定母集団から消さず、BLOCKED_COVERAGEとして残す。

旧38評価sessionをそのまま使うreset結果が必要な場合だけ、SELECTED_SESSION_DIAGNOSTICとして別表示してよい。gapをまたぐ結果を月次Primaryへ昇格しない。
同じ20日列の計算はモード表示が違っても1回だけreuseする。

### 4.2 Reset対象と、resetしないもの

各window開始時:
    cash = Decimal('1000000')
    positions = {}
    pending orders / fills / intents = empty
    portfolio由来の予約資金・cash recycler・拘束・履歴・累計 = 初期状態

window内は複利連結する。毎日100万円へresetしない。
前windowのcash・数量・decision ledgerを流用せず、現windowの残高で各BUYの整数数量を再計算する。

resetしないもの:
    当該時点で利用可能だった凍結市場履歴・model・score・reference・ARRIVAL_TABLE。
    正式な日付別/block別のモデル適用と、過去だけから作った参照分布。

つまり「口座を新規開始する」のであって、特徴量のwarmupを消したり、評価期間末のmodelを期間初日に配ったりしない。
時間とともに適用modelが変わる既存scheduleは、その当時の固定scheduleを継承する。

### 4.3 既存engineを最小wrapperで使う

V5 day_replay等の保存された核を読み取り専用で再利用し、window orchestration・明示calendar・reset・結果保存を外側へ追加する。
元run_profileのように候補行から日付を作るだけでは、真の候補0営業日を消すため、windowの明示session列を走査する。
時刻順、同batch順序、SELL creditの解放時刻、MTM、MAX3、same-symbol、EODを変更しない。

immutableな価格・book・scoreは共有/caching可。window別のcash・quantity・ordersは共有不可。
保存済みV5 decision/picked/funded数量を、そのまま新windowの正解として入力しない。

### 4.4 終点・未決済・部分結果

全処理完了・全決済なら、final_cashを正式な最終資産とする。
未決済・価格source不足・会計不一致ならfinal_cash_for_primary=nullとし、該当windowを失敗/未測定として保存する。
途中のcash、含み益、最後の既知価格、強制的な0 returnで正式終点を作らない。
window途中で失敗した後の日を100万円から再開して、同windowの続きに合算しない。
他の独立開始windowはその初期条件から評価を続けてよい。

「独立reset」は口座状態の独立を意味する。重複windowが統計的に独立した月次標本になるわけではない。
window数をそのまま独立標本数として通常のCIや有意差を出さない。

### 4.5 最小の評価器検証

人工データで、reset、複利、真の候補0日、gap拒否、100株丸め、MAX3、cash不足、同時刻SELL/BUY、費用二重計上、未決済、window間状態汚染を検査する。
既存V5と完全に同じ初期状態・日付列になる最初の比較可能window/日だけ、保存台帳との一致を確認する。旧38-session全Replayはしない。
実行sourceの変更が必要と分かったら、比較原本を黙って直さず影響範囲をblockする。

V5は同じpolicyで全予定windowを1つのbatchとして再baselineする。
「V5を1回測る」はbatchが1回という意味であり、window/dayの実行回数まで1ではない。両方の件数を記録する。

## 5. 🏷️ U5/U10保持＋R5/R10追加 — ラベルが先、予測モデルは作らない

### 5.1 定義

U5/U10の既存定義・計算期間・価格basis・既存列名は変更しない。
表示上のU5H/U10Hは既存U5/U10へのaliasに限り、別のHighやhorizonで再定義しない。

R5/R10は新しい評価専用の指標として追加する。

    r_net = sell_credit / buy_debit - 1
    R5 = r_net >= 0.05
    R10 = r_net >= 0.10
    Loser = r_net <= 0

境界を含む。保存値がpercentなら5/10、ratioなら0.05/0.10であり、単位を先にbindingする。
表示丸めで分類しない。decimal/rational原本から比較し、ちょうど5%/10%の直前・同値・直後をテストする。
R10はR5の内数。U10はU5の内数。WeakとLoserは重複する。

### 5.2 どのEXITを使うか — 今回固定する実装上の明確化

Capital用R5/R10は、凍結Entryから「現行Capitalが実際に適用する固定EXIT＋既存EOD・約定・費用契約」までのnet returnで定義する。
Structural EXIT v3だけの保存returnと、V5のEODを含む実現returnが違う場合は混ぜない。
前者を別列に残し、Capital用主ラベルは後者にbindingする。EXITのルール変更ではなく、評価ラベルの対象経路の明示である。

各行にexit_policy_hash、exit_kind、price_source、source_minute、available/release時刻、cost_basisを記録する。
intent価格やfuture Highを約定価格にしない。現在V5原本はBUY/SELLに費用係数を含むため、effective価格からさらに同じ費用を引かない。

### 5.3 全候補へのラベル

対象の基本単位はFrozen Entry identity。Capital購入後の150件だけを教師母集団にしない。
全Frozen Entry候補を残し、rank-pass、時刻/価格等の実行適格性、funded、outcome-knownを別maskとして保存する。
Capitalで買えない時刻等の行を「実行可能な取り逃し」に含めない。適格性に将来の勝敗や将来の売却source有無を使わない。

既存の費用込み全候補outcomeが同じ契約なら、その列をreuseして閾値分類だけ追加する。
不足する場合は、保存済みFrozen EXIT event/EOD sourceから、100株referenceのstandaloneラベルを決定論的に1回materializeしてよい。
これはCapital portfolio Replayではない。新EXIT policyやmodelを走らせて教師を作り直す権限ではない。

buy_debit・sell_credit・時点・費用を同じ契約で確定できない行はR5=null/R10=null。falseやLoserへ置換しない。
reference100株は比較用単体ラベルであり、資金制約下で全候補を同時に買えたことを意味しない。
数量によって手数料/価格/約定可否が変わる契約なら、referenceラベルと実funded quantityの実現ラベルを分ける。比例拡大を仮定しない。

正しいR5/R10は将来outcomeを使う。保存先をevaluation-onlyに隔離し、現在の購入判断に直接渡さない。
「過去として参照可能」なラベルは、当該判断以前に売却/必要sourceが確定し、release/knownAtが満たされるものだけ。

## 6. 🔍 診断は必要な差分だけ — 金額・数量・枠を結ぶ

既存のU5/U10 miss表、Weak/Loser表、slot集計はreuseする。旧54件のoracle-feasible U5をゼロから再最適化しない。
追加する中心は、同じ台帳へのR5/R10結合と、resetにより変わった購入数量・cash経路である。

### 6.1 母集団と実績の分離

一意Entryの全候補censusと、windowごとのportfolio実績を分ける。
同じEntryが重複windowに現れた回数を、独立した市場取引機会として合算しない。
旧150件・Loser82・Weak58・U5購入50・U10購入26は旧chainの値であり、reset結果に固定しない。

必須表:
    全候補 / rank-pass / 実行適格 / funded / 非funded のNとknown/unknown。
    net returnの排他的区分: <=0、0超～5%未満、5%以上10%未満、10%以上。
    U5/U10 × R5/R10/Loser の交差表。
    各区分のbuy_debit、net PnL、保有拘束時間、資金×拘束時間。
    R5/R10の購入率、買えなかった理由、window別投入額・利益寄与。

R5未満を一律「悪い候補」にしない。小幅利益・短時間回転も最終資産へ寄与し得る。
株数は同一Entry/銘柄内の配分比較に使う。異なる株価の銘柄の合計株数を資金集中の代用にしない。

### 6.2 PrecisionとRecallの分母

R5 funded precision = fundedかつR5 true / fundedかつR5 known。
R5 capture recall = fundedかつR5 true / 事前固定した実行適格母集団内のR5 true。
R10も同様。全Frozen Entry母集団とrank-pass母集団は別表。
unknown率を必ず併記し、knownの比率を全unknownへ外挿しない。
これはV5の購入集合の品質であり、新しいR5予測モデルのaccuracyではない。

### 6.3 「何を直せば実数量が変わるか」を特定

R5/R10の非購入候補に対して、保存decision時点の以下だけを追加結合する。
    Reserve / MAX3 / cash / minimum lot / band cap / target / 同batch競合 / cutoff / same-symbol。
    当時保有していたpositionと、まだ解放されていなかったcash/slot。
    同batchに合法な資金の受け手がいたか、後続新Entryでしか受け取れないか。

複数制約が同時に効く場合、保存primary reasonだけで単独原因と断定しない。
「そのLoserが保有中だった」は記述的な競合証拠。「その取引を外せばR5が買えた」はまだ未検証の反実仮想として分ける。
非購入R5の仮想PnLを全件合計して、回収可能な利益・将来資産にしない。MAX3、cash、時間の競合がある。

donor削減 → 実際に空くcash/slot → 合法なreceiver → 増加する整数lot、のどこが止まるかを示す。
新しいfull portfolio反実仮想を大量に作らず、保存traceとローカルな会計/制約検算で機構を絞る。

## 7. 🧠 既存scoreのR5/R10分離情報 — 新fitなしの限定診断

使用可能なscoreはmanifestで確認した既存pP/MOVE_P5、MOVE_U2、MOVE_U3、MRETを基本とする。
既存同義列を別headとして重複評価しない。特徴量全列の探索・組合せ探索へ広げない。

ラベルとの関係を新規集計する前に、対象head、元の向き、既存training由来区分、mask、session集計方法を固定する。
現在test全体のquantileから新しい良好bucketを切らない。既存training referenceによるpercentile/rankをreuseする。

必要最小限で出すもの:
    headごとのR5/R10に対する順位分離（両classが存在する場合のAUROC）。
    保存済みrank/bucket別のR5/R10率、連続net return、N、known率。
    既存forward block別・session別の支持の偏り。

元のU5/U10 AUCを再現するための再fit・元bootstrap再実行は不要。
同じscoreで新しいR5/R10との関係を計算することは、元のU5/U10性能証明とは別の追加診断として記録する。
絶対確率として認証されていないscoreを「R5になる確率」と呼ばない。MRETのabsolute-loss defenseをPASSへ格上げしない。

OOFは生成時点のlineageを照合する。in-sample予測を過去OOFへ読み替えない。
session集約・cluster統計の既存実装が適用可能ならreuseする。今回、新しいbootstrap研究や未知のsupport閾値作りで長引かせない。
標本が少ない/偏る場合はNと不確実性を明示し、恣意的なAUC足切りで成功・不可能を決めない。

全期間の診断を見た後で設計するV5.1は、既知Developmentに対する設計である。
後からprecommitしても「このDevelopmentが未見だった」ことにはならない。新たなFresh/OOS主張は禁止。
R5分離情報が弱くても、機械的な数量配分の欠陥が証明できるなら、その構造修正を検討してよい。R5モデル完成を全作業の前提にしない。

## 8. 🔧 V5.1へ進む条件と、1候補の事前固定

以下を満たした場合は、途中のユーザー確認待ちを挟まず、このWorkでV5.1へ進んでよい。

A. V5 baselineが、同じ確定window・正しい会計で比較可能。
B. Rラベルの契約・known maskが確定し、runtimeから隔離されている。
C. 既存causal scoreの支持または機械的配分の根拠から、具体的な変更機構を説明できる。
D. 旧失敗案との実質的な差を説明でき、将来labelを見ない実行可能な数量式を定められる。
E. 凍結・cash・MAX3・lot・時点条件を保持したまま、実decision/数量に変化が生じ得る。

「既存情報で根拠を作れない」なら、V5.1=NOT_CREATEDとし、診断と不足事項まで完成させる。新headをその場でfitして救済しない。
coverage未完了でも、両policyを同条件で比較できる確定範囲の開発実験は可。ただし全予定範囲の月次改善・2倍到達の認証は保留する。

### PRECOMMITに最低限書く内容

candidate_idはV5.1として1つだけ。複数案をReplayして良い方を採用しない。
変更点、無変更点、入力列とas-of、整数数量式、target/cap、最低lot処理、tie順序、同batch順序、cash解放、欠測時動作を完全に固定する。
単に「良い候補へ配分する」では不足。任意の合法入力からBUY/no-BUYとquantityを一意に返せること。
定数・閾値を新しく選んだ場合は、選択根拠と閲覧済みDevelopmentを記録する。既存値だったと偽装しない。
R5/R10を増やすためのgrid、未来損益から逆算したweight、根拠のないAND/OR/weighted blendは禁止。
全候補のscore/rankを別モデルで作り直さない。Capital内の順位/数量の利用法を変える場合は、その変更として明記する。

原slot1/2全ID保護、U5件数floor、全window非劣化等の旧局所Gateを自動移植しない。
逆に、R5件数増加・利用率向上を新しい必須Gateにもしない。
現金が余っても損失を避けて最終資産が上がるなら前進になり得る。「空き資金を必ず使う」ことを強制しない。

policy、code、inputs、window manifest、metric定義、実行予算をGitHubへ保存し、commit確定後にcandidate Replayを開始する。
設計後は同cycleで係数・閾値・候補ID・窓を救済変更しない。

## 9. 🧪 新経路の検証 → V5.1 Replay

人工canaryで最低限確認する:
    購入判断に未来R5/R10/U5/損益/将来arrival/将来売却可否を渡していない。
    未来suffixを変えても、その変更がまだ観測不能な時刻までの判断prefixは不変。
    同batchの未確定結果を現在判断へ戻さない。
    cash非負、quantityが100の倍数、MAX3、同銘柄制約、費用二重控除なし。
    未確定SELL・MTMだけではcashが増えない。
    seed・tie・順序・出力が決定論的。

最初の実差分は、時刻順に最初に異なるdecision/quantity/debitを記録する。後から良好なR5例だけを選んで説明しない。
全期間の市場canary反復はしない。必要最小限のprefix検証と人工テストに絞り、その実行量も数える。
実差分が0ならNO_POLICY_DIFFERENCE。閾値を緩めて発火させず、重い同一Replayを省略する。

V5.1は、固定した同じwindow manifest・初期cash・source・約定費用で1batch実行する。
追加購入後はcandidate自身のcash・position・quantityを進める。V5の下流cashや購入集合へ戻して結果を作らない。
未来の売却sourceが不足する候補を、その不足を知って事前に購入対象から外さない。購入後に計測不能となればwindowにその失敗を残す。

独立会計検算は保存出力を再要約するだけでなく、raw price/source・cost・quantity・credit/debitから別計算で各windowのcashを再構成する。
window初期cash、日次carry、BUY/SELL件数、保有、費用、最終資産、差分の一致を検査する。full engineをもう1本作ることは必須にしない。

## 10. 📊 判定 — 最終資産と測定成立を混ぜない

比較表には必ず、各policyの予定window数・coverage可・実行完了・unknown/blocked数を出す。
主比較は同じ予定window集合を維持し、片方だけ完了したwindowを黙って除外しない。
両方完了subsetのpaired値は診断として出せるが、それだけで全体改善としない。

| 指標 | V5 RESET20 | V5.1 RESET20 | 差 |
|---|---:|---:|---:|
| 最終資産 最小 | 計測 | 計測 | 計算 |
| 最終資産 平均 | 計測 | 計測 | 計算 |
| 最終資産 中央値 | 計測 | 計測 | 計算 |
| 最終資産 最大 | 計測 | 計測 | 計算 |
| 200万円到達数/完了窓数 | 計測 | 計測 | 計算 |
| 予定窓数・未完了窓数 | 計測 | 計測 | 計算 |

中央値差は median(FinalCash_V51) - median(FinalCash_V5)。paired差の中央値とは別欄にする。
各windowの差も全件保存する。平均・最小・MaxDDが悪化したら、中央値が上がっていても隠さずtrade-offと記録する。
R5/R10の件数・投入額・利益寄与、Loser投入額、U5/U10、cash/slot利用率は補助表。
2倍hitは正式終点cash >= 2,000,000円。途中一時的に2倍になったケースとは区別する。

statusを分離する:
    MEASUREMENT_COMPLETE / MEASUREMENT_INCOMPLETE
    NO_POLICY_DIFFERENCE / NO_WEALTH_PROGRESS / DEV_WEALTH_PROGRESS
    NORTH_STAR_MEDIAN_NOT_REACHED / NORTH_STAR_MEDIAN_REACHED_DEVELOPMENT

DEV_WEALTH_PROGRESSは、事前固定した主評価集合が両policyとも測定成立し、中央値差>0の場合のDevelopment上の前進を意味する。
不完全subsetの改善はPARTIAL_DIAGNOSTIC_ONLY。中央値差<=0なら今回候補は不採用。
中央値200万円到達は別の目標判定であり、1窓の2倍hitを中央値達成としない。
いずれも将来の月次倍増・本番有効性の証明ではない。productionReady=false、main/paper/liveへの昇格は行わない。

## 11. ⚡ 実行予算と待ち時間の削減

| 実行 | 上限/方針 |
|---|---|
| 新model fit/refit/calibration | 0 |
| 新Capital policy候補 | 最大1 |
| V5 RESET20 | 1つの正式batch。既存同一結果があればreuse |
| V5.1 RESET20 | 条件成立時だけ1つの正式batch |
| Rラベルmaterialization | 同じsource/契約で1回。保存済みならjoinだけ |
| 旧38-session full Replay・閉鎖済み案再Replay | 0 |
| 新価格provider取得・有料処理・保護期間開封 | 0 |
| Claude | 原則0。重大な争点が残る場合だけ依頼要否を報告 |
| 実注文・main merge・force push | 0 |

Wを固定したwindow数とすると、正常系の各policyは最大20×Wのday評価が必要。batch数、window試行数、day試行数、prefix/canary、auditを別カウンタにする。
技術失敗はcheckpointから未完了範囲を再開し、成功済み同一入力を繰り返さない。
全batch再起動は各policy最大1回の技術修復に限定。根拠となる例外・仕様差・修復前後code hashを残す。
これはpolicyの再設計枠ではない。結果が悪いことを「バグ」として仕様変更しない。
共通評価器の修復で比較basisが変わったら、影響する両policyを同じ版に揃える。揃えられない場合は比較未成立。

coverage調査中に、既存入力のbinding・評価器人工テスト・Rラベル契約の作成は並行可能。
CI待ち中は独立したラベル結合・報告整形・保存検証を進める。CI自体が必要なGateなら未完了をPASS扱いしない。
モデル性能の再認証、大規模Oracle再探索、全特徴census、同じ図表の大量作り直しをしない。

## 12. 💾 最小成果物・GitHub保存

保存directoryは新cycleとして、既存有無を確認してから次を使う:
    docs/evidence/capital-v51-reset20-r5r10-20261006-v1/
    research/capital-v51-reset20-r5r10-20261006-v1/

論理的に以下が揃えばよい。項目ごとに小さな文書を大量増殖させず、関連項目はJSON内へまとめる。

1) WORK_REQUEST.md、本書hash、START_AND_INPUT_BINDING.json、過去研究reuse一覧。
2) COVERAGE_AND_WINDOWS.json、calendar/source根拠、予定windowとblocked理由。
3) RESET20仕様・実装・人工テスト結果、V5_RESET20_RESULT.json。
4) R_LABEL_CONTRACT.json、R_LABEL_CENSUS.json、privateの評価用ラベル。
5) CAPITAL_DIAGNOSTIC.json（R捕捉・score支持・金額/枠・介入候補の根拠）。
6) 条件成立時のV51_POLICY_PRECOMMIT.json、実装、初回実差分、V51_RESET20_RESULT.json。
7) INDEPENDENT_ACCOUNTING_AUDIT.json、比較表、必要最小限の図。
8) REPORT-ja.md、CURRENT_STATE.json、WORK_STATUS_LOG.jsonl、MANIFEST.json、actual GET receipt。

privateな生価格、銘柄別台帳、口座情報、secretを公開GitHubへ追加しない。認証されたprivate artifactの保存先・hashで参照する。
図は実結果がある場合のみ。主に「開始日別の20-session終点cash（V5/V5.1/200万円目標）」と「net区分別資金・利益寄与」。異なるwindowを1本の運用曲線へ連結しない。

開始、baseline/診断確定、candidate precommit、最終結果の意味あるcheckpointで、実時計JST・現在地・完了/未実行・根拠・次の方針・countsをappend-only保存する。
書込直前にHEADを再確認し、他作業者の変更を上書きしない。新commitのSHAは成立後だけ記録する。
文書だけなら無関係CIを発火させない保存方法を使い、実装変更に必要な専用検証は省略しない。
保存後はGitHubから読み戻し、commit/tree/blob/本文を確認する。receiptのreceiptを無限に追加しない。

## 13. 🏁 最終報告・停止条件

日本語で見出しと絵文字、数値は表を使用する。最終報告は次の順。

    最終資産比較と目標との差
    → 何を実際に完了したか
    → R5/R10の件数/捕捉/既存score支持
    → V5.1で変えたCapital機構と最初の実数量差
    → 未決済・欠測・不確実性・副作用
    → GitHub commitと次の1手

source/契約不足で一部blockされた場合も、無関係な完了可能工程まで放棄しない。
coverage理由を推測、unknownを0、未来Winnerで購入、未見を装う、閾値救済、V5.2へ連続探索はしない。
V5.1を作れなかった場合は、不足がラベル・入力・既存情報・実数量経路のどこにあるかを区別して報告する。
新モデルなしで解ける可能性まで否定せず、このcycleで示せた範囲だけ結論にする。

### Safety

researchReplayAllowed=true（本書の有限範囲のみ）。
executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed /
liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed /
transmitted はすべてfalse。

## 14. 📎 出典と、この指示書が新たに決めたこと

本書作成時にactual GETした原本:
[S1] a35399fc27dd8cc67751aadd21d690ba92aefe5b
     docs/evidence/capital-main-reallocation-20261005-v1/checkpoints/P1_HANDOFF_COMPLETE.json
[S2] 同commitの docs/evidence/capital-main-reallocation-20261005-v1/NEXT_WORK-ja.md
[S3] 710656491be06235901b45c50a8b5cbd714ba4eb
     research/capital-v5-max3-slot-intelligence-20261004-v1/replay.py
[S4] 同commitの research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py
[S5] 添付最新handoff ZIP内の CURRENT_STATE.json / GITHUB_POINTERS.json / README_FIRST.md。
[S6] 本会話でユーザーが転送した前チャットのsession/rolling20照会回答。
     URLは転送本文に残っていないため、prepare.py等の正確なpathはWork開始時にmanifestで解決する。

S1/S2は凍結・未実行・過去閉鎖・資金経路の根拠。
S3はlegacy正規化式、day単位の会計、候補集合からのsession生成、EODの実装根拠。
S4はBUY/SELL係数と固定EXIT/EOD source処理の実装根拠。
S5/S6のhashや原因説明は、実物を照合するまで本書による再認証済みとはしない。

新しい合意/設計条件:
    R5/R10を追加し、既存U5/U10を置換しない。
    毎窓cash100万円resetを主評価とし、連続calendar/coverage条件を別flagで保証する。
    最大1候補だけ、仕様固定後に同じWork内でV5.1まで進める。
    上記のmetric/status、有限予算、EODを含むRラベルbasisを明示する。

これらは新しいWorkの仕様であり、既に結果が出た・2倍が実現できたという意味ではない。

END_OF_WORK_REQUEST — ARK_CAPITAL_V51_RESET20_R5R10_WORK_V1_20261006
