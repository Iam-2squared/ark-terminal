# Phase57 Capital — 日末資産・日次収益率の独立検算 / controlling handoff

Saved: 2026-09-27 17:03 JST.
Basis research HEAD: `701cb9ad18dc6f4474225023b2273bdf71811b78`.
Report result commit: `21bed32a7e0cfaf879a732ba5bf129747c8d5770`.
This file's enclosing commit is the new handoff; re-fetch HEAD rather than assuming a self-SHA.

## 現状

**REPORTING_AUDIT_PASS / 4_COMPLETE_EOD_CURVES / 2_UNRESOLVED / CAPITAL_V2_NO_SELECTION.**

Capital Rank v2の3候補・24 fitsは、この作業を開始する前に既に完了していた。今回新しく行ったのは、既存結果に対する独立現金監査、日末だけの追加資産曲線・日次収益率の生成、38 tests、専用CI、local/CI byte identity確認。新モデル学習・prediction refit・policy replayは0。

新Capitalは未採用。以下のPortfolioは全てEXISTING_R35_CAUSAL_CONTROL＋TERMINAL_HOLD_BENCHMARK。Final EXIT未選定。統合戦略の完成や全6条件の連続日中曲線完成とは呼ばない。

## 期間と定義

評価は2025-07-22 09:00～2025-08-25 15:30 JST、24取引セッション、35暦日（両端含む）。以前の34-session窓でも全2,155/58-session測定でもない。

旧protocolは、日中eventに一つでもequity nullがあるとfullEquity/全期間Return/日次統計をnullとする定義だった。元の出力・Gate・formal negativeは変更していない。

今回の追加specは明示的にPOST_RESULT_SUPPLEMENT_NOT_SELECTION。結果閲覧後の会計・報告追加検算であり、performance-blindな戦略評価とは称さない。全eventの現金・数量・cost basis・売却代金・手数料・PnL・保有identityを独立検算し、15:30 post-eventで保有0・未決済0・equityValid・equity=cashが成立する日末だけ認証した。昼の価格欠損を埋めず、その日に実際に保存された確定売却処理で全て現金へ戻った場合の日末残高を報告する。

日次return=EOD[t]/EOD[t-1]-1。初期現金100万円。欠損日を飛ばして接続しない。幾何平均の分母は全24予定sessionで、 surviving valid daysではない。EOD MaxDDは初期現金を含む日末列のみの下落率で、日中MaxDDとは別。旧strict intraday MaxDDは全6条件でnullのまま。

## 独立検算結果

| 条件 | 認証日末 | 最終日末資産JPY | Endpoint Return | 日次算術平均 | 日次中央値 | 日次幾何平均 | 日末MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| IM MAX3 | 24/24 | 870,981.371563 | -12.901863% | -0.528029% | -1.056078% | -0.573908% | -17.445521% |
| IM MAX4 | 24/24 | 899,231.434113 | -10.076857% | -0.386894% | -0.695519% | -0.441584% | -10.925484% |
| IM MAX5 | 24/24 | 850,512.904350 | -14.948710% | -0.642628% | -0.652836% | -0.672378% | -15.171363% |
| R1 MAX3 | 9/24 | null | null | null | null | null | null |
| R1 MAX4 | 9/24 | null | null | null | null | null | null |
| R1 MAX5 | 24/24 | 939,925.932650 | -6.007407% | -0.214258% | -0.394707% | -0.257810% | -14.572876% |

確定した4条件は全て損失。R1 MAX5がこの4条件では最も小さい損失だが、残る2条件が未確定なので6条件の勝者や正式採用を決めない。

原結果の確定取引PFは順に0.734/0.807/0.710/0.943/0.875/0.873。R1 MAX3/4のPFは未決済を除く閉じた取引だけ。価格評価可能時間に限定した時間加重稼働率はIM MAX3 80.32%（対象時間coverage98.80%）、MAX4 79.72%（95.92%）、MAX5 74.12%（94.93%）、R1 MAX5 71.23%（95.36%）。これを全時間の無条件統計と呼ばない。

20/60/120/240取引日の同率複利はendpoint-report.jsonに機械的換算として保存。将来予測・保証ではなく、負けた24-session率を延長した仮定計算に過ぎない。

## 真のデータblocker

R1 MAX3/4は `2025-08-04|36700|602` のauction未決済。100株、簿価JPY190,595.25が残り、跨日markと企業行動の連続性を証明できない。最終cash797,007.30115 / 783,027.406175は、未評価の保有株を含むequityではない。8/4以降の追加日末もnull。

元のmissing-reference768行は昼休み関係50、未証明overnight718。この欠損は未補完。以前の34-sessionの2025-07-17/59050も未修復。今回の24-session日末評価をその修理と称さない。

## Capital Rank v2の評価設計問題

旧rank v2は0/3 PASS / NO_SELECTION_STOPを維持。固定Top3 enrichment Gateは両arm1.15倍。ただしexact Entry timestampのbatchでTop3はIM731/819=89.26%、R1776/795=97.61%を選択する。

既知label K、全候補N、Top3選択Sとして、未知行を全て選択側へ置く最大限有利な場合でも既知選択はS-(N-K)以上。全positiveを選べても濃縮の緩い上限はK/[S-(N-K)]。

- IM: 808/(731-11)=1.122222倍
- R1: 786/(776-9)=1.024772倍

