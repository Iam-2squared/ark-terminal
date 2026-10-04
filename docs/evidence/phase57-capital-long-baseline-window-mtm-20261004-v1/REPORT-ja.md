# 📊 今回のLONG-only Capital baseline — 最終Report

記録日時: 2026-10-04T13:01:24.490+09:00  
Repo / branch: Iam-2squared/ark-terminal / capital-state9-vnext-20261004  
basis HEAD: `c285aa629ab568a35c3ee5bb4b445e4c6c8ce8ae`  
結果commit: 保存後に `receipts/` へ追記。未来SHAは記載しない。

## 🛑 結論

**MTM実装・契約監査はPASS、baseline完全測定はBLOCKED。**

承認された正式MTM valuation contractを結果前にprecommitし、今回のLONG-only旧Adaptive mechanics/current-input baseline MAX3/MAX4/MAX5と、別枠のFixed sanity3 armを実行した。最初の「5分window最終分の保存足なし」は新契約で通過した。しかし、その後のfunded positionで**同一5分window内の保存sourceが本当に0件**となった。ユーザー指定どおり6 armすべてfail-closedで停止した。

完了した営業日は0。日次成長率・rolling20を部分traceから作らず、null/未測定とする。これは「利益0%」でも「rolling20で2倍にならなかった」でもない。現時点では判定不能である。State9-aware新Capital、昔のCapital成績調査、Integrated版には進んでいない。

## 🎯 ご指定の主要結果 — MAX3/MAX4/MAX5

| 今回のAdaptive mechanics baseline | MAX3 | MAX4 | MAX5 |
|---|---:|---:|---:|
| 対象Development sessions | 58 | 58 | 58 |
| 完全測定したsessions | 0 | 0 | 0 |
| 1営業日あたり幾何平均 | 未測定 | 未測定 | 未測定 |
| 1営業日あたり算術平均 | 未測定 | 未測定 | 未測定 |
| 1営業日あたり中央値 | 未測定 | 未測定 | 未測定 |
| rolling20・100万円換算最小 | 未測定 | 未測定 | 未測定 |
| rolling20・100万円換算中央値 | 未測定 | 未測定 | 未測定 |
| rolling20・100万円換算平均 | 未測定 | 未測定 | 未測定 |
| rolling20・100万円換算最大 | 未測定 | 未測定 | 未測定 |
| 20-sessionで200万円到達区間 | 判定不能 | 判定不能 | 判定不能 |
| Final Equity / MaxDD / utilization | 未測定 | 未測定 | 未測定 |
| 状態 | BLOCKED | BLOCKED | BLOCKED |

完全測定できた場合の定義はprecommit済み。全58 sessions（取引なしも含む）の前日終値equity比を使用し、幾何平均・算術平均・中央値を併記する。rolling20は全39重複区間を集計し、各区間の成長倍率×100万円の最小・中央値・平均・最大と200万円以上の区間数を測る。良かった区間のみを採用しない。今回は実測区間0のためグラフを生成していない。Private curveは停止前の既知prefixのみで、完全equity curveではない。

## ⚙️ 今回の対象とmechanics

Frozen FIRST ENTRY v2 P1_Q70とFrozen Structural EXIT v3 Local Guardを維持し、既存のdownstream EOD/cutoff/liquidityと組み合わせた**現在のLONG-only baseline**である。昔のSHORT+LONG成績や旧Adaptive scorerそのものの再現ではない。

