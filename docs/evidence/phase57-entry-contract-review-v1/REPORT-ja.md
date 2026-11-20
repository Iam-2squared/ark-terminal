# Phase57 Entry — 外部暫定レビューの独立監査

Audited HEAD: `aa4dab3d79c26b89e0f699def30e9c4bc65752ff`。保存Development artifactだけを使った追加診断。v1 Evidenceとdecisionは変更しない。

[コード](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/scripts/phase57_chart_entry.py) / [元REPORT](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/docs/evidence/phase57-chart-entry-v1/ci-result/REPORT-ja.md) / [decision台帳](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/docs/evidence/phase57-chart-entry-v1/ci-result/measurement/trades.json.gz) / [Opportunity/grid](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/docs/evidence/phase57-chart-entry-v1/ci-result/substrate/opportunities.json.gz) / [feature台帳](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/docs/evidence/phase57-chart-entry-v1/ci-result/substrate/features.json.gz) / [outcome台帳](https://github.com/Iam-2squared/ark-terminal/blob/aa4dab3d79c26b89e0f699def30e9c4bc65752ff/docs/evidence/phase57-chart-entry-v1/ci-result/substrate/outcomes.json.gz)

## 主な再計算

| Baseline | BUY | +3 Capture | +5 Capture |
|---|---:|---:|---:|
| Immediate one-shot | 1,392 | 502/761 = 65.97% | 279/408 = 68.38% |
| Immediate + identical retry | 1,652 | 565/761 = 74.24% | 315/408 = 77.21% |
| E5 saved decisions | 1,645 | 546/761 = 71.75% | 304/408 = 74.51% |

この比較は同じsaved gridに限定した記述的診断。retry mechanicsの交絡を除いたとき、E5に捕捉上の追加優位は確認できない。収益性全般・独立OOSの結論ではない。

## 1. HEAD / provenance — 確認済み

PR #587 latest HEAD aa4dab3d79c26b89e0f699def30e9c4bc65752ff、Draft。artifact run35499090053、ZIP SHA256 63f4e6626f8bee365aefdb435561ea2f4307ba77fa648024ab55fa64cd9d3636。選択した5ファイルは各manifest hash一致。

## 2. 共通母集団 — 確認済み

evaluation Opportunity2,155件。E5/Immediate両方BUY1,388、E5のみ257、Immediateのみ4、両方未BUY506。

## 3. E5 BUY内訳 — 確認済み

初回BUY1,197、先行するLEARNED_NEXT_STEP_ADVANTAGEあり208、学習WAITなしで約定/quote再試行後BUY240。合計1,645。

## 4. E5 No-entry分類 — 定義を分離

未BUY510。空grid201、grid内全tickでfill priceなし245、fill priceはあるがquoteと同時に利用できるtickなし57、実行可能tickがあったが学習WAITで逃した7。提示された201+291+18は合計のみ一致し、分類定義がないため再現確認とはしない。最終attempt理由で分類すると空201/stale206/unfilled103。

## 5. 90%固定Gate — 確認済み

+3 winner761件→685件必要、+5 winner408件→368件必要。Gate変更なし。

## 6. 既存tick内oracle上限 — 確認済み

実行可能tick＝保存grid内・quoteAvailable・実fill priceあり。+3捕捉上限583/761=76.61%、+5上限326/408=79.90%。固定contractの同じ価格/同日Capture定義で90%は到達不能。threshold別のoracleで、単一policyが同時達成する保証ではない。

## 7. 残されたmodel余地 — 表現を修正

E5は546/583=93.65%、304/326=93.25%のoracle上限を捕捉。なお37件/22件（全winner分母で4.86pp/5.39pp）の余地はある。「余地ほぼなし」より「このgridだけでは90%Gateに届かない」が正確。

## 8. Capture改善帰属 — 確認＋因果解釈を修正

Immediateからの新規capturedは+3が65件（E5-only63、両方BUY2）、+5が37件（35、2）。E5-only改善全件でImmediate最終理由はBUY_ORDER_UNFILLED_NO_SOURCE_TRADE。失われたwinnerは+3が21、+5が12。2件をmodel alphaと断定できず、因果効果や有意性は未識別。

## 9. retry-matched baseline — 新しい保存台帳診断

同一grid/quote/priceで学習WAITなし、最初の実行可能tickでBUY。BUY1,652。+3捕捉565/761=74.24%、+5捕捉315/408=77.21%。E5は各19件/11件少ない。E5新規vsRetry2件/2件、喪失21件/13件。元decisionを上書きせず補助診断。

## 10. 11:30と短いgrid — 確認済み

空grid201件はすべて11:30選出。grid長は0:201、5:179、6:218、7:1,557。11:00〜11:29の候補は今回11:00の218件で6tick。コード例11:00→6、11:05→5、11:10→4、11:15→3、11:20→2、11:25→1、11:30→0。これはv1事前固定契約の挙動だがOpportunity維持の目的との不整合。

## 11. 11:30だけ修正する上限 — 計算条件を明示

空grid201件のうち+3 winner72、+5 winner38。既存tickでoracle最適化した上限にこれら全部を足すと655/761=86.07%、364/408=89.22%。提示数値はこの意味で一致。現在E5の他decisionを固定し空gridだけ成功にするなら618/761=81.21%、342/408=83.82%。session-active時計で他の短いgridも延ばすvNext全体の上限ではない。

## 12. paired評価 — 解釈上の制約

paired entrantsは処置後の選択へ条件付けした部分集団。全2,155件のfixed-population capture/throughputを主とし、paired MAEは補助とする。No-entryのutilityを0等にする場合は政策目的として事前定義し、実現収益と混同しない。既存codeのpopulationObjectiveはNo-entry/unknown=0とmissed-winner penalty。

## 13. BUY/WAIT教師 — コード確認・改善案は未検証

targetはU(now)−U(next5m)。予測差>=0でBUY、最後tickはBUY試行。絶対Uが負でもBUYし得る。Uには30m return/MAEとsession-end MFE/MAEが混在し、MFEに正の重み。最適停止・EXPIRE価値明示は検討候補であり、性能改善が証明された修正ではない。

## 14. feature availability — warmup主因説を支持しない

NEW適格evaluation tick13,102件で層別。連続場中経過30〜59分(n3,042):w15 47.67%、w30 36.75%、w60 0%。60分以上(n10,060):w15 31.08%、w30 25.97%、w60 18.43%。w60の前半不足は説明できるが、w15/w30の多数欠測は単なる時間不足では説明不可。元1m無約定、source欠測、strict集約等の区別はこの保存featureだけで確定しない。VWAP complete-prefix/adapter不一致をw15欠測原因と即断しない。

## 15. clock vNext / Gate — 未実装

session-active30分で昼休みcarryする案は合理的な候補。11:30 auctionがいつavailableか、12:30開始と最初closed-bar時点、15:25〜auction、30m教師のlunch crossing、staleness、同一retryを先に固定する必要がある。単にclockを差し替えた性能で採否を決めない。90%Gateは維持しoracle-normalized/実行可能winner分母は補助表示に留める。

## 16. 次工程・Safety — 提案、変更なし

最優先は公平なretry baselineとclock/fill/availability原因監査。その後にclock vNextをprecommitしv1併記。最適停止教師は別v2研究。同じ交絡を残した再学習は行わない。この監査でEntry/model/threshold/features/clock変更・fit・Common Holdout/他sealedアクセス・EXIT・昇格・売買は行っていない。

## 再現入力

audit-summary.jsonに集計・入力SHA256を保存。再現scriptは保存artifactの展開ディレクトリを--priorで受け取り、ファイルhashを検証する。

```bash
PYTHONPATH=. python docs/evidence/phase57-entry-contract-review-v1/reproduce.py --prior /path/to/entry-artifact --output /tmp/entry-review-summary.json
```
