# Ark Terminal — State Predictiveness V3 最終報告

作成JST：2026-10-02T13:09:35.406519+09:00

**STATE_REVERSAL_PREDICTIVENESS_LIMITED_SAMPLE**。Integrity PASS、独立核心不一致0、採用するReversal／Pathは0件。

現在StateだけのR1に対し、full State9のR2は危険誤予測の点推定を17.70%から12.78%へ下げた。しかしCoreは597 anchor・6評価日・3foldで、下降反転は98件。固定した8日・actual support100件の基準を満たさない。Path追加のR3/R4はR2より危険誤予測が多く、較正後の確率log lossもbaselineより悪い。サンプル不足をintegrity BLOCKへ読み替えず、今回の測定をCで固定する。

## 主要結果

| model | accuracy | UP precision | DOWN precision | DOWN recall | UP予測→DOWN実現 | date-equal log loss |
| --- | --- | --- | --- | --- | --- | --- |
| R0 | 76.72% | 76.72% | NA | 0.00% | 98/597 = 16.42% | 0.86132 |
| R1 | 66.67% | 79.42% | 10.81% | 12.24% | 86/486 = 17.70% | 0.93999 |
| R2 | 80.07% | 81.67% | 64.29% | 27.55% | 69/540 = 12.78% | 4.7498 |
| R3 | 76.88% | 80.49% | 55.00% | 22.45% | 76/533 = 14.26% | 2.9031 |
| R4 | 77.05% | 79.67% | 57.50% | 23.47% | 75/541 = 13.86% | 2.2638 |


R0=全体prior、R1=current Primary、R2=State9全tuple、R3=State9＋従来Path、R4=State9＋反転用Path Anatomy。DOWNは価格損失の定義ではなく、Frozen context=-1を伴う最初の確認済みState遷移。REBOUNDもcontextがDOWNなら含む。UP継続はgenuine transitionによるRISE／SHARP_RISEかつcontext/local=+1で、単なるHOLDは含めない。

図：危険誤予測と95%日cluster区間（CHARTS/02_up_to_down_dangerous_error.png、完全Evidence ZIPに同梱）

| model | 危険誤予測率 | 95% cluster区間 | DOWN予測→UP実現 |
| --- | --- | --- | --- |
| R0 | 16.42% | 6.48%–34.00% | 0/0 = NA |
| R1 | 17.70% | 4.55%–33.52% | 72/111 = 64.86% |
| R2 | 12.78% | 2.15%–30.11% | 14/42 = 33.33% |
| R3 | 14.26% | 3.45%–31.38% | 13/40 = 32.50% |
| R4 | 13.86% | 2.96%–31.35% | 17/40 = 42.50% |


分母はUPを予測したanchorであり、DOWNの全実例98件に対するRecallとは別。30slot窓とminute anchorは重複する。95%区間は保存済みの同じ1000 date-cluster vectorsから計算した記述的区間で、独立した売買試行の精度ではない。6日で区間は広い。

図：class別precisionとrecall（CHARTS/01_reversal_class_precision_recall.png、完全Evidence ZIPに同梱）

## 取得・評価母数

| 項目 | 結果 |
| --- | --- |
| 固定72候補 | ACQUIRED 65 / U_UNAVAILABLE 4 / RAW_UNAVAILABLE 3 |
| 今回の残り33候補 | 30取得 / 3 U_UNAVAILABLE / 未分類0 |
| 総データ | 34日 / 90 security-session / 29,305 endpoint |
| 全observed / null | 6,289 / 23,016 |
| 新しいFrozen生成 | 9,810 endpoint; 原本19,495 endpointは再利用 |
| 新規固定日 | 11日、全日で最低1 session取得 |
| Core OOF | 597 rows / 6日 / 11 security-session / 3fold |
| Core actual labels | UP 458 / DOWN 98 / RANGE_OR_STOP 41 / NO_DECISION 0 |
| Motion OOF | 677 rows / 9日 / 16 security-session / 3fold |
| 次distinct 9State OOF | 1,490 rows / 10日 / 17 security-session / 3fold |
| 次observed 9State OOF | 1,791 rows / 11日 / 23 security-session / 3fold |


全145日／142 currentリンクを取得したとは主張しない。72候補の選定順と銘柄を維持し、結果後の補充0。N039の過去U_UNAVAILABLE中断と旧3skipも元Evidenceに保持し、V3で欠けた3件も次銘柄へ置換しなかった。11取得日でもgap・null・session境界などによりCoreの有効日は6日に減る。Coreの8日ゲートをsecondary 9Stateの10／11日で救済しない。

## Fold・確率品質

