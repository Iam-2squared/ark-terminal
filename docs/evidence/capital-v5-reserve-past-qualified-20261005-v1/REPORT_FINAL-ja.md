| 100万円→20 sessions | V5 | R | R−V5 |
|---|---:|---:|---:|
| Min | 1,082,366円 | 未実行 | 未評価 |
| Mean | 1,190,646円 | 未実行 | 未評価 |
| Median | 1,199,154円 | 未実行 | 未評価 |
| Max | 1,297,031円 | 未実行 | 未評価 |
| 2x hit | 0/19 | 未実行 | 未評価 |

## 🛑 判定：PAST_SUPPORT_NOT_ESTABLISHED

元OOFの8 blockすべてで過去適格性が不成立でした。Rのprimary Replay、実行claim、独立R再構築は実施せず、固定STOPしました。V5を保持します。研究候補の提案・Capital候補選択・Champion更新・注文・main適用はありません。

上表のV5は保存原19窓の表示参考値です。R未実行を0円・0勝・V5同値へ補完していません。38 session連結系列の対応する20-session正規化窓であり、独立reset試験・完全calendar月・全市場営業日の成績ではありません。

| 対応比較 | 結果 |
|---|---|
| better / equal / worse（19窓） | 未評価 / 未評価 / 未評価 |
| 最悪のR−V5差 | 未評価 |
| V5全系列 minute-MTM MaxDD | 10.225325% |
| R全系列・各20窓 MaxDD | 未評価 |

## 📋 全E/Q/R1 Gate

| Gate | R判定 | 理由 |
|---|---|---|
| E0 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| E1 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| E2 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| E3 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| E4 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q1 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q2 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q3 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q4 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q5 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| Q6 | NOT_EVALUATED | 過去支援不成立によりR未実行 |
| R1 | NOT_EVALUATED | 過去支援不成立によりR未実行 |

事前の因果接続・保存case照合はPASSですが、R最終Q6 PASSやCapital改善とは扱いません。NO_EFFECT_PROVENも主張しません。全prefix同値走査を実施していないためです。

## 🕰️ 過去だけの8適格表

| block | 先行OOF session | S N/session/block | F N/session | S U5/U10 | S平均net return | session proxy CI95% | 不成立Hi | 適格 |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 0 | 0/0/0 | 0/0 | 0/0 | — | 未評価（COLD） | H0, H1, H2, H3, H4, H5, H6 | false |
| 2 | 5 | 2/2/1 | 17/4 | 0/0 | -3.444705% | [-3.534754%, 0.000000%] | H1, H2, H3, H4, H5, H6 | false |
| 3 | 10 | 5/5/2 | 33/9 | 0/0 | -1.359184% | [-1.993491%, 0.254830%] | H1, H2, H3, H4, H5, H6 | false |
| 4 | 15 | 7/7/3 | 56/14 | 0/0 | -1.736371% | [-1.975618%, 0.074163%] | H1, H2, H3, H4, H5, H6 | false |
| 5 | 20 | 10/10/4 | 80/19 | 0/0 | -3.369749% | [-3.727499%, -0.303353%] | H1, H2, H3, H4, H5, H6 | false |
| 6 | 25 | 15/15/5 | 98/24 | 0/0 | -2.742993% | [-3.307211%, -0.417310%] | H1, H2, H3, H4, H5, H6 | false |
| 7 | 30 | 18/18/6 | 118/29 | 1/0 | -3.832169% | [-4.167570%, -0.799403%] | H1, H2, H3, H4, H5, H6 | false |
| 8 | 35 | 21/21/7 | 134/34 | 2/1 | -2.534989% | [-3.202704%, 0.180448%] | H2, H3, H4, H5, H6 | false |

block8はSの件数条件H1を通りましたが、H2/H3/H4/H5/H6を通りませんでした。先行blockのSのみを利用し、当blockの3件を加えた全S24件で判定していません。block2–8の必要S/F outcome unknownは全て0、block1はCOLD_ABSTAINです。

| block | 不足S N | 不足S session | 不足S block | 不足F N | 不足F session | 不足U5 | 不足U10 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 10 | 2 | 20 | 8 | 2 | 1 |
| 2 | 8 | 8 | 1 | 3 | 4 | 2 | 1 |
| 3 | 5 | 5 | 0 | 0 | 0 | 2 | 1 |
| 4 | 3 | 3 | 0 | 0 | 0 | 2 | 1 |
| 5 | 0 | 0 | 0 | 0 | 0 | 2 | 1 |
| 6 | 0 | 0 | 0 | 0 | 0 | 2 | 1 |
| 7 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

