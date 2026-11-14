# MSH-Entry LONG v1 — EXIT専用チャットへのUpstream Handoff

**MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH**。Historical=BORDERLINE、Fresh Validation=PENDING、OOS=PENDING_SEALED。今回はEntryの固定と引継ぎだけでSTOPする。この文書はEXIT研究の実行指示ではない。

| Identity | 固定値 |
|---|---|
| Repo / Branch / PR | Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / #587 |
| Entry Freeze Manifest | docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/manifest.json |
| Manifest SHA256 | b1755d173e25267f00c9ab89f2ab3f2cfb82bbaf841d2d88dc6ad19421284a32 |
| Selector freeze commit | 565d74b3dea823581fdb32380113aac5913a248d |
| Selector payload SHA | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| Selector Ridge SHA | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| Candidate Contract SHA | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| Model SHA | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| Scaler SHA | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| Global Budget SHA | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |
| Historical dataset contract SHA | 4a1d3e4ec4229d32ee2a50678db8fe3f8739abb3530df521e3036d201e75b441 |
| Historical session-list SHA | de4a4264a7d78446ff01f72c2f927cc29ec45b18126068ca2e9dc2cfe16c5483 |
| 277 ENTER identity SHA | 72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236 |

E[L]=P1+2P2+3P3+4P4、threshold2.0。未ENTERのsymbol-sessionでE[L]>=2.0ならENTER、それ以外はSKIP_THIS_DECISION。CoreはfrozenSelectorRidgeScore / frozenSelectorRidgeRankだけ。Decision PriceはREFERENCE_ONLY。Optional、WAIT、expiry、persistent SKIPなし。同一symbol-sessionの再Entryは禁止。

JPX現物LONG-only。SHORT・空売り・信用・Margin・Leverageは禁止。固定decision時刻は09:30/10:00/10:30/11:00/11:30/13:00/13:30/14:00/14:30/15:00 JST。5分decisionへ変更しない。Entry timestampは保存済みSelector decision timestampと同一のhistorical reference instantで、実測約定遅延ではない。decisionPriceはその判断時点の保存referenceで、broker fillではない。PIT情報のみをfeatureへ使用する。

277件のledgerはhistorical-enter-identities.json。selectorEventId / symbolSessionId / sessionDate / symbol / decisionTimestamp / decisionPriceを持つ。既存predictionのENTER行と既存入力のidentity joinによる投影で、predictionの再実行ではない。277 unique symbol-sessions、76 sessions、2024-09-17–2025-01-09。全期間がfinal Entry modelの直接Development / IN-SAMPLE。FreshまたはOOSへ再分類しない。

既存測定のHIGH Precision（labelable181件）は+1/+2/+3/+5=86.19/72.93/52.49/30.94%。Selector baselineの分母は1303。Preservation=17.79/23.52/27.22/36.94%。ENTER277=3.64/session。CURRENT96=1.26/sessionはcadenceの違うsupporting reference。Quality・Preservation・ThroughputはHistoricalで支持されるが、独立一般化の証明ではない。

主要残リスクはstrict30m MAE median−1.53%、adverse5th percentile−10.26%、worst−35.29%。181件で算出した既存値の参照であり、今回の再計算ではない。96 ENTERはstrict30m label不能。Observed-minuteの疎な5m aggregationを含むため、完全なtick pathや実現損失を保証しない。

Entry threshold/model/scaler/features/label/target/state/WAIT/expiry/score/candidate selectionは変更禁止。Global fresh budget195、Future20を保護し、今回の消費0。すべてのexecution/broker/Excel/RSS/live/paper/promotion/production/transmittedフラグはfalse。

前の指示で開始したEXIT作業は最新指示で終了した。commit1435f044344d509fb9f01e9e55d4f51c8b9f75fdに診断準備が存在し、run35087975004は停止確認時に完了済みだった。結果は未ダウンロード・未閲覧・Freeze判断への使用なし。診断workflow/scriptは最終treeから取り下げ、経緯をscope-transition.jsonに保存。新しいチャットへこの結果を採用済みEvidenceとして渡さない。

**次の正確な作業:** このHandoffとmanifestのSHAをEXIT専用チャットが照合する。EXIT調査・測定・設計の範囲は、そのチャットで別途指示を受けてから決める。現チャットはSTOP。