| fold | rows | dates | R1 accuracy | R2 accuracy | R4 accuracy | R2 date-equal LL | R4 date-equal LL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 215 | 2 | 89.77% | 93.02% | 88.37% | 0.48704 | 0.98132 |
| 2 | 226 | 3 | 63.27% | 69.47% | 69.03% | 8.9106 | 3.6447 |
| 3 | 156 | 1 | 39.74% | 77.56% | 73.08% | 0.79272 | 0.68592 |


図：fold安定性（CHARTS/06_fold_stability.png、完全Evidence ZIPに同梱）

| model | 未較正date-equal LL | 較正後date-equal LL | 較正後date-equal Brier |
| --- | --- | --- | --- |
| R0 | 0.88124 | 0.86132 | 0.4901 |
| R1 | 0.80234 | 0.93999 | 0.47647 |
| R2 | 2.5395 | 4.7498 | 0.38024 |
| R3 | 1.8482 | 2.9031 | 0.43737 |
| R4 | 1.448 | 2.2638 | 0.3997 |


temperatureは各foldの最後のtraining日だけで固定し、testで再選択していない。今回、R1–R4のouter probability log lossは較正によって悪化した。R2はFold2で特に大きく悪化した。ridge scoreのclip→normalizeと温度調整の組合せで、誤ったclassへ極小確率を割り当てるリスクが残ったという結果を保持する。良かった未較正版へ結果後に選び直してpromotionしない。温度調整はargmaxを維持し、accuracy／危険誤予測率は変えない。

図：較正前後log loss（CHARTS/04_calibrated_vs_uncalibrated_log_loss.png、完全Evidence ZIPに同梱）

図：DOWN確率の較正（CHARTS/05_down_reversal_calibration.png、完全Evidence ZIPに同梱）

## Pathの追加効果・集中

R2→R3でaccuracyは80.07%→76.88%、危険誤予測は12.78%→14.26%。R3→R4でaccuracyは76.88%→77.05%、危険誤予測は14.26%→13.86%、date-equal LLは2.9031→2.2638へ改善したが、R2よりaccuracy／DOWN recallが低く、R1よりlog lossが悪い。反転用Anatomyの有用性を認証する条件は満たさない。

図：R0–R4比較（CHARTS/03_r0_r4_incremental_performance.png、完全Evidence ZIPに同梱）

図：日・銘柄への集中（CHARTS/07_date_security_concentration.png、完全Evidence ZIPに同梱）

危険誤予測の件数シェアと、promotionに使うgross positive correctness gainの集中は別集計。PROMOTION_GATE_V3.csvに全モデル／UP・DOWN候補／R1・R2比較のprecision調整CI・calibration・recall・risk・集中gateを保存した。1日／1銘柄へ改善が集中するcaseもある。今回deltaのR4 gainだけで将来の個別feature効果を因果認証しない。

## 反転前Pathの記述

| current State | N | 日 | UP継続 | DOWN反転 | Range/Stop |
| --- | --- | --- | --- | --- | --- |
| RISE | 355 | 6 | 248 / 69.86% | 76 / 21.41% | 31 / 8.73% |
| PULLBACK | 216 | 6 | 198 / 91.67% | 14 / 6.48% | 4 / 1.85% |
| RISE_STOP | 22 | 4 | 8 / 36.36% | 8 / 36.36% | 6 / 27.27% |
| SHARP_RISE | 4 | 1 | 4 / 100.00% | 0 / 0.00% | 0 / 0.00% |


| history長 | sequence数 | 完全history anchor | 最大N | 支持基準合格sequence |
| --- | --- | --- | --- | --- |
| 1 | 4 | 597 | 355 | 0 |
| 2 | 13 | 567 | 211 | 0 |
| 3 | 28 | 515 | 193 | 0 |
| 4 | 45 | 478 | 153 | 0 |


history長1=currentのみ、長2=current＋直前1 run、長3=直前2、長4=直前3。R4のpredictor自体は直前1–4 completed runを使う。dwellはanchor時点で既知の値だけで、未来のrun最終長を読まない。未形成historyはMISSINGのまま出す。

| 3-State sequence | N | 日 | DOWN / rate | UP / rate |
| --- | --- | --- | --- | --- |
| RISE>PULLBACK>RISE | 193 | 6 | 25 / 12.95% | 164 / 84.97% |
| PULLBACK>RISE>PULLBACK | 153 | 5 | 11 / 7.19% | 138 / 90.20% |
| RISE>DROP>RISE | 41 | 4 | 15 / 36.59% | 11 / 26.83% |
| DROP>RISE>PULLBACK | 13 | 3 | 0 / 0.00% | 13 / 100.00% |
| RISE>RANGE>RISE | 12 | 1 | 0 / 0.00% | 9 / 75.00% |
| PULLBACK>DROP_STOP>RISE | 11 | 2 | 4 / 36.36% | 7 / 63.64% |
| RANGE>RISE>PULLBACK | 11 | 1 | 0 / 0.00% | 11 / 100.00% |
| DROP_STOP>RISE>PULLBACK | 9 | 2 | 3 / 33.33% | 6 / 66.67% |


