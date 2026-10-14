# 新Selector V1 — 研究成果物の受入れ記録（運用品質未承認）

2026-10-14 JST / `ARK_PREOPEN_SELECTOR_V1_READ_ONLY_ACCEPTANCE_V1`

## 判定を混同しない

| 判定 | V1現時点 | 意味 |
| --- | --- | --- |
| RESEARCH_ENGINEERING_ARTIFACT_COMPLETE | **PASS** | 計算コード・モデルhash・学習/較正/監視候補固定・実市場測定・旧Frozen比較・別経路再計数の既存証跡が整合 |
| PREDICTIVE_QUALITY | **NOT_APPROVED** | 上昇機会が同条件の売買代金基準を下回り、低流動性に偏る |
| LIVE_READINESS | **NOT_CERTIFIED** | 最新D-1全市場入力とWindows/RSS実機の継続供給は未認証 |
| Fresh/OOS | **credit 0** | FIT30/較正10/Report7はすべて既閲覧Development |
| Entry/EXIT/Capital/Orders | **範囲外／禁止** | 朝の監視候補と約定可能な売買判断は別工程 |

**本書の「V1完成」は研究工程の成果物が揃ったことだけを意味する。品質合格・取引可能・本番昇格・Frozen統合版No.1/No.1.1への統合を一切意味しない。**

## 固定済みの設計と識別子

- repo: `Iam-2squared/ark-terminal`、Draft PR #593、base: `research/ark-integrated-no1-1-freeze-20261008` / `10c94c92c4bd2a59a22744667fd0210252602df4`
- 研究コード・計算の固定参照HEAD: `c1529e7db10f0d5ecf11f0884d1644d31f5aa9ec`
- source code SHA256: `3a2fb32dfad9e2ea4f9956038709f2a640a3380213f68ca7af8f1c9c621950ab`
- trained model SHA256: `e82279729b9ccc02fbcf7a1ffced7ade9057d8be41b058963dc4133e4ea19b48`
- schema SHA256: `79a81013c5903913f531de6d97e402f5f19d7f13b6657e58363483128574f243`
- policy SHA256: `c9294e40ab8024618b0858bb4c9ccd1f388a22575765f2f761da4ac8099edc7a`
- sealed split SHA256: `e18a181197927bed31b22fb376c42eb35fd0ed42dcabbbb88f7ffcc0b7208325`
- 朝08:50、前日RAW終値 >75円、現物普通株、日足SMA/EMA5/15/25/75、前日分足MA5/15/30/60、週/月独立MAなし。
- HistGradientBoostingClassifierの上昇5・下落4・Close負1の10head、FIT112,144行/較正37,484行/Report26,269行、FIT使用463列。1モデルcandidate/10head fit/10較正fit。順位は `sum(up1..5)-2*sum(down1,2,3,5)-closeNegative`。費用後EVではない。
- Reportは7営業日、7日×15=105監視銘柄日。モデルを別processでhash照合して再ロードし、固定105件の1,050 head再予測差0を記録。過去レポートlabel開封の前に全候補をhash固定。
- 元原本・モデル・個別候補・行特徴量はprivate。GitHubには非復元集計とhashのみ。小さな再開indexは全payloadではない。既存の保存済み本体・所有者の保存identityを引き継ぐ。

## 同条件基準との成績（実現損益ではない）

| 実際の当日Openを起点とする指標 | 新V1 | 前日売買代金上位15 |
| --- | ---: | ---: |
| 選出件数 | 105 | 105 |
| High ≥1% | **34** | **56** |
| High ≥3% | 10 | 13 |
| High ≥5% | 2 | 5 |
| Low ≤−3% | 5 | 17 |
| Low ≤−5% | 0 | 1 |
| UNKNOWN | 3 | 0 |

新V1は下落側が相対的に少ない反面、上昇機会の検出が弱く、105件中87件が前日売買代金LOW三分位。上昇≥1%差は−20.9524 percentage points。7日の日対応bootstrap95%記述区間は[−44.7619,+2.8571]pp。評価日は旧Frozen親のFIT露出期間内であり、旧日中K5×10時刻と寄り前K15の数字を同条件の性能差にはしない。Highで全数量売却できたと仮定しない。

## 未解消の入力観測差（学習変更ではない）

現行の列別coverageによると、FITで使用された**5つの前日Tick特徴**が較正・Reportでは全欠測：
`tick_burst_relative_1m` / `tick_realized_volatility_1m` / `tick_realized_volatility_5m` / `tick_up_tick_ratio_1m` / `tick_up_tick_ratio_5m`（正式feature名には `preopen_previous_tick_` が付く）。

これは**確定したcoverage差**であり、原因やモデル成績への寄与は未確定。2024-11-05以後の取引時間・引けの窓との関係は検証仮説であり、Reportで勝つように窓・列・K・係数を変更する許可ではない。StateのReport観測も8,561／26,269行（約32.59%）にとどまり、未観測を形式的な状態や0で補完しない。

## 読み取り専用受入ゲート

```bash
python research/independent-long-selector-20261012-v1/v1_acceptance/verify.py
python -m unittest discover -s research/independent-long-selector-20261012-v1/preopen_tests -p "test_v1_acceptance.py" -v
```

- 固定公開証拠11ファイルのGit blob SHA、固定計算コードの全直下`*.py` SHA256結合、モデル/スキーマ/ポリシー/partition結合を検査。
- 集計CSVとReport、別算式原本再計数、source coverage、UNKNOWN、品質未承認、全11の執行停止flagを検査。
- 結果は標準出力の非復元集計receiptのみ。外部通信、privateモデルload、学習、原本再読取、注文、ファイル上書きは一切行わない。
- **PASSするのは工学研究成果物の整合だけ。** 品質未承認は必ず保持し、LIVE認証と誤認させない。
- 計算コードのroot `*.py` を一切変更しない。追加検査コードはサブディレクトリに設置し、既存model `sourceCodeHash` を保つ。

## 次候補・運用について

品質を改善するには、順位の上下方向寄与・流動性・欠測・較正・2024-11-05前後の観測窓を**記述診断として分離**し、次candidateの仕様（変更理由・学習区間・候補budget・独立評価/既閲覧区分）を事前提示して所有者承認を得る。現行7 Report日でスコアや閾値を探索しない。

将来の毎朝D−1更新、RSS実機、売買容量、Entry/EXIT/一銘柄現物現金集中・売却後の慎重な順次回転は別工程であり、V1の研究受入から切り離す。

**禁止：** main merge、Frozen No.1/No.1.1・旧weights/spec・State9原本・PR #591変更、強制push、実注文、paper、RSS注文、口座・Excel書込み、保護期間の新規開封、無断学習・自動昇格。
