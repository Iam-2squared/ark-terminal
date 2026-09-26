# Phase57 — State Ground Truth Additional Diagnostics v1

**記録: 2026-09-21 20:24 JST**  
**Status: DIAGNOSTICS_1_TO_5_COMPLETE / STATE_V2_NOT_STARTED / HUMAN_REVIEW_REQUIRED**

## 結論

State Definition v1を変更せず、既存G measurementだけで5つの追加診断を実施した。**まだState Definition v2には進んでいない。**

1. D 2,154行の **strict residualは0行**。Direction / Phase / Attributes / Level / VWAP eventが全部空の行は存在しない。
2. B 11,326行のsame-session next Structure解決は **4,459/11,326 = 39.37%**。6,867行は同日最後までStructure未識別。pivot<4を一律FORMINGとは呼べない。
3. pivot3ほど、また観測密度が高いほど後続Structureへ解決しやすい。
4. SCALE_INSUFFICIENT群は絶対活動量は低いが、前日→当日の **相対活性化** が強い。前日Sのみへの依存が系統的な取りこぼしを生む可能性は診断課題として残る。
5. pivotSignature 3×3は同一セルがUP/DOWN/RANGE/Dへ跨る。**Structure classではなくdescriptorとして扱う**方向が支持された。

## 診断1 — 真の未記述集合

- D: 2,154
- strict residual: **0**
- Phaseなし+CHOPなし: 231（Direction/他Attributes/Eventsを含めると未記述ではない）
- Phase/全Attributes/Level/VWAP eventが全部空: 19。この19行にもDirectionは存在。
- descriptor presence: Direction 2,154 / Phase 1,868 / all Attributes 1,680 / CHOP 356 / Level event 1,323 / VWAP event 31。

**結論:** 旧231件をVocabulary gapの最優先集合とする根拠は撤回。Structureが空でも他軸は何かを記述している。ただし完全State coverageとは呼ばない。

## 診断2 — 層別チャート再抽出

**36 checkpoints / 36 Opportunities / 29 sessions**。9 signature × 4例。  
time band: OPEN 8 / AM 9 / PM_EARLY 9 / PM_LATE 10。

固定seed `phase57-state-additional-diagnostics-v1-seed-20260921` + SHA256順位、1 Opportunity最大1 checkpoint、PnL/return非使用。
図にactual 1m・pivot effective/confirmed・S reference・latest30 active-minute windowを重ね、欠測は補完していない。

36図の目視スポットチェックでは、同じsignatureでも一方向トレンド、底練り、急変後収束、レンジ様など文脈が異なる。signature単独をStructure名に昇格させる根拠にはならない。固定rubricの2名独立判定は未実施。

## 診断3 — B time-to-next-Structure

| pivotN | rows | resolved | resolved率 | resolved median | P25 | P75 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 3,723 | 966 | 25.95% | 35m | 20m | 70m |
| 1 | 4,091 | 1,544 | 37.74% | 30m | 15m | 55m |
| 2 | 2,185 | 1,094 | 50.07% | 25m | 15m | 45m |
| 3 | 1,327 | 855 | 64.43% | 10m | 5m | 25m |

Observation density quartile:
Q1 18.11% / Q2 28.95% / Q3 41.50% / Q4 69.08% が同日中に次Structureへ解決。

**解釈:** Bを単純にFORMINGへ昇格せず、pivot数とObservation Qualityを別軸で保持する方が妥当。

## 診断4 — SCALE_INSUFFICIENT vs AVAILABLE

| 指標 | AVAILABLE | SCALE_INSUFFICIENT |
|---|---:|---:|
| n | 1,005 | 1,105 |
| 前日regular bars median | 264 | 40 |
| 当日regular bars median | 285 | 82 |
| 当日/前日bar比 median | 1.01x | 1.71x |
| 寄り30分/前日全日Value median | 0.24x | 0.40x |
| 寄り30分Value > 前日全日Value | 7.66% | 26.15% |
| 当日bars > 前日bars | 52.54% | 79.46% |
| Selector時点までbars > 前日全日bars | 5.47% | 44.43% |

SCALE_INSUFFICIENT群は当日の絶対活動量も低いので、全部が突然活発化銘柄ではない。一方で **相対活性化の偏りは明確**。これはS定義の追加診断根拠であり、まだS変更の根拠とはしない。

## 診断5 — pivotSignature 3×3

| signature | UP | DOWN | RANGE | D |
|---|---:|---:|---:|---:|
| H_UP|L_UP | 1,784 | 0 | 21 | 177 |
| H_UP|L_EQ | 41 | 9 | 24 | 88 |
| H_UP|L_DOWN | 4 | 8 | 131 | 845 |
| H_EQ|L_UP | 83 | 36 | 16 | 73 |
| H_EQ|L_EQ | 34 | 116 | 20 | 74 |
| H_EQ|L_DOWN | 1 | 150 | 34 | 116 |
| H_DOWN|L_UP | 245 | 434 | 58 | 479 |
| H_DOWN|L_EQ | 41 | 160 | 51 | 104 |
| H_DOWN|L_DOWN | 0 | 3,473 | 5 | 198 |

D比: H_UP|L_DOWN 85.5%、H_UP|L_EQ 54.3%、H_DOWN|L_UP 39.4%、H_EQ|L_DOWN 38.5%、H_EQ|L_UP 35.1%、H_EQ|L_EQ 30.3%、H_DOWN|L_EQ 29.2%、H_UP|L_UP 8.9%、H_DOWN|L_DOWN 5.4%。

`H_DOWN|L_UP`はUP 245 / DOWN 434 / RANGE 58 / D 479と混在。**3×3 signatureだけでStructureを決められない。**
identified StructureでもpivotN<4のため3×3対象外: DOWN 470 / RANGE 1,235 / UP 125。

## 再現性 / Guard

- 診断1/5、診断3/4、診断2 sampleを独立2回実行し対象出力hash一致。
- local evidence manifest SHA256: `5e0ef437d86e7ae3e70e8f0df50a7e92ebb8c8fb22edec88616c12d568f79224`
- conversation ZIP SHA256: `1abde291d4a4cea59ebe59f48966ef5ba3fadff6c562e4eb4150d1168e7c7f79`
- State Definition変更0 / threshold変更0 / PnL 0 / future return 0 / provider 0 / protected data 0。

## STOP / 次

**State Definition v2・正確表v2・Causal Recognition・Signal・BUY/WAITには進まない。**
次はこのEvidenceを人間確認し、v2設計へ進むかを判断する。進む場合もv1を上書きせずside-by-side。
