# Phase57 — Development Evidence Freeze

2026-09-16 JST

**MSH_ENTRY_LONG_V1_DEVELOPMENT_EVIDENCE_FROZEN**

これは既存Development成果のEvidence Freezeです。Entry Candidate Freezeではありません。
Development判定は **MSH_ENTRY_LONG_V1_DEVELOPMENT_BORDERLINE**、採用thresholdは **NONE** のままです。

## Git / remote / CI

| 項目 | 確認値 |
| --- | --- |
| Repo | Iam-2squared/ark-terminal |
| Branch | research/phase57-long-only-cash-equity |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587) |
| Original local Development commit | `772c4ed40a43590c6198f6f34ab18b5e9226df18` |
| Local offline infrastructure commit | `dcfc87cb503f2760b0cc136d6625294e645406a6` |
| 元remote head | `97617f410a181108ab533632487d05c65f3a9ea8` |
| Development＋offline修正のremote固定／tested head | `4595b609c80bee82d36dc0b0739cb35a9224f3b4` |
| Latest main確認値 | `6b6c4d522cd1863132185463a0aed74bc819be01` |
| main merge | なし |

この報告とmanifestは、上記tested headのCI成功後に追加するattestation-only commitです。
そのcommit番号はGit履歴で特定します。manifest自身へ自身のcommit hashを埋め込む循環参照はしません。
追加commitにも同じCIを要求し、最終headはチャットの最終報告に明記します。

