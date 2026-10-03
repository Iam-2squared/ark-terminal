# 銘柄別Dictionary Profile coverage

**判定：標本精度のcoverageは定量化。NEW LONG Entry/EXITへの引渡しは未成立。**

事前固定した60-position snapshotを主表とし20/250も全件保存。HIGH/MEDIUMは標本精度の診断ラベルであり、銘柄固有の時間再現性・校正済み信頼確率・収益性の認定ではない。旧registry・Gate・判定は不変。

## 1–2. 固定USABLEの個別Profile

| lane / trait | 全銘柄 | 算出可 | HIGH | MEDIUM | LOW | INSUFFICIENT | H+M割合 |
|---|---:|---:|---:|---:|---:|---:|---:|
| daily / inside | 4010 | 3805 | 0 | 0 | 3805 | 205 | 0.00% |
| daily / gap_fill | 4010 | 3677 | 0 | 0 | 3677 | 333 | 0.00% |
| daily / gap_cont | 4010 | 3677 | 0 | 0 | 3677 | 333 | 0.00% |
| daily / amihud | 4010 | 3805 | 607 | 1690 | 1508 | 205 | 57.28% |
| intraday / amihud | 3899 | 3767 | 623 | 1499 | 1645 | 132 | 54.42% |
| intraday / value_O30 | 3899 | 1807 | 558 | 934 | 315 | 2092 | 38.27% |
| intraday / value_AM | 3899 | 1807 | 300 | 1102 | 405 | 2092 | 35.96% |
| intraday / value_PM1 | 3899 | 1806 | 127 | 1103 | 576 | 2093 | 31.55% |
| intraday / pdh_break | 3899 | 366 | 0 | 120 | 246 | 3533 | 3.08% |

各traitの人数/割合、nSessions/nEff/episodesのp10/median/p90、shrinkWeight、posterior SD、正規化不確実性、trait値、peer差、層別coverageは01_trait_coverage.json。全対象銘柄と算出可能銘柄の統計を分離。セルごとの全値はall-symbol-profiles.csv.gz。

episodesは条件付きtraitのevent-bearing sessionsのみ。非条件付きPDH break等の正の発生session数はeventPositiveSessionsであり、個別episode数とは異なる。INSUFFICIENTで数値peer priorが存在するとは限らない。

## 3. Calibration-only WATCH23判定

| lane / trait | raw | incremental | slope | H+M / 全銘柄 | peer差あり H+M |
|---|---:|---:|---:|---:|---:|
| daily / body_range | 0.3394 | 0.2261 | 0.2174 | 0 / 4010 | 0 |
| daily / large_up | 0.4131 | 0.1894 | 0.1715 | 0 / 4010 | 0 |
| daily / doji | 0.3158 | 0.3778 | 0.4745 | 0 / 4010 | 0 |
| daily / long_lower | 0.4612 | 0.3492 | 0.3556 | 0 / 4010 | 0 |
| daily / outside | 0.4537 | 0.3252 | 0.4622 | 0 / 4010 | 0 |
| daily / trend_day | 0.7081 | 0.3738 | 0.4119 | 0 / 4010 | 0 |
| daily / range_s | 0.6170 | 0.4262 | 0.3394 | 2 / 4010 | 1 |
| daily / range_exp | 0.7712 | 0.3338 | 0.3188 | 0 / 4010 | 0 |
| daily / range_con | 0.7328 | 0.4477 | 0.4802 | 0 / 4010 | 0 |
| daily / gap_up | 0.5945 | 0.4404 | 0.4537 | 0 / 4010 | 0 |
| daily / gap_dn | 0.5454 | 0.4532 | 0.4758 | 0 / 4010 | 0 |
| daily / overnight_var_share | 0.6699 | 0.4408 | 0.3952 | 1 / 4010 | 1 |
| daily / value_shock | 0.8616 | 0.4134 | 0.4717 | 0 / 4010 | 0 |
| daily / jump | 0.3750 | 0.1960 | 0.2441 | 0 / 4010 | 0 |
| intraday / inside | 0.5949 | 0.2953 | 0.4477 | 0 / 3899 | 0 |
| intraday / trend_day | 0.5170 | 0.3113 | 0.4761 | 46 / 3899 | 23 |
| intraday / range_con | 0.5865 | 0.2265 | 0.3146 | 375 / 3899 | 52 |
| intraday / gap_fill | 0.3894 | 0.1558 | 0.4712 | 30 / 3899 | 1 |
| intraday / overnight_var_share | 0.3946 | 0.2170 | 0.3109 | 89 / 3899 | 16 |
| intraday / value_shock | 0.5980 | 0.1906 | 0.3238 | 1 / 3899 | 1 |
| intraday / value_CL | 0.9534 | 0.7944 | 1.8264 | 1292 / 3899 | 901 |
| intraday / range_PM1 | 0.4397 | 0.2685 | 0.4674 | 471 / 3899 | 49 |
| intraday / volume_CL | 0.9533 | 0.7943 | 1.8251 | 1291 / 3899 | 901 |