各Sは当時の原head・原参照・V5 native snapshotから、score条件を満たし元singleton allocationで初めて実数量が出るproposalをsessionあたり1件だけ固定したものです。台帳へ介入せず、outcome join前にhash/manifestをcommitしactual GETしました。Sはstandalone proposal supportであり、historical policy Replay・実際の回収PnLではありません。

label成熟は保存teacherのpotential horizon/capture complete、Frozen EXIT/EODのCOMPLETE・source/release上限から、元session15:31を保守的な境界として後続block09:00と比較しました。既存のclosed-bar assumed availability契約に基づく証明です。実際の過去provider配信時刻はUNKNOWNで、そこまでの保証へ拡張していません。warmup・training resubstitution・同block・後続block outcomeは資格判定へ使用していません。

## 🔍 block8の品質比較（過去S21対過去F134）

| target | 過去S | 過去F | 条件 | 結果 |
|---|---:|---:|---|---|
| U5 | 2/21 | 45/134 | S率≥F率 | FAIL |
| U10 | 1/21 | 24/134 | S率≥F率 | FAIL |
| U3 | 4/21 | 68/134 | S率≥F率 | FAIL |
| Weak | 12/21 | 53/134 | S率≤F率 | FAIL |
| realized_nonpositive | 14/21 | 74/134 | S率≤F率 | FAIL |

S平均returnはS件数を分母とし、bootstrapのsession proxyは先行OOF session全体を分母として空sessionを0にしています。両者は分母が異なります。PCG64、seed=571005310+b、1999回、linear percentileを固定し、保存countsから独立再集計しました。新たな抽出・閾値探索は行っていません。

## 🌊 activity waterfall

| 段階 | N | session | block | 補足 |
|---|---:|---:|---:|---|
| 構造Reserve | 181 | 35 | 8 | 保存snapshot、state mutationなし |
| native picked空 | 167 | 32 | 8 | 保存snapshot、state mutationなし |
| raw pP先頭 | 158 | 32 | 8 | 保存snapshot、state mutationなし |
| score条件 | 52 | 26 | 8 | 保存snapshot、state mutationなし |
| 過去適格block | 0 | 0 | 0 | 適格blockなし |
| 適格状態のnative数量≥100 | 0 | 0 | 0 | 適格blockなし |
| 初回差分 | 未実行 | 未実行 | 未実行 | prefix走査0 |
| actual例外funded | 0 | 0 | 0 | R Replay未実行 |
| 完全決済 | 未実行 | 未実行 | 未実行 | R台帳なし |
| 診断：score条件＋snapshot数量≥100 | 41 | 24 | 8 | actual BUYではない |
| 過去Sの固定集合 | 24 | 24 | 8 | 最初のfundable proposalだけ |

構造Reserveは181行/170 batch、picked空は167行/158 batchです。選んだ158 snapshotのうち、score条件を無視した単なる数量診断では126件がfundable、32件がquantity0でした。score通過52件のうち41件は数量が出ますが、過去支援不成立のため実行へ進みません。

| abstain・非選択理由 | N | session | block |
|---|---:|---:|---:|
| native_picked_nonempty | 14 | 11 | 7 |
| raw_pP_not_first_no_backfill | 9 | 8 | 5 |
| WINNER_RANK_BELOW_3_4 | 105 | 30 | 8 |
| BOTH_QUALITY_LOW | 1 | 1 | 1 |
| score_pass_quantity0 | 11 | 9 | 6 |
| later_fundable_session_collection_closed | 17 | 12 | 6 |
| PAST_UNQUALIFIED_score_pass | 52 | 26 | 8 |
| packet_or_reference_unknown | 0 | 0 | 0 |
| label_unknown_in_required_past_S_F | 0 | 0 | 0 |

理由は段階ごとの分母を持ち、session数も重なります。PAST_UNQUALIFIEDはscore通過52件すべてに適用されます。quantity診断の失敗理由は別に示します。

| snapshot数量0の診断理由 | N | session | block |
|---|---:|---:|---:|
| CAP_BELOW_1LOT | 1 | 1 | 1 |
| CASH_AVAILABLE_TARGET_BUDGET_BELOW_1LOT | 27 | 13 | 7 |
| CASH_BELOW_1LOT | 4 | 4 | 3 |

「cashで100株を払える」と「target/cap/budgetを満たして元allocationで数量が出る」を分けました。先頭score失敗から下位へ乗換え、quantity0後の同batch backfill、強制1lotはありません。

