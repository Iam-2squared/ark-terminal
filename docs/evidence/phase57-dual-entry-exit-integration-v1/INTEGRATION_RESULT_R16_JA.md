# Phase57 — Entry → EXIT → Capital 接続結果 R16

## 結論

**2本のFrozen Entry → 同一Candidate A → 同一Cash Capitalの接続・全件再生・会計検証は完了。最終Entry選定は保留。**

EXIT評価可能分ではCandidate AはFixed12を改善したが、平均net損益はまだマイナス、PFは1未満。
Capitalでは欠損参照価格による未確定ポジションが残るため、全Portfolio Return / Max Drawdown / 最終Equityは算出不可。
未確定を除外した好成績や、旧277件のCapital結果は使っていない。

## 固定情報と実行Evidence

- Entry Dual Freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`。
- 最終候補: `IMMEDIATE` / `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`。再学習・再選定・追加最適化なし。
- Frozen EXIT: `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1`。元policy / Fixed12 sourceをSHA固定して再利用。
- EXIT adapter実装・事前固定: `416595cc824068fb34abcdc2e2bc368e8c155831`。
- Capital契約事前固定: `4d20b6fa0fec7977a08da70484a2b126e6aa0178`。
- Capital最終実行HEAD: `fd68460930a3198e3976aba057d41cde1c2c9c97`。
- EXIT CI: run `36115061827` / artifact `10855136419` / SUCCESS。
- Capital CI: run `36117117239` / artifact `10855870021` / SUCCESS。
- EXIT/Capitalの固有合成テスト合計38件PASS。全3,848 fillsでstreaming EXITとR13のstatus/time/netが一致。
- EXITの5出力、Capitalの3出力は、それぞれRun A/Bとローカル/CIがbyte-identical。

これは接続・再現性・会計のPASSであり、収益性・Fresh/OOS・productionのPASSではない。
PR全体の旧CI不合格をこの専用CIの成功で置き換えない。

## データ範囲と日数訂正

各Entryとも2,155 Opportunitiesを保持。Provider新規取得0、保護区画の新規開封0。
対象は既にoutcome-exposedのDevelopmentであり、Fresh/OOSではない。

**R14の日数表記を訂正する。Opportunityが発生した日は58日だが、固定評価カレンダーは59営業日。**
2025-05-30〜2025-08-25の固定protocolにある、Opportunity 0件の2025-07-14もCapitalに含めた。
データを58日に絞り込んだのではなく、CIの日数assertionを固定protocolに合わせた。
旧R14 Evidenceは上書きせず残す。

## EXIT — 同じEntry内のCandidate A vs Fixed12

各Entry内で同じ評価可能IDをpaired比較。単位は取引notionalに対するnet %、Portfolio Returnではない。
ImmediateとR1の直接比較には、次節の共通1,101件を使う。

|Entry|EXIT|paired N|平均net %|PF|下位5% net %|平均保有時間 分|
|---|---|---:|---:|---:|---:|---:|
|Immediate|Fixed12|1,118|-0.07664|0.9346|-5.1863|67.94|
|Immediate|Candidate A|1,118|-0.05414|0.9505|-4.7689|64.83|
|All-Material R1|Fixed12|1,105|-0.12540|0.8908|-4.8530|74.57|
|All-Material R1|Candidate A|1,105|-0.08344|0.9211|-4.5088|71.48|

Candidate Aの平均改善はImmediateで+2.25bps、R1で+4.20bps。改善と黒字化は別。
中央値・worst・勝率・preservationの詳細はEXIT_RESULT_R14.mdおよびR13 summary.json。

## Entry同士 — 同一Candidate A、共通1,101件

|指標|Immediate|All-Material R1|
|---|---:|---:|
|共通評価件数|1,101|1,101|
|平均net損益|-0.07809%|-0.08491%|
|PF|0.9288|0.9199|
|下位5% net損益|-4.7609%|-4.5095%|
|平均保有時間|64.49分|70.84分|

Immediateはこの共通集合で平均/PF/保有時間がわずかに有利、R1は下位5%が良い。
平均差はR1−Immediate=-0.006829pp。これだけで最終採用Entryを決めない。

## EXITの未確定を隠さない

|指標|Immediate|All-Material R1|
|---|---:|---:|
|全Opportunities|2,155|2,155|
|No Entry|192|270|
|凍結済みEntry fills|1,963|1,885|
|Candidate A EXIT確定|1,133|1,115|
|Candidate A EXIT未確定|830|770|
|最初の欠損が15:30の未確定|202|217|
|それ以外の欠損による未確定|628|553|

Candidate Aが先にEXITできたため、その後Fixed12参照が欠けても確定できたケースは15 / 10件。
Fixed12が最後まで評価可能なものだけをEntry/Capitalに通すフィルターは使わない。
15:25〜15:30の問題だけを解消しても、全件の欠損問題は解消しない。

## Capital — 新ledgerによる全件再生

初期cash ¥1,000,000、100株単位、LONG/cash-only。
既存のMAX3は資金配分の3分割であり、保有上限は10ポジション。
両Entryに同じONE_LOT_REFERENCE / EQUAL_MAX3を適用した。
同時刻EXITのcash releaseをENTRYより先に行い、未知EquityでEqual sizingをしない。

|項目|Immediate 100株固定|R1 100株固定|Immediate Equal/MAX3|R1 Equal/MAX3|
|---|---:|---:|---:|---:|
|受付対象fills|1,963|1,885|1,963|1,885|
|資金管理で受付|26|24|3|2|
|EXIT確定・決済|16|14|2|1|
|未確定ポジション|10|10|1|1|
|受付拒否|1,937|1,861|1,960|1,883|
|期末cash|¥483,929.51|¥639,372.39|¥653,643.71|¥658,146.68|
|未確定の取得原価拘束|¥485,342.55|¥313,356.60|¥329,764.80|¥329,764.80|
|決済済み取引のみの損益|-¥30,606.60|-¥47,192.67|-¥16,509.05|-¥12,006.08|
|全Portfolio Return|算出不可|算出不可|算出不可|算出不可|
|全Max Drawdown|算出不可|算出不可|算出不可|算出不可|

取得原価拘束は時価評価額ではない。cash減少を損失額とみなさない。
決済済み取引は4系統とも2025-05-30のものだけであり、59営業日の運用成績ではない。

100株固定は未確定10ポジションで上限に到達し、後続の1,936 / 1,860件が保有上限で拒否された。
Equal/MAX3は純資産評価額が分からず、1,949 / 1,875件をCURRENT_EQUITY_UNKNOWNで拒否した。
両Equal系統で最初に残るのは `2025-05-30|61770|570`、3,200株、取得原価¥329,764.80。
最初の確定的な参照欠損時刻は2025-05-30 10:10 JST。
これはデータ欠損時に資金を架空解放しない会計結果であり、実市場で永久保有したという意味ではない。

全系統でcash非負、100株単位、受付数=決済数+未確定数、cash+取得原価拘束と損益の照合がPASS。
金銭照合誤差の最大値は¥0.00001未満。全未確定/全拒否/決済/Equity ledgerを保存した。

## 接続上の明示的な前提

Entry時刻/価格は変更していない。5分足途中のEntryは、Entry後に完全に含まれる次のregular5mから評価。
例:09:31 Entryに対し09:35〜09:40が最初の対象足。Entry前HIGHやEntry起点の合成5分足を混ぜない。
疎な足のOPENは実在する最初の1分足時刻に置き、nominal時刻へ逆算してcashを戻さない。
保存Entry価格には既に買いslippage 5bpsが含まれる。これを保持し、既存round-trip cost 0.05ppを1回だけ計上。
「全コスト合計5bps」とは表示しない。

旧方式のmin(5,時刻差)による資金拘束サンプリングはEntryごとに時刻点が異なり、集計tradingMinutesが一致しない。
その平均拘束/平均同時保有をEntry順位付けに使わない。上表は確認できる期末拘束原価のみを示す。
平均utilization、全Equity、全MDDは未確定。保有上限やEntry時刻を変えて数値を整えることはしない。

## CI失敗と修正の保存

run36116691952: drawdown初期化の転記ミスを合成テストで検出。実データCI再生前に失敗。
run36116943012: 修正後の再生は完了したが、CIの日数58というassertionが固定カレンダー59と不一致。
両失敗run/artifactと旧Evidenceを残した。最終run36117117239は38 tests、全件replay、byte再現性までSUCCESS。
修正でEntry/EXIT/Capital閾値やデータ集合を変更していない。
初期ローカル結果の一部は転記ミス前後でsourceラベル不一致があったため、正式なsource一致Evidenceには採用していない。
最終fd684609のsourceとローカル/CIの出力一致のみを正式な再現性判定に使用した。

## 次の一手と停止境界

次はEntry再研究ではなく、**保存済みcurrent-Developmentのregular5m参照欠損を監査すること**。
真の未取得、無約定区間、terminal calendarの意味を、既存raw/manifestから区別する。
証拠なしの補間、前値埋め、架空約定、欠損のある日や銘柄の事後除外は行わない。
旧277の好成績、解決済みEXITだけのcomplete-case、Fresh/OOS追加開封でこの問題を隠さない。
固定契約で全Portfolioが評価可能になるまで、最終Entryの採用判断は保留する。

Safety9項目は全false。main merge / live / paper / production / 自動昇格なし。
CI artifactは30日保存であり永久保管ではない。EXITは2026-10-25 08:50:29Z、Capitalは同日09:13:37Zに期限。
正式ハッシュ・失敗履歴・判定はCAPITAL_RECEIPT_R16.jsonを参照。
