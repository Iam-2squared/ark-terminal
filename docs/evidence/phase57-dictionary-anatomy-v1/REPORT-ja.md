# Dictionary不合格理由の解剖 — 最終研究判定

対象HEAD: `573a0bfebf87319cdc07f93ee6db533f74457c69`。取得済み日足733日・分足144日、固定73 scalar×2 lane、定義/Gate/旧結果を維持。保存済み結果だけを読むpost-hoc診断であり、新しい確認的検定・raw再取得・全量再測定は行わない。

## 1. Completion Gateを落とした理由

| lane | USABLE / WATCH / INSUFFICIENT | trait数 ≥8 | family数 ≥4 | daily ≥2 | intraday ≥2 |
|---|---|---|---|---|---|
| 日足 | 4 / 30 / 39 | 4 FAIL | 3 FAIL | 4 PASS | 0 FAIL |
| 分足 | 5 / 62 / 6 | 5 FAIL | 3 FAIL | 1 FAIL | 4 PASS |

Gateは銘柄ごとの最低trait数ではなく、母集団全体で信頼できるtrait集合の多様性を要求する。日足だけのlaneではintraday最低数は構造的に満たせない。実際の拡張Completionは分足laneのGateを参照し、こちらも独立に不合格。日足と分足のUSABLEの単純和集合は8種類だが、異なる期間・標本の結果を足して新しい合格とはしない。

WATCHのcalibration失敗は日足30/30、分足55/62。**calibrationだけの不通過は日足14・分足9、合計23判定**。分足のvolume_O30/AM/PM1の3件は統計Gateを通過し、対応value配分との重複のみでWATCH。したがって92 WATCHを「92種類すべて無信号」と解釈してはいけない。92は同一traitのlane別判定数であり、独立92種類ではない。

日足のINSUFFICIENT39件はすべてintraday tierで、分足のないlaneの構造的欠測。分足6件はSwing amplitude/duration、Pullback、Rebound、Giveback、closing range。標本不足を無信号とは判定しない。

## 2. 本当に再現した性格（固定Gate通過）

| lane | trait | raw reliability | incremental | calibration slope |
|---|---|---:|---:|---:|
| daily | inside | 0.7671 | 0.5281 | 0.6799 |
| daily | gap_fill | 0.6330 | 0.4068 | 0.6360 |
| daily | gap_cont | 0.5452 | 0.3383 | 0.5522 |
| daily | amihud | 0.9161 | 0.6255 | 0.7759 |
| intraday | amihud | 0.8949 | 0.4027 | 0.6427 |
| intraday | value_O30 | 0.7878 | 0.6460 | 0.9695 |
| intraday | value_AM | 0.7823 | 0.6425 | 1.1544 |
| intraday | value_PM1 | 0.6059 | 0.4845 | 0.9164 |
| intraday | pdh_break | 0.8150 | 0.4867 | 0.7912 |

これらはDevelopmentの銘柄間順位・校正の再現性であって、特定銘柄の恒常的性格や売買利益の証明ではない。日足insideは包みではなくinside day、gap_fillは窓埋め、gap_contは窓方向継続。分足pdh_breakは前日高値突破の発生傾向。

## 3. 重要Chart traits

| family | 現状と解釈 |
|---|---|
| Swing | amplitude/durationは両半分で適格な銘柄が各9、pullbackは0（最低100）。pullbackの跨昼休み比率の定義欠陥を合成入力で確認。 |
| Rebound / Giveback | 適格銘柄0。Reboundは片側最大6/4 event-bearing sessions、Givebackは5/6で、既存最低8にも届かない。イベントそのものの無効性は未判定。 |
| VWAP | reclaimはraw 0.1469、incremental −0.0155。raw/incremental/CI/calibration/direction/strata/tail/FDR不通過。現在の定義では再現性を示せない。 |
| Breakout | pdh_breakはUSABLE。OR breakはraw 0.4992、incremental 0.1682だがCI/calibration/FDR不通過。OR follow/failureもWATCH。 |
| Reclaim | PDL reclaimはraw 0.0144、incremental −0.0351。raw/incremental/CI/calibration/direction/timeRandom/tail/FDR不通過。 |
| Wick | 上ヒゲは日足raw 0.5135 / incremental 0.3248、分足0.3377 / 0.2212だがcalibration/timeRandom不通過。下ヒゲもWATCH。方向や規模を確信して利用できない。 |
| Compression | 日足range_conはcalibrationだけ不通過（0.4802）。分足laneでも0.3146でcalibration不通過。これは日足レンジ縮小traitで、当日intraday compressionの独立評価ではない。 |
| S/R | PDH/PDL/ORに限定した証拠。一般的な支持抵抗帯・touch personalityは別の検定済みscalarではない。 |
| Volume confirmation | 配分3種はUSABLE、出来高配分3種は重複だけ。break_value / gap_down_value compositeの信頼性は未検定。配分を出来高確認付きbreakoutの証拠に読み替えない。 |