RISE>PULLBACK>RISEは193 anchorでUP164、DOWN25だが6日。RISE>DROP>RISEは41 anchorでUP11、DOWN15、Range15。SHARP_RISEは4 anchor・1日だけでDOWN0、RISE_STOPは22 anchorでUP8／DOWN8／Range6。支持不足の100%や小Nの反転率を高精度パターンとは呼ばない。全sequenceの支持基準はN>=100・日>=8・銘柄>=3で、合格0。

図：長さ別supportと反転率（CHARTS/08_path_length_support_vs_reversal_rate.png、完全Evidence ZIPに同梱）

図：反転を含む高支持Path（CHARTS/09_highest_support_down_reversal_paths.png、完全Evidence ZIPに同梱）

図：継続を含む高支持Path（CHARTS/10_highest_support_up_continue_paths.png、完全Evidence ZIPに同梱）

## Controls・9State secondary

| control | model | matched N | 日 | REAL date-equal LL | control date-equal LL | warning |
| --- | --- | --- | --- | --- | --- | --- |
| TRUE_NULL | R2 | 597 | 6 | 4.7498 | 4.7426 | True |
| TRUE_NULL | R3 | 597 | 6 | 2.9031 | 4.1335 | False |
| TRUE_NULL | R4 | 597 | 6 | 2.2638 | 4.5437 | False |
| SHIFT60 | R2 | 131 | 3 | 1.5546 | 7.1234 | False |
| SHIFT60 | R3 | 131 | 3 | 1.0112 | 7.0616 | False |
| SHIFT60 | R4 | 131 | 3 | 1.0241 | 6.5343 | False |


TRUE_NULLのCore R2は固定したdate-equal LL規約でwarning。R3/R4はこのwarningなしでも他gateを通らない。TRUE_NULLは同日・同security-sessionでlabel/provenanceを一緒に置換するため、group marginal priorは残る。SHIFT60 Coreは131 matched rows・3日・3fold、R2–R4に同等性能warningなし。強弱はregime/dependence stressの結果で、actual leakageの証明とは扱わない。timestamp／partitionは直接照合した。

| task | V3 R1 | V3 R2 | V3 R3 | V3 R4 |
| --- | --- | --- | --- | --- |
| NEXT_DISTINCT_PRIMARY | 44.56% | 69.53% | 70.13% | 68.46% |
| NEXT_OBSERVED_PRIMARY | 79.12% | 71.19% | 77.78% | 73.87% |


V2の次distinct B3 accuracy60.44%に対し、V3 R3は70.13%。ただし別の評価日・母集団であり、制御された改善証明とはしない。V3次distinctのSHARP_RISE actual supportは2件、次observedは4件。9State全class、分母0のNA、支持不足を除外していない。rare Stateのsupportが一様に増えたとは言えない。全modelのPrecision／Recall／F1・支持数・9×9はCSVを正とする。

図：V2とV3のState precision（CHARTS/11_nine_state_precision_v2_vs_v3.png、完全Evidence ZIPに同梱）

図：V3全modelの9×9（CHARTS/12_nine_by_nine_confusion_all_models.png、完全Evidence ZIPに同梱）

図の略号：RS=RISE_STOP、R=RISE、SR=SHARP_RISE、PB=PULLBACK、RG=RANGE、RB=REBOUND、SD=SHARP_DROP、D=DROP、DS=DROP_STOP。

## 監査・保存・境界

| 項目 | 実数／状態 |
| --- | --- |
| 独立main照合 | 3399751 |
| 独立補助照合 | 2053 |
| 核心不一致 | 0 / PASS |
| fit / cap | 576 / 1200（final180＋inner396） |
| provider HTTP / cap | 66 / 900 |
| Frozen generation / cap | 9810 / 18000 |
| global bootstrap | 1000一度生成、全集計で再利用 |
| 今回resumeでfit / label / draw / provider | 各0 |
| 図 | 12種類×PNG/SVG、CSV hash照合PASS |
| State9 / Path / profile / M0変更 | 各0 |
| Common Holdout / Protected / Fresh / OOS / Prospective | 各0 |
| Entry / EXIT / profit / Capital / Portfolio / orders | 各0 |
| main merge / force push / external AI | 各0 |


独立照合は別コードで、同じassistantが実施したものであり、外部の独立人間レビューではない。Frozen原本hash、保存traceからの63 primitive feature、causal prefix Anatomy、event order、censoring、donor/fold purge、全final／inner係数のnormal equation、inner-grid／temperature選択、固定OOF、class混同行列、risk、保存bootstrap CI、calibration bucket、promotion、図CSVを照合した。再fit／kernel／provider／bootstrap新drawは0。purge済みのAPI full raw responseを取得し直した監査ではない。historical known_at UNKNOWNと研究assumed bar_endの区別を保持する。

