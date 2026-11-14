# Ark Terminal — State Predictiveness V5

Final status: `STATE_R2_CONFIRMATION_LIMITED_SAMPLE`。JST 2026-10-02T18:47:38.100845+09:00。

fresh Core 542 anchors／13 OOF日／3fold、DOWN 75／UP 354。R1 12.93% → R2 9.70%。改善 3.2361 pp。

direct integrity PASS／independent PASS（mismatch 0）／R2 control PASS。この結果からEntry／EXITのルール、threshold、利益・取引成績を推論しない。測定不足／失敗を保持し、結果を見たscope追加や再fitは行わない。

## V4を救済しない

V4は `BLOCKED_V4_INTEGRITY / FAIL_CONTROL` のまま。R2のV4改善18.53%→15.38%（+3.15pp、95%CI+1.19〜+6.32pp）は過去exposedの観測であり、このWorkのfresh確認ではない。R3分類は `F3_CALIBRATION_INSTABILITY`。V4原本2784 manifest entriesと4指定hashを照合し、原本上書き0。

## Calibration researchとfresh確認を分ける

exposed-only research36fits、実装独立PASS/mismatch0。ROLLING_INNER_OOF_TEMPERATURE_V1のみ。R2 raw date LL0.765198→cal0.814415（+6.43%）、row Brier0.474282→0.502249（+5.90%）、ECE0.099226→0.181768。悪化を保持し追加family／結果後変更0。これはpromotion Evidenceではない。alpha1/T1.5がexposedの両foldで選ばれた事実はfreshの固定alpha/Tではなく、fresh outer train内で同じ有限methodを対称に適用する。

## Mandatory25 answers

| # | 問い | 結果 |
| ---: | --- | --- |
| 1 | V4 R3 failure分類 | F3_CALIBRATION_INSTABILITY。較正前の僅かな全体優位が、同じT0.5によるREALスコアのより大きいLL悪化で逆転。Path分布／alpha差は副次候補、因果断定しない。 |
| 2 | direct future leakage | 保存prefix・timestamp・partition・coefficients・whole-label provenance監査で未検出。全State/Path kernelの再auditやhistorical known_atの全面証明ではない。 |
| 3 | calibration前にもR3 failureがあったか | 全体では無い。raw REAL1.080486 < NULL1.097922。ただしfold3ではrawからREALがNULLより悪い。calibrated全体REAL1.493967 > NULL1.313498。 |
| 4 | R3をcandidateから外すか | はい。V5 primaryから外しdiagnostic-only。救済fit／feature tuning0。R4もdescriptive／nonpromotable。 |
| 5 | fresh Development確保 | 19日／44security／45security-session。追加scopeはmetadata上24日で固定、未取得日もsplit calendarに保持。 |
| 6 | V4 unavailable109件の回収 | 0件、fresh eligible export0件。原順序の1回pass、差し替え0。U58／raw24／HTTP400 provider27のまま。 |
| 7 | fresh OOF日数 | 13 |
| 8 | fresh evaluable fold数 | 3 |
| 9 | DOWN support | 75 |
| 10 | UP support | 354 |
| 11 | R1 dangerous FP | 67/518 = 12.93% |
| 12 | R2 dangerous FP | 45/464 = 9.70% |
| 13 | R1→R2改善pp・95%CI | 3.2361 pp、95%CI [1.0824, 6.7586] pp。日cluster1000 exactly once。単日subset CIはinformative扱いしない。 |
| 14 | R2 DOWN Precision／Recall／F1 | 38.46% / 40.00% / 39.22% |
| 15 | R2 UP Precision／Recall／F1 | 70.26% / 92.09% / 79.71% |
| 16 | 未較正LL／Brier／ECE | row LL 0.794894、date-equal LL 0.762407、row Brier 0.438263、ECE 0.138595 |
| 17 | 較正LL／Brier／ECE | row LL 0.852527、date-equal LL 0.820150、row Brier 0.472208、ECE 0.185937 |
| 18 | 新calibrationはouterで悪化したか | date LL +7.57%、row Brier +7.75% の相対変化。5%非致命的悪化gate FAIL。ECEも保存。Tはouterの結果で選び直さない。 |
| 19 | R2 TRUE_NULL PASSか | PASS。candidate-local calibrated LLと事前固定90% positive-gain equivalence。rawも保存。R3の過去failureによる自動BLOCKなし。 |
| 20 | concentration PASSか | PASS。gross dangerous-error reduction／class correctness gain各々の最大1日・1security share<=0.5。詳細CSV、fold／current Stateも保存。acquired44securityのうちOOFにavailable targetがあるのは16security。 |
| 21 | independent mismatch0か | 0、audit PASS。別logic、候補helper import0、fit0、新bootstrap0。 |
| 22 | State9／Path／target／family changes | 各0。profile／M0も0。V4原本status／Contract／Precommit／scope／OOFのhashを保持。 |
| 23 | Holdout／Protected／Entry／EXIT／profit exposure | V5 delta各0。Fresh-validation reserve／OOS／Prospective／orders／broker write／Capital／Portfolio／externalAIも0。過去unknown/nonzero exposure履歴は消さない。 |
| 24 | Hybrid Entryへ進めるか | いいえ。今回のfinal gateを満たしていない。V4やexposed researchをfresh確認として救済利用しない。 |
| 25 | 渡すState representation | promotion representationなし。Bならclass/rank Evidenceのみ保持し、probabilityを信頼できる確率として渡さない。C/D/F/Eなら確認済みcandidateと呼ばない。 |