| Required CI at tested head | 結果 |
| --- | --- |
| [Predict Tests / 35056097724](https://github.com/Iam-2squared/ark-terminal/actions/runs/35056097724) | SUCCESS |
| [LONG-only Research Foundation / 35056097730](https://github.com/Iam-2squared/ark-terminal/actions/runs/35056097730) | SUCCESS |
| [Phase52 Daily Dry-Run Persistence / 35056097734](https://github.com/Iam-2squared/ark-terminal/actions/runs/35056097734) | SUCCESS |

研究用4 workflow（L2 Selector Development、New Selector with CURRENT Entry Exit、Missed Opportunity Diagnostic、Selector Capacity Diagnostic）は既存のworkflow_dispatch-only条件によりSKIPPED。
研究を再実行していません。Phase52のmainへのpersist stepもPR条件によりSKIPPED。これらはregression testのSKIPではありません。

## Regression — localとGitHub双方で確認

| Suite | Total | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: | ---: |
| Predict（既存npm testと同一file set） | 2,694 | 2,694 | 0 | 0 |
| Discovery | 26 | 26 | 0 | 0 |
| Python：model/evaluation synthetic | 30 | 30 | 0 | 0 |
| RSS | 89 | 89 | 0 | 0 |
| 重複を除く合計 | **2,839** | **2,839** | **0** | **0** |
| Foundation再実行（Predict内の39件） | 39 | 39 | 0 | 0 |
| Network guard専用probe（別枠） | 6 | 6 | 0 | 0 |

Skipped test names：なし。
既存Project modelの再fitではなく、既存synthetic regressionだけを実施しました。
CIログでも各suiteの件数、exit0、unexpected network attempts0を直接確認しています。

## Network inventory / offline contract

直接原因はP23.17の定数テストが、top-level Yahoo取得を持つ研究runnerをimportしていたことです。
runner・研究ロジックは変更せず、テストは実際のcanonical定数宣言だけをisolated VMで評価するよう変更しました。
既存の全assertionは維持。runner実行、EXIT測定、live fixture取得はありません。

| 実在経路 | 対応 |
| --- | --- |
| Yahoo chart／historical downloader／fetchHistory | 既存fixture・mockを維持、実transportを遮断 |
| J-Quants v2／TDnet | 既存fetchImpl mock、実API取得なし |
| Finnhub | 既存mock、実取得なし |
| GitHub-hosted screener provider | Discoveryのmock、テスト中のdefault fetchは禁止 |
| MarketSpeed／Excel RSS | 既存Python fixture/mock。実端末・注文機能は使用しない |
| HTTP/HTTPS、fetch、HTTP2、DNS、TCP/TLS、UDP、WebSocket | Node/Python guard＋OS filter |

TradingViewを新providerとして追加していません。実行test内でaxios/requests/urllibの外部取得callは見つかりませんでした。
詳細pathは[offline contract](../../phase57-offline-regression-contract.md)に記載。

新しいtest専用flagは`ARK_TEST_OFFLINE=1`の1つ。`ARK_OFFLINE_AUDIT_DIR`は出力先です。
Production defaultは変更していません。Linux x86_64＋system libseccompが使えない環境では実行を拒否します。

- Node/Python guardは実通信前に拒否・記録。例外をcatchしてもexit97で失敗。
- OS filterはInternet socket生成とconnectを禁止し、子プロセスにも継承。
- OS禁止への違反はprocess termination。通信できなかったことを正常provider responseとして扱いません。
- 6 probesでcatch後失敗、IPv4/IPv6のkernel拒否、明示mock成功を確認。
- Fixture/mockの仮想request counterは、実provider requestに計上しません。

| 今回のmarket-data通信 | 件数 | Confidence |
| --- | ---: | --- |
| Yahoo | 0 | CONFIRMED |
| J-Quants | 0 | CONFIRMED |
| その他market-data | 0 | CONFIRMED |
| 通常suiteの予期しない通信試行 | 0 | guardログ確認 |

確認範囲は今回のguarded regression process treesと、その他の作業でmarket-data providerを呼び出していないことです。
GitHub確認・push・CI取得、公式文書閲覧、CI dependency install/artifact uploadはmarket-data通信ではありません。
前工程の不明だった通信件数を遡って0に変更していません。

## Integrity — before / after一致

| 対象 | Before = After SHA-256 |
| --- | --- |
| Frozen Selector payload | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| Ridge artifact frozen参照 | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| Fit Contract | `64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938` |
| OOF compressed artifact | `1428f222b19203bc6736cf4ef3bd3ae18be068f289657e9c2b59ecbe6ec44c34` |
| Development result JSON | `eb5cff588991543e5900d1b7b6827f8e567d72633326168d6508b20f7dc692e0` |
| Original REPORT.md | `ed16a62b3b36fa17eab2bb14203f825ec96d6957e78ee8c15bd9a750a2b816f3` |

Ridge raw artifactは再取得せず、frozen参照SHAを確認しました。Selector payloadはcanonical serializationからSHAを再計算。
4モデル・OOF・decision ledger・全report・original manifestはbyte単位で不変です。
監査はhash-onlyで、model import・prediction・performance再計算はしていません。

`772c4ed4`からのdiffはtest infrastructure、test-only constant extraction、CI設定、追加の監査Evidenceだけ。
禁止された研究変更0。元Development directoryの変更0。Selector/CURRENT Entry/Fit Contract/model/training codeは変更していません。

## 結果・制約の固定

| Threshold | ENTER | Coverage | Development result |
| --- | ---: | ---: | --- |
| 1.0 | 1,086 | 98.82% | 不変・未採用 |
| 2.0 | 143 | 13.01% | 不変・未採用 |
| 3.0 | 23 | 2.09% | 不変・未採用 |

全精度・Preservation・Throughput等の元performance値は元JSONのSHAで保護し、manifestにもそのまま転記。
VerdictはBORDERLINEから変更なし。

1. strict30m true MAEは未取得・未算出。Session MAEで代用しない。
2. CURRENT Entryのstrict30m比較は66 PASS中24件のみ。fully pairedとは呼ばない。
3. Coverageはfuture labelable subset条件付き。実運用coverageではない。
4. 実際の保存済みSelectorは10 decisions/session、概ね30分間隔。5分event再構成なし。
5. Developmentのみ。Validation/OOS性能でもupstream Selectorを含む独立OOSでもない。

元report内のregression BLOCKED記述は当時の履歴として変更せず保存。
今回の追加attestationがそのinfra blockerの解消を証明します。Development性能判定は更新していません。

## Safety / Conservation / STOP

今回のProject model fit、scaler fit、prediction、CV rerun、OOF regeneration、threshold search、Validation/OOS/Project EXIT access、Project SHORT evaluationはすべて0。
Threshold selection = NONE。JPX現物LONG-only、空売り・信用・Margin・Leverageは追加なし。

executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed /
liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed /
transmitted はすべてfalse。元manifestの追加SHORT/Margin/Leverage flagsもfalse。

**Evidence SHA-256:**

`68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead`

対象は`development-evidence-freeze.json`のUTF-8 bytes（末尾LF込み）。自身のhashは別ファイル`evidence.sha256`に保存。

**Exact next action: STOP。** 次の明示指示までCandidate選択・追加研究・Validation/OOS・EXIT・統合へ進みません。