| 項目 | 今回の仕様 |
|---|---|
| Side / account | LONG-only・現物cash-equity-only |
| Causal score | 保存済みFrozen first_intent.score。旧confidence/probabilityへ読み替えない |
| Adaptive sizing | score ordering / weight / candidate equity cap / dynamic target utilization / cash |
| MAX3/4/5 | 同時保有上限のみ。Adaptive資金量を1/Nへ置換しない |
| Fixed sanity | Equity/N。主方式と分離 |
| Liquidity | 直前20 trading sessionsのmedian Trading Value×1%。欠測入力はfunding fail-closed |
| Entry cutoff | fill timestamp >=15:20はfunding0。Frozen identity保持 |
| EOD | 既存15:20 SOR-market研究reference route。実注文0 |
| Limit-up | causal confirmationのみ。保存flag UNKNOWNをconfirmedへ変換しない |
| Lot | 100株 |
| Broker commission | 0円 |
| Execution friction | BUY×1.0005、SELL×0.9995を1回のみ。旧round-trip fee追加0 |
| Cash release | valid fillの既存source completion assumed_available_at。backdate0 |
| 実arrival / live認証 | historical actual arrivalはUNKNOWN。live利用可能性の新認証ではない |

P1 Entryが既に使っているState9情報は変更しない。Capital layerへの新しいState9/Path直接参照・Rank作成・評価は0である。

## 🕒 正式MTM valuation contract

Contract: `CAPITAL_OBSERVED_CLOSED_5M_WINDOW_MTM_REFERENCE_V1`  
Precommit commit: `0cd22086ffb1fee129851ab5c7d609a9eb52b6c4`

各closed5m window `[t−5min,t)` 内に存在する保存済み1m barのうち、timestampが最大のbarのCloseを、そのwindow終了時のmarkとする。前windowからの価格持越し・interpolation・forward-fillは禁止。window内source0件なら停止する。「欠測補完」ではなく、正式な観測window valuation contractとして保存した。

| 検査段階 | 保存source rows | 結果 |
|---|---:|---|
| 最初の旧final-minute blocker | 同一window内sourceあり | 新契約で通過 |
| 次のfunded blocker・Primary保存足 | 0 | STOP |
| 同じblocker・Independent保存足 | 0 | STOP一致 |
| 同じblocker・元provider保存token | 0 | 元原本にも存在しない |
| 保存済み同symbol/sessionの他path検索 | 該当path1、window rows0 | 既存別path回収0 |

元providerの保存prefixはwindowの前後時刻をcoverしている。単なるCompact schema変換で落ちた行ではない。ただし保存metadataだけでは「実市場no-trade」と「capture gap」を区別できず、`SOURCE_WINDOW_EMPTY_UNKNOWN_NO_TRADE_OR_CAPTURE_GAP` を維持する。薄商い・売却不能・悪いEntryと断定しない。公開Evidenceはaggregate/hashのみ。row-level symbol/session/timeはPrivateに保持する。

## 🔍 STOP時点の進捗（成績ではない）

| Arm | Funded prefix | 決済済みprefix | Cash recycling prefix | STOP時open | 観測最大同時保有 | Funding未評価 |
|---|---:|---:|---:|---:|---:|---:|
| Adaptive mechanics MAX3 | 3 | 2 | 2 | 1 | 3 | 1,574 |
| Adaptive mechanics MAX4 | 3 | 2 | 2 | 1 | 3 | 1,574 |
| Adaptive mechanics MAX5 | 3 | 2 | 2 | 1 | 3 | 1,574 |
| Fixed sanity MAX3 | 3 | 2 | 2 | 1 | 3 | 1,574 |
| Fixed sanity MAX4 | 3 | 2 | 2 | 1 | 3 | 1,574 |
| Fixed sanity MAX5 | 3 | 2 | 2 | 1 | 3 | 1,574 |

全1,600 identitiesを保持。22件はあらかじめ固定した15:20 cutoffによるfunding0として全cohortに記録した（STOP後の実処理を行ったという意味ではない）。停止前に実際に観測したLiquidity skipは各arm1件。3 funded + 1 liquidity skip + 22固定cutoff + 1,574未評価 = 1,600。

