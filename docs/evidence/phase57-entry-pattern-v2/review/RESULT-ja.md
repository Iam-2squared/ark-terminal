# NEW LONG Entry v2 — 最終結果

研究比較は完了しました。**v2の採用基準は未達、昇格しません。** 判定は `ENTRY_DEVELOPMENT_INCONCLUSIVE`。条件付きMAE・Returnの一部改善はありますが、OpportunityとBUY throughputを失いすぎています。

144日を監査し、候補が存在する142日・Selectorイベント7,100件・5,375 Opportunityから160,608 pattern sampleを構成。内部評価は59日manifestのうち58日・2,155 Opportunityです。候補なしの2025-04-15 / 2025-07-14もinventoryに保持しています。

選択期間20日で固定したPrimaryは `RIDGE_FULL_QUALITY_1m`。評価結果を見たモデルの入れ替えや再学習はしていません。

| 方法 | BUY | +3 Capture | +5 Capture | 30m完全観測 | 30m MFE中央値 | 30m MAE中央値 | 30m MaxDD中央値 | 30m net平均 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0_RETRY_1m | 1963 | 85.28 | 87.50 | 1365 | 1.09 | -1.23 | -2.13 | -0.06 |
| B1_WAIT5_1m | 1899 | 73.19 | 75.98 | 1343 | 1.00 | -1.18 | -2.04 | -0.05 |
| B2_E5_V1_PRESERVED | 1645 | 71.75 | 74.51 | 1243 | 1.10 | -1.21 | -2.14 | -0.07 |
| RIDGE_FULL_QUALITY_1m | 1020 | 40.74 | 41.91 | 695 | 1.12 | -1.11 | -2.01 | 0.02 |

価格指標・Captureは%。30m/60mは昼休みを除くsession-active時間。Path/Returnは完全観測ケースに条件付けた値で、BUY母集団が異なります。v1旧wall-clock数値は上書きしていません。

- 公平なB0に対し、BUY throughputは52.0%。+3 Capture差は-44.55ポイント、+5差は-45.59ポイント。
- +3 capturedは310/761、+5は171/408。+3 missedのうち402件、+5 missedのうち206件は未Entryです。
- LOW_THEN_HIGH保持率も、+3はB0 87.2% → v2 41.8%、+5は90.4% → 42.9%でした。
- B0自体もCapture90%には届いていません。ただし、それを基準緩和の理由にはせず、v2はB0にも大幅に劣るという結果をそのまま保存します。

## P0と計測基盤

- 評価期間の11:30 selection 201件は、v2では空grid 0件。全144日では空grid 600→90件。残る90件は取引時間延長前の15:00 selectionで、残り取引時間がないsession境界です。
- B0/モデルは同じ1m・5m grid、参照価格freshness、実1m Open＋5bps、未約定retry契約を共有。MODEL_WAITと価格欠測・未約定・EXPIREを分離しました。
- 前日full observed1m・当日closed prefix、476個の固定numeric/sequence/context特徴を構成。欠測とpartialを保持し、価格補間はしていません。full observedは全minute存在の保証ではありません。
- 1mは選択モデルの5mよりCaptureを保ちましたが、公平baselineとの差は依然大きく、成功とは判定しません。全モデル・固定wait・ablationは詳細表に保存しました。

## 検証と制約

- focused tests 334 PASS、既存regression 2949 PASS。基盤・測定・REPORT/グラフは2回生成一致。このread-only reviewも2回生成一致。
- v1 BUY時刻・価格・Captureは一致確認済み。Frozen Selector / Dictionary Gateは変更なし。Common Holdout244未開封、9 Safetyすべてfalse。NEW EXIT、Capital Allocation、merge、売買、昇格は行っていません。
- 本研究は再利用Development内の診断です。独立OOSではありません。Frozen upstreamの同日Daily metadata制約は継承し、そのprospective PITを独立認証したとは主張しません。
- 継続価値は実現した将来最大品質を教師にした楽観的proxyで、Bellman最適停止の解ではありません。Dictionary/Pattern Memoryの追加評価は今回のPrimaryから分離しています。
- 既存の別研究CIに失敗が残るため、v2専用CIの成功をPR全体のgreenとは扱いません。

測定HEAD: `4bf0b05ee916f898f5561d7410753ea2b7586c25`。専用CI: https://github.com/Iam-2squared/ark-terminal/actions/runs/35510863265。

[全方式の30m/60m比較・可用性層別](REPORT.md) / [グラフ付き本体REPORT](../ci-result/REPORT-ja.md) / [raw review](review.json)