C5 JSONLは74,885行で途切れていたが、完全な4 CSVから105,090行を復元し、元C5 SHA `2b13dd18c80723dc2ab4838e62c6804d4e999b94f3019c8a54d71e0f7d4b87fe` とbyte一致。切れた原本も保持した。checkerのmodule接続修復と同値の計算効率修復はROUTINE_REPAIR_RECEIPTに記録し、結果・target・split・thresholdを変えていない。

V1の正式BLOCK・3000/cap1000の過去超過・旧RC1 16FAIL・88workflow incident・V2のno promotion・4行append ledger欠落を保存し、過去budget／outside exposure unknown/nonzeroを0へリセットしない。GitHubは専用branchのcode／Contract／aggregateのみ。row-level features／traces／labels／OOF／fitsはユーザー用Evidence ZIPへ保存する。

## 次の方針

今回の33候補は全件分類済み。既存V3を結果に合わせて拡張・再較正しない。次に進める場合は、承認済み145日metadata inventoryから未使用Developmentを日付順・metadataだけで選ぶ追加取得計画を、新しいscope／有限budget／precommitに固定する。Coreの有効日8以上とDOWN support100以上を取得件数とは別に満たす必要がある。結果駆動の銘柄補充は行わない。

ridgeの確率品質と単日inner selectionの不安定さが残った。次の別Contractで、適切なprobability modelやcalibration法・固定小gridを先に決め、既存V3をexposedとして扱って測る。現在のEntry／EXITへ渡せる採用featureは0。再利用できるのはFrozen schema、prefix処理、危険誤予測の定義・Evidenceと失敗知見。Holdout準備は未達で開封0。

## 必須27問への対応

| 番号 | 問い | 回答 |
| --- | --- | --- |
| 1–2 | DOWN / UP予測 | R2 DOWN P64.29%・R27.55%、UP P81.67%・R96.29%。R4 DOWN P57.50%・R23.47%、UP P79.67%・R94.10%。 |
| 3–4 | 危険誤予測・baseline比較 | R1 86/486=17.70%、R2 69/540=12.78%、R4 75/541=13.86%。点推定は改善、採用認証なし。 |
| 5 | R1→R2 | accuracy／DOWN precision改善、較正後date-equal LL悪化・support不足。 |
| 6 | R2→R3 | 危険誤予測・accuracy・DOWN recall悪化、Path採用なし。 |
| 7 | R3→R4 | 一部改善があるがR2／R1追加gate不成立。 |
| 8 | 較正 | R1–R4のouter LL悪化。未較正版へ事後切替しない。 |
| 9 | current State | RISE／PULLBACKは記述的比較可能。全classの8日support不足。 |
| 10 | RISE前Path | 上記高支持tableと全長1–4 CSV。独立予測パターンとしては未認証。 |
| 11 | SHARP_RISE前Path | 4 anchor・1日。DOWN0でも読みやすいとは主張できない。 |
| 12 | RISE_STOP後 | UP8／DOWN8／Range6、全22件。 |
| 13 | PULLBACK | UP198／DOWN14／Range4、全216件。継続の高い記述率はあるが採用gate未達。 |
| 14–15 | history長・支持sequence | 長さ1–4を保存。長くするとhistory不足・small N増。支持基準合格sequence0。 |
| 16 | 日／銘柄依存 | 6評価日。集中CSV・図・promotion gain shareを保存し、依存なしとは認証しない。 |
| 17 | TRUE NULL | Core R2 warningあり。R3/R4もcalibration/support等で採用不可。 |
| 18 | SHIFT60 | Core131 matched rows、R2–R4同等warningなし。regime stressでありleak証明ではない。 |
| 19 | 9State比較 | V3 R3 next-distinct70.13%。V2とは別日・別母集団。controlled improvement未認証。 |
| 20 | rare State | 全9Stateを保存。SHARP_RISE support等が少なく、一様増加なし。 |
| 21 | 第3fold | 確保。ただしCore Fold3は1評価日。 |
| 22 | 残り取得 | 33候補=30取得・3skip。固定72候補の未分類0。 |
| 23–24 | Entry／EXIT再利用 | 採用feature0。schema・危険誤予測定義・prefix実装・Evidenceのみ研究再利用可。 |
| 25 | Holdout準備 | 未達、開封0。 |
| 26 | State9／Path意味変更 | 各0、profile／M0も0。 |
| 27 | 禁止exposure | Holdout／Protected／Entry／EXIT／profitの今回delta各0。過去unknown/nonzeroは保持。 |