23は日足14＋分足9のlane別判定数。calibration以外の旧Gateは通過。global/reverseの符号とA/B raw中心化符号一致はJSON。B peer残差が保存されていないため、後者を個別銘柄のpeer残差sign persistenceとは呼ばない。

補正可能性は仮説。観測したB slopeを掛けて同じBで合格とはしない。A内の有限方式と別時間Development区間で校正・誤差・driftを検証する必要がある。今回は補正fit/USABLE昇格なし。

## 4–5. Trait数分布と統合

| 対象（60 window） | 0 | 1–2 | 3–5 | 6–10 | 11+ |
|---|---:|---:|---:|---:|---:|
| daily available | 201 | 136 | 3673 | 0 | 0 |
| daily hm | 1713 | 2297 | 0 | 0 | 0 |
| intraday available | 132 | 1960 | 1807 | 0 | 0 |
| intraday hm | 1477 | 1087 | 1335 | 0 | 0 |
| archival union available | 190 | 102 | 2087 | 1701 | 0 |
| archival union hm | 1185 | 1509 | 1386 | 0 | 0 |

コード和集合4080、共通集合3829。同じtrait IDは重複カウントしない。推定値は混合しない。available=有限Profile、hm=USABLEかつHIGH/MEDIUM。WATCHはtrait数に含まない。

日足終端2024-09-13、分足終端2025-08-25。統合は履歴上の和集合であり同時点のProfileではない。Reader未成立・銘柄別再現性未検証も含め、現在検証済みでEntry/EXITへ渡せる銘柄は0。性格が存在しないという意味ではなく引渡し条件未達。

## 代表銘柄：保存されている知識

PDH confidence群とH+M trait数からコード順で機械選択。値はraw、peer差は変換後で単位が異なる。driftは保存済み指標、銘柄別時間再現性は未確認。

### Code 16050 — first_code_PDH_MEDIUM

| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |
|---|---:|---:|---|---|---|
| daily / inside | 0.08333 | -0.3359 | LOW | 60 / — | False |
| daily / gap_fill | 0.1667 | -0.4528 | LOW | 24 / 24 | False |
| daily / gap_cont | 0.5417 | -0.1051 | LOW | 14.74 / 24 | False |
| daily / amihud | 1.238e-12 | 0.09353 | HIGH | 58.43 / — | False |
| intraday / amihud | 8.929e-13 | 0.5401 | MEDIUM | 39.82 / — | False |
| intraday / value_O30 | 0.21 | 0.1666 | HIGH | 42.91 / — | False |
| intraday / value_AM | 0.2437 | 0.171 | HIGH | 53 / — | False |
| intraday / value_PM1 | 0.1626 | 0.0355 | MEDIUM | 53 / — | False |
| intraday / pdh_break | 0.5957 | 0.09827 | MEDIUM | 36.64 / — | False |

### Code 14170 — first_code_PDH_LOW

| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |
|---|---:|---:|---|---|---|
| daily / inside | 0.06667 | -0.8627 | LOW | 60 / — | False |
| daily / gap_fill | 0.3333 | 0.08892 | LOW | 12 / 12 | UNKNOWN |
| daily / gap_cont | 0.5 | 0.02865 | LOW | 12 / 12 | UNKNOWN |
| daily / amihud | 2.559e-11 | 0.2397 | MEDIUM | 32.21 / — | False |
| intraday / amihud | 1.09e-11 | 0.1302 | HIGH | 53 / — | False |
| intraday / value_O30 | 0.1614 | 0.02258 | MEDIUM | 35.79 / — | False |
| intraday / value_AM | 0.2098 | -0.0782 | HIGH | 41.19 / — | False |
| intraday / value_PM1 | 0.1896 | 0.04376 | HIGH | 50.82 / — | False |
| intraday / pdh_break | 1 | 0.1364 | LOW | 21 / — | UNKNOWN |

### Code 13010 — first_code_PDH_INSUFFICIENT

| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |
|---|---:|---:|---|---|---|
| daily / inside | 0.2 | 0.2649 | LOW | 60 / — | False |
| daily / gap_fill | 0.5385 | 0.7717 | LOW | 13 / 13 | UNKNOWN |
| daily / gap_cont | 0.4615 | 0.01957 | LOW | 13 / 13 | UNKNOWN |
| daily / amihud | 1.077e-10 | 0.09679 | MEDIUM | 53.96 / — | False |
| intraday / amihud | 4.626e-11 | 0.5067 | MEDIUM | 53 / — | False |
| intraday / value_O30 | 0.2392 | 0.2567 | MEDIUM | 27.09 / — | UNKNOWN |
| intraday / value_AM | 0.2528 | 0.1133 | MEDIUM | 32 / — | UNKNOWN |
| intraday / value_PM1 | 0.1983 | -0.03996 | LOW | 32 / — | UNKNOWN |
| intraday / pdh_break | 1 | — | INSUFFICIENT | 12 / — | UNKNOWN |

