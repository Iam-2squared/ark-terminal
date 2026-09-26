# DROP/PULLBACK 1分State再認識 — 測定完了・手動STOP

2026-09-23 JST / PR #587 / research/phase57-long-only-cash-equity

## 結論

事前固定した「DROP/PULLBACKだけState再判定を5 active-minuteから1 active-minuteへ変更する」実験を完了した。専用CI、2回replayのbyte一致、凍結資産保全、通常回帰がPASSした。

結果は `PASS_CLEAR_IMPROVEMENT`。これは不採用だった5分版State v3に対する事前固定の相対改善Gateを満たしたという意味である。Immediate超え、平均EntryPosition <=0.25達成、Entry全体完成、Fresh/OOS合格、実運用昇格を意味しない。今回の単一実験でSTOPし、新しい仮説へ進まない。

## Git identityと変更範囲

- 開始時に再取得したHEAD: `5b47b975b1d833b3992e56ee7dce4010e58e17bb`
- テスト・全件測定対象HEAD: `8c256ff98d365d01c7150afe193686f020e2026c`
- 開始時点で1分版実装は既に存在したが、元run `35815694968` は静的因果性監査でFAILしていた。
- 不具合は、凍結済みintent関数の説明文「never sees ... outcome」の単語まで禁止入力として検出していたこと。説明docstringだけをAST上で除外し、実行コード・キー・変数・属性等は元の禁止語で監査するよう修正した。実際の禁止入力を通す変更ではない。
- 監査回帰とfuture-suffix invarianceテスト、target T0一致、全non-targetレコード一致のassertionを追加した。研究ロジックや成功基準は変更していない。
- 最終報告等の後続commitはEvidence追加のみで `[skip ci]`。CI合格は上記の実装HEADに結び付く。報告commitそのものを再測定済みとは呼ばない。

研究上の変更は、T0がDROP/PULLBACKの1,757 OpportunitiesだけのState確認頻度。全体2,155件を維持した。State v3の9分類、前営業日＋当日closed-price入力、10分recent/priorの定義、既存6 SignalのOR、上昇系T0即BUY、非対象policy、fill proxy、Oracle evaluatorは凍結したまま。新しい時間fallbackはない。

## DROP/PULLBACK対象群 1,757件

| KPI | 5分版State v3 | 1分版 | 差 |
|---|---:|---:|---:|
| Fill | 1,323 | 1,406 | +83 |
| Fill率 | 75.30% | 80.02% | +4.72pp |
| NO ENTRY | 434 | 351 | -83 |
| Delay平均 | 10.90分 | 8.42分 | -2.47分 |
| Delay中央値 | 10分 | 7分 | -3分 |
| EntryPosition <=0.10 | 85 / 1,317 = 6.45% | 113 / 1,396 = 8.09% | +1.64pp |
| EntryPosition <=0.25 | 308 / 1,317 = 23.39% | 362 / 1,396 = 25.93% | +2.54pp |
| EntryPosition <=0.50 | 650 / 1,317 = 49.35% | 688 / 1,396 = 49.28% | -0.07pp |
| +3 Capture | 389 / 620 = 62.74% | 426 / 620 = 68.71% | +5.97pp |
| +5 Capture | 211 / 328 = 64.33% | 232 / 328 = 70.73% | +6.40pp |

Position達成率の分母は、各policyでFillでき、かつ既存Oracle評価が可能だったケース。1,757件全体を分母にした率ではなく、policy間で分母も異なる。NO ENTRYや評価不能を母集団から削除していない。Fill/Captureと併記し、評価可能なFillだけの良化を全体の成功へ読み替えない。

## 共通Fillでのpaired比較

差は1分版 minus 5分版。買値改善だけは正値が安いEntryを示す。指標ごとに評価可能数が異なる。

| 指標 | paired N | 差の平均 |
|---|---:|---:|
| 買値改善 | 1,323 | +0.0472% |
| EntryPosition | 1,317 | -0.00747 |
| Low→Entry距離 | 1,317 | -0.0512pp |
| Delay | 1,323 | -2.75分 |
| Entry→Later High余地 | 1,243 | +0.0584pp |
| Range Retention | 1,243 | +0.9004pp |
| 30分MFE | 982 | +0.0622pp |
| 30分MAE | 982 | +0.0055pp |
| 60分MFE | 791 | +0.0656pp |
| 60分MAE | 791 | -0.0459pp |

60分MAEは僅かに悪化しており、すべての指標が改善したわけではない。paired差の中央値は上記指標すべて0。58 sessionsの買値改善session-equal bootstrapの95% percentile範囲は [+0.00499%, +0.08374%] だが、保存データを繰り返し使うDevelopment研究の記述統計であり、confirmatory/OOSの証明ではない。

事前固定Gateは、<=25%率+2pp以上、paired Position改善、paired Low→Entry改善、Fill/+3/+5 Captureの各低下が-2pp以内、causality PASSの全7項目。今回7/7を満たした。結果を見てGateを緩和していない。