## 🧪 原score接続・誤排除の診断

| 母集団 | N | known/unknown | U5 | U10 | Medium3–<5 | Weak<2 | realized≤0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| structural181 | 181 | 181/0 | 30 | 10 | 22 | 94 | 96 |
| native_picked_nonempty | 14 | 14/0 | 3 | 1 | 3 | 7 | 6 |
| raw_PP_not_first | 9 | 9/0 | 2 | 1 | 1 | 5 | 4 |
| first158 | 158 | 158/0 | 25 | 8 | 18 | 82 | 86 |
| score52 | 52 | 52/0 | 9 | 5 | 8 | 25 | 32 |
| score_rejected106 | 106 | 106/0 | 16 | 3 | 10 | 57 | 54 |
| score_pass_qty0 | 11 | 11/0 | 2 | 1 | 1 | 6 | 8 |
| score_and_snapshot_qty100_41 | 41 | 41/0 | 7 | 4 | 7 | 19 | 24 |
| later_fundable_not_added_to_S | 17 | 17/0 | 5 | 3 | 5 | 6 | 7 |
| first_per_session_S24 | 24 | 24/0 | 2 | 1 | 2 | 13 | 17 |

新score条件で除外された106件にはU5が16件、U10が3件、Mediumが10件含まれます。全対象ID・原潜在値・費用込みreturn・理由はPRIVATE内の評価専用明細へ保存しました。これらは実際に失われたR取引や回収の因果効果ではありません。原1028、V5 funded150、Reserve181のmaskは異なり、原AUC/原bootstrapは再計算せず既存certificateをhash/body reuseしました。

## ↔️ impact table

| 分類・項目 | 件数 | 数量 | PnL | 判定 |
|---|---|---|---|---|
| V5_COMMON | 未評価 | 未評価 | 未評価 | R未実行 |
| V5_ONLY | 未評価 | 未評価 | 未評価 | R未実行 |
| R_ONLY | 未評価 | 未評価 | 未評価 | R未実行 |
| 元native取引の失われた件数/数量/PnL | 未評価 | 未評価 | 未評価 | R未実行 |
| 追加Medium/U5/U10/Weak/realized損益 | 未評価 | 未評価 | 未評価 | R未実行 |
| 後続の新MAX3/cash/Reserve miss | 未評価 | 未評価 | 未評価 | R未実行 |
| 追加Winner−既存Winner loss | 未評価 | 未評価 | 未評価 | R未実行 |

元V5の保存取引150件・Loser82件はR新成績へ転記していません。単なる追加でLoser82件を残す場合Q3はFAILになる契約をsynthetic25で確認しました。「回収だけでLoserを消した」「損失防御成功」「総合採用」とは報告しません。

## 📉 保存V5の各20窓DDと未実行R

| 窓 | start→end | V5 MaxDD | R MaxDD |
|---:|---|---:|---|
| 1 | 2025-06-27→2025-07-29 | 10.225325% | 未評価 |
| 2 | 2025-06-30→2025-07-30 | 8.043720% | 未評価 |
| 3 | 2025-07-01→2025-07-31 | 8.043720% | 未評価 |
| 4 | 2025-07-02→2025-08-01 | 8.043720% | 未評価 |
| 5 | 2025-07-03→2025-08-04 | 8.043720% | 未評価 |
| 6 | 2025-07-04→2025-08-05 | 8.043720% | 未評価 |
| 7 | 2025-07-07→2025-08-06 | 8.043720% | 未評価 |
| 8 | 2025-07-08→2025-08-07 | 8.043720% | 未評価 |
| 9 | 2025-07-09→2025-08-08 | 8.043720% | 未評価 |
| 10 | 2025-07-10→2025-08-12 | 8.043720% | 未評価 |
| 11 | 2025-07-15→2025-08-13 | 8.043720% | 未評価 |
| 12 | 2025-07-16→2025-08-14 | 8.043720% | 未評価 |
| 13 | 2025-07-17→2025-08-15 | 5.807349% | 未評価 |
| 14 | 2025-07-18→2025-08-18 | 5.807349% | 未評価 |
| 15 | 2025-07-22→2025-08-19 | 9.476170% | 未評価 |
| 16 | 2025-07-23→2025-08-20 | 9.476170% | 未評価 |
| 17 | 2025-07-24→2025-08-21 | 9.476170% | 未評価 |
| 18 | 2025-07-25→2025-08-22 | 9.476170% | 未評価 |
| 19 | 2025-07-28→2025-08-25 | 9.476170% | 未評価 |