この固定Gateはevent geometry上到達不能だった。学習前に見落とした評価設計の問題であり、State/Signal/Patternに予測情報がないことの証明ではない。Gateを下げたり候補を再選択して救済しない。

| rank | IM Top1 | IM Top3 | R1 Top1 | R1 Top3 |
|---|---:|---:|---:|---:|
| Existing control | 1.159x | 1.028x | 1.107x | 1.018x |
| A: Selector/Entry | 1.172x | 1.014x | 1.077x | 1.018x |
| B: +State/Signals/path | 1.105x | 1.016x | 1.142x | 1.010x |
| C: +Pattern187 | 1.129x | 1.030x | 1.132x | 1.010x |

同時刻Top3と、1日を通した現金・保有枠MAX3は別の意思決定集合。次の研究では実際のCapital競合集合と到達可能なGateの整合を先に検証する必要がある。今回新候補・threshold・rank familyは追加していない。

## 実装とCI

- Spec: `CAPITAL_ENDPOINT_RECONCILIATION_SPEC.json`
- Spec SHA256: `7859626b18ddd85ea48920d07ba89b79e7e01a34e4960c11fbfb482f16fad456`
- Code: `scripts/phase57_capital_endpoint_reconciliation.py`
- Tests: `scripts/test_phase57_capital_endpoint_reconciliation.py`
- Workflow: `.github/workflows/phase57-capital-endpoint-reconciliation.yml`
- Required focused CI: **36304417925 SUCCESS / 38 tests PASS**
- Exact tested SHA: `60f481ee9d7a50d8674bfc64a88a5a1687322b8b`
- CI artifact: **10925989116**
- CI ZIP SHA256: `8655f3884493217c44e21907c75ea7079137d284fc3c0013501f146fc7751a80`
- Original rank/portfolio Action: 36302009680 / artifact10926311771
- Original ZIP SHA256: `afa814bb189d50d84d1101b0978f2edd208ddc74ab35fcd8348d0e501845169b`

6台帳、3,126 event/snapshot、478 funded、476 closedを照合。variant間の同一取引は独立標本に数えない。CI A/B、local A/B、local/CIの4出力ファイルがbyte-identical。7入力hashとsource/module/test/specのlocal/GitHub/CI同一性確認。

初回CI36304358140は38 testsと2回再生成まで成功し、workflow自身をsparse-checkoutし忘れたためreceiptで失敗。checkout対象1行の追加だけで修正。会計指標・研究semanticsは変更なし。最終hand-off保存は文書・結果のみ。これはPR全体greenの主張ではない。

## 永続結果と復元

本ディレクトリの `CAPITAL_ENDPOINT_RECONCILIATION_RESULT.json` に6条件summaryとCI/source/hashを保存。詳細はCI artifactの `run-a/` に以下:

- `endpoint-report.json` SHA256 `01ebe3cc97c0957b4deaaecb1644d11c844da0160d0b811a7f202bdd3b572ba8`
- `daily-endpoints.csv` SHA256 `9381f690cd2e1abc43014035834352b3a3d76caa8a2b7cc93e6c3cdbe135a4f0`（144行）
- `endpoint-summary.csv` SHA256 `a96e2991003555de50fc0f937d45e9315e4d650e55b9ffd5d5c21e3ed3bc947e`（6行）
- `rank-scorecard.csv` SHA256 `ef4eb67ead1bc30afd35107fd5910f307f2cf3ae05f9491406320385a3842893`（24行）

詳細は恒久保存された元 `CAPITAL_RANK_V2_RESULT/` と本コード/specだけから復元可能:

```bash
python -m unittest -v scripts.test_phase57_capital_endpoint_reconciliation
python -m scripts.phase57_capital_endpoint_reconciliation \
  --source docs/evidence/phase57-comprehensive-exit-v1/CAPITAL_RANK_V2_RESULT \
  --spec docs/evidence/phase57-comprehensive-exit-v1/CAPITAL_ENDPOINT_RECONCILIATION_SPEC.json \
  --out /tmp/capital-endpoint-report
```

ユーザー向けExcel、日末曲線3図、日次CSV、詳細日本語レポートとZIPを会話添付へ作成。グラフは日末のみで、R1 MAX3/4の欠損区間を接続・補間しない。

## Freeze / Exposure / Safety

Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`、Selector、rank、sizing、EXIT、fills、原mark、原Gate、formal negativeは不変。今回のnew model fits=0、new policy replays=0、provider=0、protected=0。Safety9全false。main merge / force push / live / paper / productionなし。

過去R49とsuperseded v0の範囲外decodeを消さない。今回は7つの固定済み派生結果ファイル以外のmarket payloadはdecodeしていない。

## 今後の方針 / superseded情報

- 日末にflatとなる4条件まで永久に評価不能という説明は、この追加検算で訂正。ただし旧strict all-event結果は変更しない。
- Capital v2がまだ実装/学習途中という会話説明は、既存formal resultにより訂正。0/3 PASSで既に閉じている。
- 新rank selection / Final EXIT / full six-curve completionは未達。Gate緩和、追加候補、都合の良い再学習を行わない。
- 次のCapital研究には、実際に枠・現金が競合する時点のallocation目標と実現可能Gateを新たに事前固定する必要がある。
- 2条件の全期間評価には独立した時刻付き価格と企業行動の連続性の根拠が必要。既存許可範囲で見つからなければ、新provider/範囲拡大の明示承認が必要。未来価格、架空fill、0損益化で埋めない。