## 絶対水準とImmediate比較 — 未達の部分

25.93%とは「Low→Highレンジの25%以内で入れたケースの割合」であり、「平均Entry位置が25%になった」という意味ではない。

| 同じDROP/PULLBACK対象群 | Immediate | Entry v1 | 5分版State v3 | 1分版 |
|---|---:|---:|---:|---:|
| <=25%達成率 | 36.84% | 27.28% | 23.39% | 25.93% |
| 上記分母 | 1,569 | 1,488 | 1,317 | 1,396 |
| EntryPosition平均 | 0.64194 | 0.64260 | 0.66245 | 0.66559 |
| EntryPosition中央値 | 0.40890 | 0.46607 | 0.50833 | 0.50981 |
| Fill率 | 90.95% | 85.60% | 75.30% | 80.02% |
| +3 Capture | 84.68% | 69.35% | 62.74% | 68.71% |
| +5 Capture | 87.80% | 73.78% | 64.33% | 70.73% |

各policy全体の平均Positionは改善していない。一方、共通評価ケースのpaired差は改善している。新しくFillされたケースが加わるため、異なる集合の平均差とpaired差を混ぜて解釈してはいけない。平均EntryPosition約0.666、中央値約0.510であり、Low側25%というユーザーの絶対的な目標にはまだ遠い。Immediateにも今回の主要指標では届いていない。

## 全2,155件の結果

| Policy | Fill | Fill率 | 平均EntryPosition | +3 Capture | +5 Capture |
|---|---:|---:|---:|---:|---:|
| Immediate | 1,963 | 91.09% | 0.65399 | 85.28% | 87.50% |
| Entry v1 | 1,857 | 86.17% | 0.64354 | 71.22% | 75.25% |
| 5分版State v3 | 1,681 | 78.00% | 0.67283 | 67.02% | 68.38% |
| 1分版 | 1,764 | 81.86% | 0.67487 | 71.88% | 73.53% |

全体のCapture分母は+3が761、+5が408。Position評価分母は順に1,931 / 1,839 / 1,672 / 1,751。全体NO ENTRYは391件。変更対象以外の398件は、experiment識別子を除き凍結済み5分版の全レコードと完全一致した。

## Causality / tests / CI

| 検証 | 結果 |
|---|---|
| 対象State判定 | 53,712、future violation 0 |
| Signal closed-bar検査 | 65,910 / 65,910 PASS |
| target T0 State一致 | 1,757 / 1,757 |
| 非対象レコード完全一致 | 398 / 398 |
| Oracle/Outcomeのdecision利用 | 0、intent固定後にEvaluatorを処理 |
| 専用・凍結回帰Python tests | 90 / 90 PASS |
| 2回の全件replay | 全出力file byte-identical |
| Dedicated CI | run 35818555587 / job 107045547187 PASS |
| 通常回帰 | run 35818556861 PASS、5 suite合計2,949 / 2,949 |
| 通常回帰内訳 | Predict 2,765 / discovery 26 / foundation 39 / Python 30 / RSS 89 |
| LONG-only foundation | run 35818555691 PASS |
| Provider新規取得 / protected data開封 | 0 / 0 |
| Safety9 | 全false |

通常回帰2,949は複数suiteの合計で、Predict単独は2,765。専用90との間にはテスト重複があり、独立テスト数として足し合わせない。PR全体GREENとは判定していない。

先行push run 35818543146は後続PR runに置き換えられ、replay B中にcancelledになった。cancelledをPASSに読み替えていない。正式完走は35818555587。先行runで完成したreplay Aと正式runの全measurementファイルもローカルでbyte一致を確認した。

## Evidence identityと保存場所

- 固定結果JSON: `RESULT_SUMMARY_R1.json`
- CI/全測定ファイルhash: `validation/CI_RECEIPT_R1.json`
- 修理前の失敗記録: `validation/AUDIT_REPAIR_R1.md`
- 全件レコード・元summary・paired records: Actions artifact `10732168448`, producing run `35818555587`
- ZIP SHA256: `74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8`
- 元summary SHA256: `8de015aeaf9b80d1d375b409ea597fa6dee24d767a72aeabdd5918faac367ea9`
- manifest SHA256: `940a4a76bb51b515d446b35152345863aeff151b9823cf0e20dba6740f58468b`
- ZIP download後のSHAとmanifest全6項目の内容hashを照合済み。
- Actions artifactの期限は2026-12-22T04:29:43Z。全件レコードをGitに永久保存したという主張はしない。固定集計・報告・receiptはRepoへ保存。

## STOP

1分確認により5分確認の遅延に起因する取り逃しを一部減らせるというDevelopment Evidenceが得られた。ただし残る失敗原因をこの結果だけで確定しない。

State classifier、Signal、BUY/WAITルールの次の変更、Volume/Dictionary、EXIT/Capital、新規provider、protected評価、main merge、実売買には進んでいない。毎時自動研究は再開しない。この実験の結果を人間が確認するまでSTOP。
