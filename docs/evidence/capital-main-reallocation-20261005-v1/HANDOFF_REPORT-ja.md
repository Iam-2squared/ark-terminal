# 📦 Ark Terminal — Capital 引き継ぎ確認・現在地と次の方針

作成実時計: **2026-10-05T23:50:25+09:00**  
Repository: Iam-2squared/ark-terminal  
作業branch: capital-main-reallocation-20261005  
引き継ぎ元: 220e0d8863978f5d82d0d83189d473252efda146  
状態: **HANDOFF_COMPLETE / MAIN_CAPITAL_PRECHECK_READY**

## 🎯 今回確定した目的

**100万円を20 sessionsで約200万円へ増やすことを、Capitalの目標とする。** V5は比較基準。目標達成・完成・新candidate採用の証拠にはしない。

Selector・Entry・EXITは完全凍結。今回の対象はCapitalの購入可否・実数量・資金配分の接続である。AUC、U5/U10、Weak、Loserの件数は最終資産の増減を説明する補助指標であり、単独の採用条件にしない。

見出しと絵文字、数値の表を使う。Claudeは独立した意見が実質的に必要なときだけ使う。GitHubに実時計JST、現在地、完了内容、未実行、次の方針、source/commit/hashをappend-onlyで残す。旧研究の再実行を新研究として扱わない。

今回のユーザー指示が現在の作業権限である。旧handoffのnew_work_authorized=falseは作成時点の状態であり、この引き継ぎ作業を止める新しい承認要求にはしない。一方、旧指示書に残る過去の実行許可で閉鎖済み研究を再開しない。

