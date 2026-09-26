# Phase57 CI Evidence再利用修正 — 結果

修正した6件のCIはPASS。再測定・再学習は0回。保存済み研究結果を再利用した。
PR全体の全緑は未達であり、EXIT Candidate CのFreeze禁止判定は維持する。

## 原因と修正
開始時にPR #587を直接確認したHEADは `e11f8af571a03c7e73f79a77c3964752fd109a08`。
修正実行HEADは `2453a5359aba1e0202fccaebc05c44468c6a9c89`。

6件のworkflowは研究計算・監査後、既存measurement保存先に対する
`test ! -e .../measurement` で失敗していた。
既存成果物を上書きせず、保存済みEvidenceの検証付き再利用に変更した。

科学コード・protocol・Evidence等の既存12,853ファイルをGit objectで比較し、変更・削除時は再利用を拒否する。
原workflowのhashをpinしたmanifestがあるため、元HEADを別checkoutして原監査を実行。
新workflowを原workflowと偽るhash置換は行わない。
新しいreceiptと監査logのみをActions artifactへ保存する。
今後、既存の科学ファイルが変わった場合は自動で再測定せずFAILし、再利用基準のレビューが必要。

## 検証
| 対象 | 結果 | CI |
|---|---|---|
| path | 保存済みEvidence監査・限定テスト PASS | [run 35514885036](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885036) |
| causal | 保存済みEvidence監査・限定テスト PASS | [run 35514885116](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885116) |
| dictionary | 保存済みEvidence監査・限定テスト PASS | [run 35514885063](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885063) |
| pairability | 保存済みEvidence監査・限定テスト PASS | [run 35514885095](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885095) |
| economic | 保存済みEvidence監査・限定テスト PASS | [run 35514885239](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885239) |
| low-high | 保存済みEvidence監査・限定テスト PASS | [run 35514885203](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885203) |
| Predict Tests | 2,949 / 2,949 PASS | [run](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885223) |
| 再利用拒否guard | 7 / 7 PASS | 各修正CI |
| EXIT Freeze detector / 読取監査 / determinism | 12 tests PASS / PASS / PASS | [run](https://github.com/Iam-2squared/ark-terminal/actions/runs/35514885099) |

再利用6件それぞれで、fitCalls・remeasurementCalls・rawCacheRestores・providerRequests・historicalEvidenceWrites = 0。
原Evidenceと研究判定は不変。receiptのmanifest SHA256とlog SHA256は verification.json に保存した。

## 残るFAIL
EXIT CC Freeze Auditは `NEW_LONG_EXIT_CANDIDATE_C_KILL` / `freezeAllowed=false`。
未達gate:
- DIP_REPRICE_OPPORTUNITY_timeOrdered_plus5
- contractLaterBarOrder
- exactRoutedLedger

これは保存先衝突とは別の、研究・契約適合性のblocker。
EXITの採用を許可するためのGate緩和、ledger差し替え、EXIT再開発は実施していない。
したがって「CI全件PASS」「EXIT完成」とは報告しない。

## Entry v2への影響
Entry v2のdecision・model・threshold・feature・研究結果は変更していない。
既存判定 `ENTRY_DEVELOPMENT_INCONCLUSIVE` と非昇格を維持する。
本修正は性能改善ではない。

## 境界
Common Holdout 244 sessionsと追加sealed領域を開封していない。
Frozen Selector・Entry/EXITの売買policy・Capital Allocationは変更なし。
LONG-only / cash-equity-only、Safety 9項目は全false。
PR #587はDraft・未merge。main merge、注文、Paper/Live Tradingは行っていない。