将来execution UNKNOWN18件をBUY Rankや資金量へ渡していない。停止prefixでfunded UNKNOWNは0だが、全traceが未完了なので「18件すべてfunded0」や「Liquidityで18件を自然に排除した」とは結論しない。全traceでのfunded UNKNOWN数・winner capture・全期間rejection構成は未測定。STOP原因は18 execution UNKNOWNではなく、実際にfundedしたpositionの空MTM windowである。

## ✅ Focused / future-blind / independent audit

| 検査 | 件数 | Mismatch / FAIL | 判定 |
|---|---:|---:|---|
| Focused tests | 21 | 0 | PASS |
| 全1,600候補source/future-blind canary | 11,200 | 0 | PASS |
| 別実装による独立再計算 | 100,346比較 | 0 | PASS |
| 保存原本の空window検査 | 異なるfunded blocker1・6 arm | 0 source rows | STOPの根拠確認 |
| Frozen Entry/EXIT・receipt branch refs | 3 | 0変更 | PASS |

IndependentはPrimary/新window helper/metrics helperをimportせず、別のsource lineageからcandidate、prior20 liquidity、funding、quantity、cash ledger、prefix frames、STOPを再構成した。独立監査PASSの意味は**known prefixと正当な停止が一致**ということ。58 sessions完全成績の認証ではない。

canaryはfuture execution有無・future outcome・future window price変更でruntime rank/現在markが変わらないこと、前window carry不可、同一closed windowの実Closeのみを検査した。100株lot・cash>=0・同時保有cap・commission0・entry debit/exit credit/trade PnLの整合を確認した。cash/fee二重計上0。missingをPnL0へ置き換えない。

## 🔒 Exposure / Safety / 研究予算

| 項目 | 今回消費 |
|---|---:|
| 有限replay | 6（Adaptive3、Fixed sanity3） |
| 新fit / 新ranker / 新State9評価 | 0 |
| 閾値・deadline・liquidity sweep | 0 |
| 昔のCapital成績再調査 | 0 |
| Provider request / 新市場data | 0 |
| Protected/Holdout/Fresh/Validation/OOS/Prospective開封 | 0 |
| 価格補完 / 前window carry / outcome-based除外 | 0 |
| Orders / main merge / force push | 0 |
| Claude | 0 |

executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted / productionReady はすべてfalse。既存Development reference研究でありFresh/OOS結果ではない。

## 🧾 Append-only checkpoints

| Checkpoint | 実際のresult commit |
|---|---|
| START / MTM precommit | `0cd22086ffb1fee129851ab5c7d609a9eb52b6c4` |
| 実装 / Focused / source canary（結果前） | `e6745a06c4a36322411df5a8a5f29bbc60b0f367` |
| 有限6 arm結果 | `8e3606e45d8ac412f46a551073c7610db44cbd32` |
| Independent / 保存原本audit | `c285aa629ab568a35c3ee5bb4b445e4c6c8ce8ae` |
| このclosure / handoff | commit成立後にreceiptへ追記 |

新cycle: `docs/evidence/phase57-capital-long-baseline-window-mtm-20261004-v1/`。旧15:29 negative、15:20 EOD、旧STOP、Frozen各Evidenceは上書きしていない。Source hashesはSOURCE_CONTRACT_AUDIT.json、public/private構成はMANIFEST.jsonとPrivate package manifestを参照。

## ⏹️ 最終現在地と次方針

Status: `CAPITAL_BASELINE_MEASUREMENT_BLOCKED_EMPTY_WINDOW`

今回のbaseline実装・有限replay・独立STOP監査を完了したが、**完全成績の測定は未完了**。MAX3/4/5の優劣、幾何平均、rolling20 doubling、Freeze候補はいずれも判定不能。Capital Freezeなし。Integrated開始なし。

承認されたsource0件STOPを維持し、ここで停止する。新State9研究やthreshold/liq調整で救済しない。再開可能な最小条件は「同一window内の既存admissible sourceをmechanically回収」すること。それも無ければ、別の明示的なsource/valuation authorityが必要であり、このWorkで前window持越し等へ自動変更しない。