根拠: [最新handoffのGitHub正本](https://github.com/Iam-2squared/ark-terminal/blob/220e0d8863978f5d82d0d83189d473252efda146/docs/evidence/capital-v5-reserve-past-qualified-20261005-v1/designer-review/20261005T231403_JST_NEW_CHAT_HANDOFF.json)。

## 💴 保存済みV5と目標の距離

次表は、連結38評価sessionの資産系列から計算された19個の重複する正規化20-session窓である。新たなReplay結果ではない。

| 指標 | 保存V5 | 目標 |
|---|---:|---:|
| 換算元本 | ¥1,000,000 | ¥1,000,000 |
| 20-session最小 | ¥1,082,366 | — |
| 20-session平均 | ¥1,190,646 | — |
| **20-session中央値** | **¥1,199,154** | **約¥2,000,000** |
| 20-session最大 | ¥1,297,031 | — |
| 2倍到達 | 0 / 19窓 | 増加を確認 |
| 中央値の目標との差 | ¥800,846 | 解消 |
| 38-session最終資産・参考 | ¥1,477,436.15 | 1か月成績には使わない |

原本の20-session中央値は1.19915419倍。金額は円単位へ丸めて表示した。100万円から200万円にする一定複利の算術的目安は約+3.5265%/sessionである。これは必要な成長率の計算であり、達成可能性の予測ではない。

### 評価定義の重要な区別

保存式は「窓の最終ending_cash / 窓の開始starting_cash × 100万円」である。各窓を実際に100万円へresetしたReplayではない。V5は100株単位・band cap・target budgetを持つため、資産額の比例換算だけで同じ数量になるとは限らない。

また、保存OOF38は選定された評価session列であり、連続する全市場営業日であるとの認証はない。したがって、保存値は正確に比較用として維持し、文字どおりの「100万円で開始して20連続営業日後の現金」とは区別する。

V5のCOMPLETE日は全決済済みであり、終点はending_cash。未決済を都合よく時価・0 return・最終既知cashで補って正式成績にしない。新しい購入経路で決済不能が生じれば、その経路の正式wealthは未評価となる。

根拠: [V5原報告](https://github.com/Iam-2squared/ark-terminal/blob/710656491be06235901b45c50a8b5cbd714ba4eb/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/REPORT_FINAL-ja.md)、[V5配分コード](https://github.com/Iam-2squared/ark-terminal/blob/710656491be06235901b45c50a8b5cbd714ba4eb/research/capital-v5-max3-slot-intelligence-20261004-v1/allocation.py)、保存Bridge最終報告A節。

## 🔎 V5の問題は金額と重複を含めて扱う

| 課題 | 保存値 | 割合 |
|---|---:|---:|
| 費用込み実現returnが0以下 | 82 / 150取引 | 54.67% |
| Weak: Entry→Highが2%未満 | 58 / 150取引 | 38.67% |
| U5: rank-passから実購入 | 50 / 113機会 | 44.25% |
| U10: rank-passから実購入 | 26 / 47機会 | 55.32% |

LoserとWeakは重なる。U10もU5に含まれる。将来Highへの到達と、固定EXIT後の現金利益は同じではない。

| V5の150取引 | Loser | Loserではない | 合計 |
|---|---:|---:|---:|
| Weak | 48 | 10 | 58 |
| Weakではない | 34 | 58 | 92 |
| 合計 | 82 | 68 | 150 |

U5購入50件中17件、U10購入26件中9件が実現Loserだった。従って、U5を増やすだけで資産が増えるとは扱わない。上表の重複は保存bucketの整数件数から確認したもので、新規予測ではない。

### 保存台帳で、どこに実現損益が出ているか

| Entry→将来High | 実購入数 | 保存台帳の実現損益 |
|---|---:|---:|
| 2%未満 | 58 | −¥327,666.40 |
| 2%以上5%未満 | 42 | +¥18,116.80 |
| 5%以上10%未満 | 24 | +¥95,948.05 |
| 10%以上 | 26 | +¥691,037.70 |
| 合計 | 150 | +¥477,436.15 |

これは全38-sessionの固定台帳への寄与である。「Weakを除けばその損失額がそのまま回避できる」「翌月にも同じ利益を得られる」とは主張しない。取引を変えれば、cash・枠・後続数量も変わる。将来Highと実現損益のラベルは評価専用であり、現在の購入条件へ戻さない。

| rank-pass機会 | 購入 | Reserve拒否 | MAX3拒否 | cash / lot拒否 |
|---|---:|---:|---:|---:|
| U5 | 50 | 30 | 28 | 5 |
| U10 | 26 | 10 | 9 | 2 |

根拠: [V5品質・reserve原集計](https://github.com/Iam-2squared/ark-terminal/blob/710656491be06235901b45c50a8b5cbd714ba4eb/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/SLOT_QUALITY_AND_RESERVATION.json)、[V5原報告](https://github.com/Iam-2squared/ark-terminal/blob/710656491be06235901b45c50a8b5cbd714ba4eb/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/REPORT_FINAL-ja.md)。金額の合算は保存済みbucket値の加算のみ。

## 🛑 既に実施済みで、名前を変えて繰り返さないもの

全期間完了armの20-session値は、同じ形式の正規化Development比較値である。V5を上回る新成績は今回作成していない。

| 研究 | 操作 | 20-session中央値 | 38-session最終資産 |
|---|---|---:|---:|
| V4 B_PLUS | V4比較基準 | 1.145849倍 | ¥1,433,740.25 |
| V4 S_ONLY | Sだけに絞る | 0.956602倍 | ¥895,356.10 |
| V4 A_PLUS | S/Aだけに絞る | 1.143490倍 | ¥1,393,406.80 |
| **V5** | 保存slot policy | **1.199154倍** | **¥1,477,436.15** |
| V9 I1 | q2 Pareto pressure | 0.923183倍 | ¥922,425.95 |
| V9 I2 | q2/q3 Pareto pressure | 0.914624倍 | ¥933,856.05 |
| V11R1 M1 | MRET連続cap抑制 | 評価未完了 | 28日完了・次の日で未決済 |
| V11R1 M2 | MRET中央値で100株cap | 1.067406倍 | ¥1,203,908.60 |

V9 I2はU5を50→53、Mediumを27→32へ増やしてQuality保存条件を通ったが、最終資産はV5より大幅に悪化した。q2/q3はreserve判定へ使われ、数量には使われていない。V5の数量重みは元ML、V9の保存数量設計はpP proportionalであり、異なる配分原本を混ぜて説明しない。

MRETの数値認証は維持するが、現金利益への独立した追加価値・絶対損失防御は未確立。M1/M2の再fit・再Replayで同じ問いを繰り返さない。

最新Reserve Past-Qualified RecoveryはPAST_SUPPORT_NOT_ESTABLISHED、適格0/8、candidate Replay0で終了済み。閾値緩和、4LOW→3LOW/OR、Reserve/Slot3の局所救済へ戻らない。発火0を資産改善の成果にしない。

根拠: [V4独立cutoff報告](https://github.com/Iam-2squared/ark-terminal/blob/220e0d8863978f5d82d0d83189d473252efda146/docs/evidence/capital-v4-rank-cutoff-independent-20261004-v1/REPORT_FINAL-ja.md)、[V9資産原本](https://github.com/Iam-2squared/ark-terminal/blob/c89410b1976701a36a6de2f556fbb55411eb8371/docs/evidence/capital-v9-quality-aware-max3-integration-20261005-v1/CAPITAL_ROLLING20_RESULT.json)、[V11R1資産原本](https://github.com/Iam-2squared/ark-terminal/blob/0aa28e07e4d4c5698625030343027e819375051a/docs/evidence/capital-v11r1-numeric-cert-recovery-20261005-v1/CAPITAL_ROLLING20_RESULT.json)、[最新Reserve閉鎖記録](https://github.com/Iam-2squared/ark-terminal/blob/220e0d8863978f5d82d0d83189d473252efda146/docs/evidence/capital-v5-reserve-past-qualified-20261005-v1/CLOSURE.json)。

## 🧱 統合の構造上の問題

V5の原allocationはcashだけでなく、equity、既存exposure、最上位band、保有と提案の合計数、元ML比率、band cap、100株単位で数量を決める。

| 現象 | 資産改善への意味 |
|---|---|
| 買付数量だけを小さくする | 100株以上残れば保有枠は空かない |
| 候補を丸ごと外す | 候補数や最上位bandが変わり、目標投資比率が下がる場合がある |
| 現金が増える | band cap / target budgetが拘束していれば他候補の数量は増えない |
| 初回割当が100株未満 | 余剰資金の追加配分対象にも入らない |
| 既存保有が強い | 既存契約では後から買い増さない |
| 後から自然EXITで枠が空く | 過去の見送ったEntryは復活せず、その時点の合法な新Entryが必要 |

このため、「悪い取引を減らす側」と「良い候補へ資金を渡す側」を別々に改善しても、資金移動が成立しないことがある。次に確認する対象は、**購入前の同じ予算から、合法な候補へ出す整数数量と、その後の現金・枠の推移**である。

新Capital Engineでは、凍結Expertの役割を保持した上で、購入可否と数量を同じ決定として扱う。適当なAND/OR/重み付き和を円建て期待利益と見なさない。pPはWinner priority、q2はWeak risk、q3はMedium+ floor、MRETは相対診断という現状を引き継ぐ。

## ▶️ 次の作業を絞った

詳細は [NEXT_WORK-ja.md](NEXT_WORK-ja.md)。

| 順序 | 作業 | 完了時に必要なもの |
|---|---|---|
| 1 | 既存の資金・数量・損益・cash・枠の原本を結び付ける | 再集計済み部分は再利用し、不足する資金経路だけを補う |
| 2 | 配分を減らす側→受け取る合法Entry→実際の追加lotを確認する | 現金放置、数量0、MAX3残存、既知の救済案を区別する |
| 3 | 主に変更するCapital機構を1つに絞り、有限仕様を事前固定する | 入力時点、数量式、caps、同時刻順序、停止条件、評価窓を確定 |
| 4 | 因果・会計・最初の実数量差を確認した候補だけを評価する | 費用込み20-session最終資産とV5差。条件を結果後に変えない |

現在、新しい数量写像・閾値・candidateはまだ選定していない。今回の成果は引き継ぎ、原本照合、資金経路の構造確認、次の作業仕様である。新戦略の成績は未測定であり、2倍達成・Capital改善を主張しない。

旧Bridgeの「元slot1/2の全ID保護」「U5件数floor」「全19窓非劣化」等を、今回の永久条件へ無条件に移植しない。最新の主目的は最終資産。ただし因果順序、正しい会計、凍結upstream、現物cash/MAX3/100株と実行条件は実験成立条件として守る。既存証拠の改変や未来の売却可否を使った除外は行わない。

## 🔒 Freeze authorityと今回の検証

| 対象 | 固定authority |
|---|---|
| Selector | FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75 |
| Selector freeze commit | 06e19ef9cd4fca99840487404ccb38a182b9bd2f |
| Selector artifact SHA256 | e75a49adb2a35497b6ac4d1afdd2942f87d9e139f04ae98e2478ca564ee874d8 |
| FIRST ENTRY v2 P1_Q70 | 4a2d6f35946b16820a13449a9288a6685a5c283c |
| Structural EXIT v3 | c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad |
| 正式EXIT receipt | 1ecbcc43f75279fa302f19fd896add2aac15b537 |

Selectorの正本とEntryの無変更lineageもGitHubから回収した。SelectorからCapitalまでの全行再実行を行ったという意味ではない。今回は既存native codeと入力を保存済みbindingに照合し、34ファイルすべてSHA256一致。原本を再生成していない。

| 確認 | 結果 |
|---|---:|
| 最新ZIPのSHA256 | 前チャットの正本と一致 |
| 最新ZIP内部のmanifest項目 | 13 / 13一致 |
| V4 / V9 / V11R1添付のmanifest項目 | 79 / 27 / 46件一致 |
| 主要native code / input binding | 34 / 34一致 |
| 新fit / refit | 0 / 0 |
| 市場Replay / 新候補の資産評価 | 0 / 0 |
| Selector / Entry / EXIT変更 | 0 |
| Claude / 発注 / main merge / force push | すべて0 |

資料・ソースを並列に照合した。独立した別担当の読み取りを利用したが、共通資料を読むため外部の完全な盲検監査とは呼ばない。

根拠: [Selector正式artifact](https://github.com/Iam-2squared/ark-terminal/blob/220e0d8863978f5d82d0d83189d473252efda146/predict/research/phase57-long-only-frozen-selector-min-price75-v1.json)、[保存input binding](https://github.com/Iam-2squared/ark-terminal/blob/220e0d8863978f5d82d0d83189d473252efda146/docs/evidence/capital-v5-reserve-past-qualified-20261005-v1/INPUT_BINDING.json)、SOURCE_BINDING_CHECK.json。

## ❓ 残っている確認事項

### A. 月との対応を認証するsource

OOF38は2025-06-27〜2025-08-25の選定session列。2025-07-11と2025-07-14は元all58にも入っていない。今回読んだsession splitには理由が記載されていない。欠落を無取引・0%と決めつけない。

次作業では元session manifestとcoverage receiptを先に探す。それでも確認できない場合、前チャットへ聞く内容は次の1点で足りる。

> Capitalのall58/OOF38から2025-07-11・2025-07-14が外れている理由と、その根拠になる元session manifestまたはcoverage receiptのGitHub commit/pathはどれか。真に100万円から20連続営業日を評価済みなら、そのreset条件と結果原本はどれか。

この点は引き継ぎや資金経路の設計を止める理由ではない。ただし、厳密な1か月・100万円開始の達成認証前には解決が必要。

### B. 過去I2比較値の出典差

| I2 rolling20値 | 認証済みV9原本 | V11 policy内の参照値 |
|---|---:|---:|
| 中央値 | 0.9146242057487491 | 0.9283112455 |
| 平均 | 0.9443465261832323 | 0.9542671531 |

別値の由来は未確定。原本を黙って上書きしない。本報告ではV9の結果原本を採用した。M2がV5未達という結論は変わらず、新Capital設計のために旧結果を再Replayする必要もない。将来この比較値を再利用するときだけ、由来を解決する。

### C. 反復利用したDevelopmentの位置付け

既存データはITERATIVE_DEVELOPMENT_EVIDENCE。予測時点の未来情報を遮断しても、研究者が同じ期間の結果を繰り返し見た事実は消えない。今後のDevelopment改善を、新しい未使用期間での2倍達成へ読み替えない。現資料は2倍達成可能性を証明していない。

方法論の一次資料: [Baileyほか, The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)。

## 💾 保存と再開位置

P0は153ba39564c216dd53ca5530e40fa038ab913947に保存済みで、actual GETの本文一致とtreeを確認した。今回の最終保存commitは保存後のreceiptに記録する。未来のSHAは記載しない。

再開時はP1_HANDOFF_COMPLETE.json、NEXT_WORK-ja.md、WORK_STATUS_LOG.jsonlを読み、branchの最新HEADをactual GETしてから続ける。最初の作業は資金経路と評価定義のbinding。旧Reserveの再実行、モデル精度の再測定、根拠のない新候補量産へ戻らない。