V5の厳密19窓growth/amount/DD分数はPAIRED20_EXACT.json・CSVへ保存しました。R値はnull/空欄とNOT_EXECUTED理由を持ちます。未実行R曲線や台帳は生成していません。

## ✅ 独立監査・実施量・修復

| 項目 | 結果 |
|---|---:|
| 独立pre-main検査 | 119,061 checks / mismatch0 |
| 保存native batch / 全入力行 | 907 / 1,039 |
| native gate行 / filter-only行 | 494 / 545 |
| singleton primary診断 / 独立照合 | 158 / 158 |
| 過去proposal S / 適格表 | 24 / 8 |
| 保存bootstrap統計の独立再集計 | 13,993 |
| 必須synthetic | 28/28 PASS |
| first-divergence 主/独立走査 | 0 / 0（条件で未実行） |
| R primary市場Replay / 独立R再構築 | 0 / 0 |
| V5/OFF/control/旧arm市場Replay | 0 |
| new fit/refit/current inference/教師再生成 | 0 |
| 原AUC/原bootstrap/Bridge診断再計算 | 0 |
| provider/Fresh/Claude/注文/main merge/force push/自動昇格 | 0 |
| dispatch/cancel | 0 / 0 |

独立側はPrimary gate/allocation/evaluatorをimportしていません。同じ研究者が別実装し、元score・参照・source・Decimal28を共有するため、完全盲検の外部監査ではありません。R未実行なのでBUY–SELL/cash/MTM/日次/19窓の独立R再構築も存在しません。

技術修復は3件です。P2のnp.bool_ JSON serializationは保存countsから書出しを復旧し、乱数再抽出・新しい資格表実験をしませんでした。P3では保存gate_decisionsにfilter-only行がないschemaを検知し、P1のzip照合不足を保存DECISIONSのidentity joinで補完しました。synthetic case12のDecimal import欠落は失敗code/receiptを保存後、期待値を保ちcase12以後だけ再開しました。全失敗receiptと原code hashを残し、policy・母集団・閾値・Gate・許容差を変更していません。

## 🔒 Authority・復旧・Safety

作成時刻：2026-10-05T22:52:40.715497+09:00。branch：capital-v5-reserve-past-qualified-20261005。strategy parent：710656491be06235901b45c50a8b5cbd714ba4eb。Bridge最新actual GETは0bb1173854217e5533d01dff13d1d9e1db98312b、F9 closureは保持しました。新branchはV5 parentから作り、旧cycleを再開していません。既存の有効なR execution claim/closureは開始時にありませんでした。

正本DIRECTIVEはGitHubから全文をactual GETし、34,119 bytes、SHA256=1df3aea1ebadacff7b0a329ddfb580cfcc1f24e33f50a17885b89a99e27688c3、git blob=fa81b475448fe577583d3e1b0ee150ed8165e661を照合しました。Bridge PRIVATEは28,110,631 bytes、SHA256=a31eae5a5aea92bcd96bcc093e8379f588d801faee7858b2265a1de150401686、ZIP CRC・全298 payload hashを検証しました。packet1039とhead別32参照、native snapshots・原決済source・旧OFFreceiptを再利用しています。

workflow treeは既存監査と同一で、新branch/pathのpush適合0を検査しました。[skip ci]だけを証明にしていません。workflow dispatch/cancelや無関係job操作はありません。

| Safety flag | value |
|---|---|
| executionAllowed | false |
| brokerWriteAllowed | false |
| excelOrderWriteAllowed | false |
| rssOrderFunctionAllowed | false |
| liveTradingAllowed | false |
| paperTradingAllowed | false |
| automaticPromotionAllowed | false |
| productionUpdateAllowed | false |
| transmitted | false |
| productionReady | false |

activeCapitalChampion=V5、selectedCapitalCandidate=null、selectedResearchCandidate=null、championUpdated=false。Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。past-onlyの二段目decision artifactであり、既視DevelopmentをFreshへ戻しません。新head fit0でも適応・過学習がないと主張しません。将来非劣化・無損失保証はfalseです。

CLOSURE.jsonと全checkpoint/WORK_STATUS_LOGをappend-only保存しました。P0–P3は実測検証済み、P4は固定STOP判断、P5/P6は条件により未実行、P7は報告・PRIVATE保存です。このcycleでthreshold変更・別arm・Replay再試行へ移らないDO_NOT_REPEATを保存します。

添付表示用PNGはローカルに存在しませんでしたが、必須のnative MTM源は実ファイル・hashで認証できています。未取得PNGのhash一致やRグラフは推測していません。
