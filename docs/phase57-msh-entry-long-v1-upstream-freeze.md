# MSH-Entry LONG v1 Final Upstream Freeze — Entry only

**MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH**。Historical=BORDERLINE / Fresh Validation=PENDING / OOS=PENDING_SEALED。モデル・Selector・Candidateを変更せず、既存Evidenceの参照とidentity固定だけを実施。正式Validation PASSではない。

最新のEntry-only指示に切替後はEXIT研究を続行していない。切替前の明示指示でEXIT source確認と診断job開始があったため、全会話のEXIT access/replayを0に書き換えない。停止確認時にjobは完了済みで、結果は未ダウンロード・未閲覧・不使用。追加したEXIT診断用workflow/script/contractは最終branch treeから取り下げ、Git履歴とscope-transition.jsonに経緯を残す。既存EXIT戦略コードの変更は0。

| # | Required item | Evidence / result |
|---:|---|---|
| 1 | Branch | research/phase57-long-only-cash-equity |
| 2 | PR | #587 |
| 3 | Final head | This report is committed with the final Entry-only freeze; exact remote HEAD and final-head CI are reported in the completion message. |
| 4 | Latest main | b7801ce2c13772cbc3f5b51506819c119fe868ea |
| 5 | Selector Freeze commit | 565d74b3dea823581fdb32380113aac5913a248d |
| 6 | Selector payload SHA | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| 7 | Selector Ridge SHA | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| 8 | Candidate Contract SHA | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| 9 | Final model SHA | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| 10 | Final scaler SHA | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| 11 | Threshold | 2.0 unchanged |
| 12 | Decision Score | P1 + 2P2 + 3P3 + 4P4 |
| 13 | Core Features | frozenSelectorRidgeScore / frozenSelectorRidgeRank; optional NONE |
| 14 | State | ENTER / SKIP_THIS_DECISION; WAIT/expiry/persistent SKIPなし; 再Entryなし |
| 15 | LONG-only | JPX cash equity; SHORT/信用/Margin/Leverage0 |
| 16 | Historical period | 2024-09-17–2025-01-09 |
| 17 | Sessions | 76 |
| 18 | Exposure | 全76 direct Development / IN-SAMPLE |
| 19 | Historical Verdict | BORDERLINE |
| 20 | Fresh Validation | PENDING; OOS=PENDING_SEALED |
| 21 | Candidate ENTER | 277 |
| 22 | ENTER/session | 3.6447368421 ≈3.64 |
| 23 | +1 Precision | 86.19% |
| 24 | +2 Precision | 72.93% |
| 25 | +3 Precision | 52.49% |
| 26 | +5 Precision | 30.94% |
| 27 | +1 Preservation | 17.79% |
| 28 | +2 Preservation | 23.52% |
| 29 | +3 Preservation | 27.22% |
| 30 | +5 Preservation | 36.94% |
| 31 | strict30m MAE median | −1.53% |
| 32 | strict30m MAE bad-side5% | −10.26% |
| 33 | strict30m MAE worst | −35.29% |
| 34 | 277 identity SHA | 72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236 |
| 35 | Freeze Manifest SHA | b1755d173e25267f00c9ab89f2ab3f2cfb82bbaf841d2d88dc6ad19421284a32 |
| 36 | Handoff | docs/phase57-msh-entry-long-v1-exit-chat-handoff.md |
| 37 | Entry changes | 0 |
| 38 | Selector changes | 0 |
| 39 | EXIT files inspected | 新Entry-only scope0。前指示では非ゼロ（63 source identitiesをhash、関連source内容も確認）。全会話0とは報告しない。 |
| 40 | EXIT replay | 新scopeの起動0。前指示の診断/replay job1件は停止確認時にcompleted、対象trade数は未閲覧。 |
| 41 | EXIT tuning | 0 |
| 42 | Fresh access | 0 |
| 43 | OOS access | 0 |
| 44 | EXIT outcome access | 新scopeで結果閲覧0。前指示のrunner内計算は実行済み、結果artifactは開いていない。全会話の計算0とは主張しない。 |
| 45 | J-Quants requests | 0 |
| 46 | Yahoo requests | 0 |
| 47 | Other provider requests | 0 |
| 48 | SHORT evaluation | 0 market-data evaluation; generic regressionのsynthetic branch testsとは区別 |
| 49 | Safety | 9 flags all false |
| 50 | Tests | Entry-only7 tests PASS。前段offline regression2886 PASS; 研究再測定なし。 |
| 51 | CI | Final-head Entry Upstream Freeze Integrity / Predict / Research Foundation / existing required CIをremoteで確認しcompletion messageへ記録。 |
| 52 | Final status | MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH |
| 53 | Blocker | None if final-head required CI PASS; inherited prior EXIT activity is disclosed, not hidden in new-scope zero counters. |
| 54 | Exact next action | STOP。別EXIT専用チャットへHandoff。現チャットでEXITを調査・実行しない。 |

PrecisionはCandidate181 / Selector1303のlabelable subset。277 ENTERのうち96件はlabel不能で、そのidentityも除外していない。MAEは既存strict30m HIGH/LOW path診断の参照で、実約定損失ではない。新しいpath解析、prediction、fit、scaler refit、OOF生成は実施していない。CURRENT96とのthroughput差はcadenceを統制した因果比較ではない。

manifest.jsonに正確な既存値・source pins・known limitations・禁止するEntry変更・9 safety flagsを保存。manifest.sha256はファイルbytesのSHA256。historical-enter-identities.jsonは既存277 ENTERを投影したledgerで、Entry timestamp/referenceを変更していない。Global Budget195とFuture20は未消費で維持。

完了後はSTOP。EXIT inventory、compatibility、path、replay、architectureの判断は今回の成果物に含めない。