全関連traitのlane別status、失敗Gate、数値は `diagnostic/06_chart_traits.json`、全146判定は `02_all_traits.json` と `08_trait_gate_matrix.csv`。

## WATCH92分類（重複分類、因果推論ではない）

| 分類 | daily CONFIRMED / INDICATION / UNKNOWN | intraday CONFIRMED / INDICATION / UNKNOWN |
|---|---:|---:|
| DEFINITION_INSTABILITY | 0 / 0 / 0 | 0 / 4 / 0 |
| NO_RELIABILITY_DEMONSTRATED | 6 / 0 / 0 | 34 / 0 / 0 |
| PEER_ADJUSTMENT_LOSS | 3 / 0 / 0 | 0 / 0 / 0 |
| PEER_CLUSTER_RELIABILITY | 0 / 0 / 30 | 0 / 0 / 62 |
| RECENT_ONLY_RELIABILITY | 0 / 0 / 30 | 0 / 0 / 62 |
| REDUNDANT_RELIABLE_TRAIT | 0 / 0 / 0 | 3 / 0 / 0 |
| RELIABLE_PARTIAL_GATE_FAILURE | 19 / 0 / 0 | 19 / 0 / 0 |
| SAMPLE_INSUFFICIENT | 0 / 0 / 0 | 0 / 0 / 0 |
| STRATUM_LOCAL_SIGNAL | 0 / 0 / 0 | 0 / 14 / 0 |
| TAIL_SESSION_SENSITIVITY | 0 / 10 / 0 | 1 / 43 / 0 |

NOT_ESTABLISHEDは残りの行で、反証やゼロではない。詳細はtraitごとのbasis参照。以下は現在の保存Evidenceからは確定できない：price/volatility層限定の再現、個別共変量の除去効果、recent-onlyの時間的再現、peer/clusterの独立再現。保存されたliquidity tertileの正負はCI/FDR付き層別検定ではない。相関がある層を結果後に選んで採用していない。

## 4. Sparse Dictionaryの利用可否

**表現・保存方式として成立可能、Entry/EXIT用の実用性は未成立。** Global USABLEとsymbol-window ELIGIBLEを分離して扱う。分足60-position snapshotでは3,767/3,899銘柄が少なくとも1traitを保持できるが、そのうち1,960銘柄はamihudのみ。PDH breakoutの観測数を満たす銘柄は20/60/250 windowで4/366/1,337。これは観測適格性で、銘柄別再現性の合格数ではない。

日足と分足のprofile終端は別。20/60/250の同じ終端を持つ重複window間の相関はrecent-only signalの証明にならない。nEff・CI・drift・coverageを保持し、欠測はabstain。peer prior、symbol residual、短中長期とdriftを分離する設計を `sparse-design.md` に固定した。これは研究設計であり採用Gateの置換ではない。

## 5. 新registryは必要か

pullback_depthの同一phase/連続性とLONG impulse-correctionの意味を修正するなら、別registry versionが必要。旧traitのコードは無関係な朝/午後の隣接swingでも比率を計算する。直接関数を呼ぶ合成反例で確認した。新versionを作れば合格するとは限らず、標本数Gateも変更しない。この工程では旧結果を解剖し、修正候補を限定したところで停止し、新registryの作成・再測定は行っていない。

## 6. Dictionary＋Chart ReaderをEntry/EXITへ渡せるか

**NOT_READY。** Readerは実履歴のsession/barValue形式に未対応で、古いmorning barを午後のavailable contextとして受理する。単位・trait対応も未検証。合成テストで確認し、旧Readerを変更せず欠陥Evidenceとした。したがって新Entry/EXIT・統合試験は未着手。

## 検証・保存・境界

診断生成を2回実施してmanifest一致を確認する。CIでも同じ2回生成と期待manifest照合、focused tests、既存回帰を実行する。完了した実測receiptは `ci-result/ci-receipt.json`、回帰詳細は `ci-result/regression/regression.json` を正本とする。合成反例は欠陥を再現するテストであり、旧Readerを完成扱いするテストではない。

新規provider取得0、元のraw再測定0、新たなprimary trait検定0、Holdout/REPORT19/Validation/OOS/Fresh payloadアクセス0。以前のREPORT19派生結果閲覧事故は消去せず維持。Common Holdout244日には既知の過去Exposureがあるため全期間unknownとは主張しない。Safety9項目は全false、Selector/Capital/main不変。

## 次の1工程とSTOP

次は確認済みpullback定義欠陥とReader接続/鮮度の問題だけを対象に、有限の修正仕様を別versionとして事前固定する工程。結果を見た閾値緩和、無制限pattern mining、Holdout開封は禁止。Dictionary/ReaderがDevelopment上で使用可能となった時だけ仕様を固定し、その次に既存Entry/EXITの微修正ではなく **NEW LONG Entry / NEW LONG EXITをDictionary＋Chart Reader前提で再設計する**。今回はそこまでの使用可能性を確認できていないため、その条件を満たしたとは扱わずSTOP。