### Code 13750 — first_code_HM_count_0

| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |
|---|---:|---:|---|---|---|
| daily / inside | 0.2 | -0.159 | LOW | 60 / — | False |
| daily / gap_fill | 0.2727 | -0.6403 | LOW | 11 / 11 | UNKNOWN |
| daily / gap_cont | 0.5455 | 0.5874 | LOW | 11 / 11 | UNKNOWN |
| daily / amihud | 1.712e-10 | 0.6761 | MEDIUM | 60 / — | False |
| intraday / amihud | 1.022e-10 | -0.1658 | LOW | 53 / — | False |
| intraday / value_O30 | 0.2691 | — | INSUFFICIENT | 13.69 / — | UNKNOWN |
| intraday / value_AM | 0.2202 | — | INSUFFICIENT | 2.769 / — | UNKNOWN |
| intraday / value_PM1 | 0.2016 | — | INSUFFICIENT | 18 / — | UNKNOWN |
| intraday / pdh_break | 1 | — | INSUFFICIENT | 3 / — | UNKNOWN |

### Code 130A0 — first_code_HM_count_1

| lane / trait | raw | peer差 | confidence | nEff / event sessions | drift |
|---|---:|---:|---|---|---|
| daily / inside | 0.2167 | 0.4056 | LOW | 58.42 / — | False |
| daily / gap_fill | 0.5 | 0.7691 | LOW | 0.4211 / 8 | UNKNOWN |
| daily / gap_cont | 0.375 | -0.5555 | LOW | 0.4211 / 8 | UNKNOWN |
| daily / amihud | 5.645e-10 | -0.1449 | MEDIUM | 58.45 / — | False |
| intraday / amihud | 4.558e-10 | 0.4786 | MEDIUM | 20.25 / — | False |
| intraday / value_O30 | 0.2977 | 0.2655 | LOW | 16.9 / — | UNKNOWN |
| intraday / value_AM | 0.3293 | 0.1495 | LOW | 24.72 / — | UNKNOWN |
| intraday / value_PM1 | 0.178 | -0.3746 | LOW | 22.33 / — | UNKNOWN |
| intraday / pdh_break | 1 | — | INSUFFICIENT | 7 / — | UNKNOWN |

## 層別coverageの根拠

A peer予測/係数/標準化パラメータの線形恒等式から共変量を復元。6式以上、末尾2式の検算、rank/条件数/残差/logVa参照値の検証を要求。識別不能座標はUNKNOWN。層は現在価格等ではなくA-period履歴層。

daily: {"VERIFIED_FULL": 2722, "INSUFFICIENT_EQUATIONS": 246, "LOGVA_REFERENCE_FAILED": 1042}

intraday: {"VERIFIED_FULL": 3093, "LOGVA_REFERENCE_FAILED": 601, "INSUFFICIENT_EQUATIONS": 205}

peer差ありは |posterior−peer prediction| > 1.96×posterior SD の探索的分類。prior fit不確実性や多重比較を完全に反映せず、銘柄別有意差証明ではない。

## 6. Sparse Dictionary

globalStatus=USABLEかつHIGH/MEDIUMのみ候補payload。LOW/INSUFFICIENTはabstain、WATCHは研究sidecar。definition hash、units/transform、nEff、SD/CI、drift、computed_throughを保持。時点・単位・Reader freshnessが未成立ならpayload全体を引渡し不可。confidenceラベルを新しい実用Gateに自動昇格しない。

## 7. 事前固定した修正仕様

correction-spec.jsonが正本。Pullbackは同一session/phaseの連続5m列で確認済み上昇impulse→直後の確認済み下落correctionを比率化。欠損/昼休みでreset、availabilityはcorrectionの確認時刻。旧trait不変、新registry候補のみ。

Readerはdaily.Date/barValueを明示adapterで正規化。完全に閉じた5本から5m barを作る。lastCompletedBarは現在phaseのfloor(t/5)*5と一致、最大staleness4分。昼休み・phase外・最新bar欠測はUNAVAILABLE。古いbarへfallbackしない。今回は仕様のみで実装/再測定なし。

## 8. NEW LONG Entry/EXITへ渡すまで

(1)有限のPullback/Reader修正実装と因果性/鮮度検証、(2)同時点Profileと単位の整合、(3)銘柄別/peer別時間再現性とconfidence校正のDevelopment検証、(4)仕様固定が必要。HIGH/MEDIUMは(3)の代用ではない。成立した次工程でNEW LONG Entry/EXITを再設計し、旧版微修正には戻さない。今回は作らずSTOP。

## 検証・境界

ci-receipt.jsonとregression/regression.jsonが実行正本。生成2回manifest一致、旧Evidence hash不変、focused testsと全回帰。新規provider取得0、raw再測定0、Common Holdout244/REPORT19/Validation/OOS/Fresh追加payloadアクセス0、Entry/EXIT trial0。過去Exposure維持、Safety9項目false、main未merge。
