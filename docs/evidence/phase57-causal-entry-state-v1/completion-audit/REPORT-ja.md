# Causal Entry State v1 — 完了監査・日足ablation補正

2026-09-21 JST。開始時GitHub最新HEADは `08e902c4ae8e23971a2b7f671e435fec91af5244`。
依頼されたv1研究は同HEADに保存済みだったため、既存成果を監査し、追加検証を行った。
元のPath・State・Signal・Timing・Evidenceは変更していない。全2,155 Opportunitiesを保持。

結論：**現在Stateと日足に識別情報の兆候はあるが、今回の固定TimingはImmediateを上回らない。Entry vNext学習・Freezeへ進めるEvidenceは不十分。STOP。**

## 1. 保存済み研究の検証

- 元protocol SHA256: `553732d1ca5dd5c03bc88e0aab22ee535bd8c6f9754a289bcc282c4ace701643`。
- [実行CI 35553422490](https://github.com/Iam-2squared/ark-terminal/actions/runs/35553422490)をGitHub直接確認：SUCCESS。
- 実行SHA: `4bb83f2e7f4cc73106f9cfd7a69cf96efe402b4c`。
- 元receiptの714 Evidenceファイル・implementation pins・manifestを再検証：PASS。
- 元研究の143 focused testsを再実行：PASS。今回の補正テスト2件を追加。
- 元CIの回帰receipt：Predict 2,765 / Discovery 26 / Foundation 39 / Python 30 / RSS 89、計2,949 PASS。
- 元CIはDaily、measurement、reportを各2回生成し一致。今回は元receiptと全hashを再検証し、補正diagnosticを2回生成してbyte一致。
- 開始HEADのActionsは68件すべてaction_required、当該専用runにはjobなし。実行済み研究のSUCCESSと開始HEAD/PR全体GREENを混同しない。承認原因は断定しない。

## 2. Future Path 5+1

| Future Path（評価専用） | 件数 | 全体比 |
|---|---:|---:|
| DIRECT_CONTINUATION | 50 | 2.32% |
| PULLBACK_RECOVERY | 202 | 9.37% |
| CONSOLIDATION_BREAKOUT | 10 | 0.46% |
| MULTI_SWING_CHOP | 828 | 38.42% |
| PERSISTENT_WEAKNESS | 76 | 3.53% |
| AMBIGUOUS_INSUFFICIENT | 989 | 45.89% |

Path6：INSUFFICIENT_OBSERVATION 496 / NO_DOMINANT_PATH 355 / TRUE_MIXED_PATH 138 / MISSING_PATH_DATA 0。定義変更や件数合わせは未実施。
観測不足496件は終日評価不能63件だけを意味しない。最低future行数・残存active時間などのPath用条件も含む。596件の低upside群とも別。

![元研究のPath・Capture・fill](../ci-result/report/01-paths-and-timing.png)

## 3. Recent Daily：補正したpaired ablation

全5日日足利用可能は1,961/2,155。残り194件も保持。144 Development sessionsは許可データ範囲で、2,155件の評価session数は58。最初29日fit／後半29日診断であり独立OOSではない。

**監査発見：元INTRADAYにも日足由来6特徴が混入。** dailyHighDistance / dailyLowDistance / dailyCloseDistance / fiveHighDistance / fiveLowDistance / todayGap。
元比較は「日足ゼロ vs 日足追加」ではない。未来情報漏洩ではなくablationの入力分離不備。
補正手順は結果生成前に `adc10af980584b2df78dcd0f577bd4ba1359e5ea` で追加precommit。
同じ特徴値をDAILY名前空間へ移し、strict INTRADAYから除外。元classifier・fit/test・missing処理は固定。
PLUS_DAILYの全予測は元結果と一致。元Evidenceは上書きしていない。

| T+active min | paired test N | Accuracy 日足なし→あり | Balanced Accuracy 日足なし→あり | Balanced差 |
|---:|---:|---:|---:|---:|
| 0 | 1,082 | 29.21%→46.95% | 32.06%→37.98% | +5.92pp |
| 5 | 1,082 | 50.74%→52.03% | 36.10%→33.83% | −2.27pp |
| 10 | 1,082 | 29.57%→49.63% | 36.61%→42.06% | +5.45pp |
| 15 | 1,082 | 25.97%→44.09% | 34.08%→37.31% | +3.23pp |
| 30 | 995 | 33.77%→47.44% | 27.97%→32.90% | +4.92pp |

T0のpaired正誤：両方正解232 / 日足のみ正解276 / 分足のみ正解84 / 両方誤り490。
ただしfit多数派Path6を全件予測する参照でもT0 Accuracyは45.01%。46.95%だけを高精度と解釈しない。
T+5でBalancedが低下し、後刻は答えの一部を既に観測している。安定した早期Path予測能力やTiming改善の立証ではない。
元reportのDaily ablation表・画像は初回記録として残し、日足ゼロ比較の解釈には本補正を使用する。

## 4. State transition / State × Signal

T0 UNKNOWN 1,270/2,155（58.93%）、TRENDは2件のみ。現状の観測・lookback・欠測条件のもとでは、全Opportunityの現在Stateを十分理解できていない。
有効な隣接minute遷移181,514件、State変更49,907件。TREND→PULLBACK 491、PULLBACK→TREND 194。延べ観測であり独立標本数ではない。RECOVERYは独立contextとして保存。

| T0 State | N | 固定Signal解釈 | Cのpaired買値改善mean | +3 Capture A→C | 解釈 |
|---|---:|---|---:|---:|---|
| TREND | 2 | Continuation / Breakout | +0.186% | 100%→0% | 標本不足。TrendではWAITが不利か未判定 |
| PULLBACK | 295 | Higher Low / Wick / Reclaim | +0.100% | 94.85%→80.88% | 買値改善と取り逃しが併存 |
| COMPRESSION | 127 | Expansion / Breakout | +0.049% | 97.87%→89.36% | 確認後のCapture低下 |
| CHOP | 106 | Higher Low / Reclaim＋range位置 | −0.165% | 94.44%→80.56% | 今回は高値買い・Capture悪化 |
| WEAKNESS | 107 | 同一closed barでHigher Low＋Reclaim | −0.284% | 97.30%→75.68% | 買値・MAE・Captureの改善を確認できず |

全StateのN/fill/MFE/MAE/WAIT/Low/retention表、Signal true/false/unknown、co-occurrenceは元reportとrawに保存。
State適合Signal Cでもfallback 1,957/2,155（90.81%）。State別signalが有効なBUY時刻を十分早く出せたとは言えない。

![元研究のState遷移・買値](../ci-result/report/03-transitions-state-price.png)

## 5. Opportunityを固定したTiming結果

| Arm | Fill | +3 Capture | +5 Capture | paired買値改善mean | WAIT中央値 | Range retention中央値 |
|---|---:|---:|---:|---:|---:|---:|
| A Immediate＋same retry | 1,963 | 85.28% | 87.50% | 0% | 0分 | 57.18% |
| B State-aware early | 1,857 | 68.33% | 70.59% | −0.0212% | 10分 | 53.96% |
| C State適合Signal | 1,857 | 69.78% | 71.57% | −0.0125% | 10分 | 53.80% |
| F 固定fallback | 1,857 | 67.54% | 70.59% | −0.015% | 10分 | 53.86% |

全arm 2,155件、modelRejection=false。fill低下をOpportunity除外で隠していない。全BUY intentにfallback/retryあり。
CはFより+3 Capture +2.23ppだが、Aより−15.51pp、+5 −15.93pp、fill −106。Immediate超えEvidenceなし。
次open＋5bpの履歴fill proxyであり、注文・実現利益ではない。

## 6. Low proximity / Upside retention / failure anatomy

- 有効なAFTER_LOWはA 84件、C 739件。Low距離中央値A +0.537%、C +1.118%だが、異なる有効集団なので直接paired改善と扱わない。
- CではEntry-before-low 1,009、same-bar unknown 53、Direct不適用43、観測不足13、no-fill 298を別計上。
- Cの有効paired買値：安い720 / 同値300 / 高い837。unpaired 298。
- Cの重複可能failure flags：安く買ったが+3 Capture喪失2、MAE改善と+3喪失15、Lowへ近づきretention非悪化5。
- Cのoracle HighがEntry以前／同時94件（A 11件）。WAITが上昇の後になるケースもある。
- retention中央値は有効集団の記述値。Low前、分母非正、High前後、same-bar、欠測を混ぜて改善とは呼ばない。

![元研究のLow・retention](../ci-result/report/04-low-retention.png)

Signal自体が無価値とは確定できない。今回の固定mapping、観測不足、認識遅延、fallback依存が重なり、各原因の因果寄与を完全には分離できていない。

## 7. Entry vNextへのfeature候補とSTOP

候補：Daily return/trajectory/HH-HL/LH-LL/range/volume/value＋missing mask、intraday efficiency/drawdown/depth/age/recovery、compression比率・継続時間、reversal count、VWAP位置・傾き・滞在比、6 SignalのEvent/State/Context・因果的初回時刻・activity。
future Path/Low/High/MFE/MAEは評価専用。decision featuresへ渡さない。

**現段階でvNext学習・Freezeを正当化するEvidenceは不十分。** 狭い一部Stateの買値改善を全体改善に置き換えない。
Dictionary追加0、Holdout/Fresh/OOS/Prospective消費0、新規価格取得0、Selector変更0、NEW EXIT/Capital変更0、全9 safety flags false。PRはDraftのまま。STOP。

補正再生成：`python -m scripts.phase57_causal_entry_daily_audit --output <new-empty-directory>`。
元研究詳細：[REPORT-ja.md](../ci-result/report/REPORT-ja.md)。補正raw：[audit.json](corrected/audit.json)、[diagnostic.json.gz](corrected/diagnostic.json.gz)、[predictions](corrected/predictions.json.gz)。