## R1／R2の比較

| fresh metric | R1 calibrated | R2 raw | R2 calibrated |
| --- | ---: | ---: | ---: |
| dangerous UP→DOWN | 12.93% | 9.70% | 9.70% |
| DOWN P / R / F1 | 33.33% / 10.67% / 16.16% | 38.46% / 40.00% / 39.22% | 38.46% / 40.00% / 39.22% |
| UP P / R / F1 | 66.99% / 98.02% / 79.59% | 70.26% / 92.09% / 79.71% | 70.26% / 92.09% / 79.71% |
| balanced accuracy | 27.17% | 33.02% | 33.02% |
| fixed4-class macro F1 | 23.94% | 29.73% | 29.73% |
| overall accuracy | 65.50% | 65.68% | 65.68% |
| date-equal logloss | 0.958697 | 0.762407 | 0.820150 |
| row Brier | 0.556025 | 0.438263 | 0.472208 |
| top-label ECE | 0.143825 | 0.138595 | 0.185937 |

R2のDOWN recallは40%、従ってDOWNの60%はDOWN classとしては検出していない。dangerous rate9.70%とは分母が異なる。UP recallはR1から低下し、overall accuracy改善は小さい。R2 calibratedはR1 calibratedよりLL/Brierが良いが、自身のrawからの悪化が5%gateを超えるためprobability gateはFAIL。positive temperatureはhard argmax/rankを変えず、較正でhard signalが改善したとは言わない。

## Gateと不確実性

sample FAIL、dangerous hard signal PASS、major reversal PASS、calibration FAIL、concentration PASS。固定priorityに従う。statistical control failureはdirect leakageと同義ではない。9State secondaryは今回任意未実施、V4/V3の保存表はParentに保持。Path anatomyもdescriptive既存Evidenceのみで新規rule化0。

historical known_atはUNKNOWNを維持し、bar-endでcausal availabilityが成立するという仮定を別記する。このresearchは実運用／約定／profit検証ではない。DOWNを見逃すRecallと、UP予測がDOWNだったdangerous rateは別指標。hard classificationとprobability qualityも分ける。

## Recoveryとfinite budget

109件回収0、U58／RAW24／provider HTTP400 27。追加24日はmetadataで事前固定、最大72security-session、原SHA順first3 factor-compatible。成功入力だけをfreshへ入れ、失敗security/dateの差し替え0。scope／split／precommitをfresh labelsより前に固定。新provider 723/900 HTTP、kernel 14715/40000 slots、research 36/80 fits、fresh 108/160 fits、total 144/240、Actions 2/2、bootstrap 1000/1000 once。独立新fit/draw0。V1の3000/cap1000 breach、V2 ledger gap、old16FAIL／88workflow incidentを継承しresetしない。

追加72件はACQUIRED45、PROVIDER_FAILURE15、U_UNAVAILABLE7、RAW_UNAVAILABLE5。原109と合わせた未取得は136security-session。新scopeを結果後に補充していない。provider原ページはrunner一時領域でpurge済みで、原ページそのものはこの納品から復元できない。features／State trace／M0検証／source hashは保存。今回の再取得を繰り返して復元しない。

GitHub専用branch state-predictiveness-v5-r2-confirmation-20261002-v1。C0〜C7のpost-commit GETはCHECKPOINTSを参照。main merge0／force push0。最終HEAD・code location index・delivery hashは各receiptを参照。

## 後でEXIT研究へ再利用可能なEvidence

UP_CONTEXT continuationとDOWN reversalのevent-order target、PULLBACK／RISE_STOP／DROP_STOP／RANGEを区別する固定State family、保存済みPath anatomy length1〜4、gap/reset/segment・causal timestamp・support/concentrationの証跡。これはEXIT/HOLD判断やprofitルールではなく、将来の別事前固定研究へのdescriptive入力候補のみ。

## Delivery

2〜3個の通常ZIPを同じdirectoryへ展開。完全なCSV／JSON／OOF／fits／labels／features／trace／raw hash receipts／Parent V4／元V3 ZIPを保持。再取得／再fit／label再生成／bootstrap再生成は禁止。DELIVERY_MANIFEST.json／SPLIT_PACKAGE_MANIFEST_V5.jsonで全memberのhashとZIP配置を照合できる。Git-backed sourceはSOURCE_CODE_LOCATION_INDEX_V5.jsonのexact commit/path/SHAを使用。
