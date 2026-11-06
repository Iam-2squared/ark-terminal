# ARK TERMINAL FIRST LAYER C11 — Development研究完了

**終了status: FIRST_LAYER_C11_RESEARCH_COMPLETE_DEVELOPMENT**

C11はC10/M20と同じMINUS KEEP 33/172で、≥5% Winner KEEPが7/20→8/20になった。PLUS全体は40/144→39/144。M40/M60はMINUS KEEPが各9件減る一方、≥5% Winnerは各1件減り、PLUS全体も減る。局所的なranking改善Evidenceとして保持し、単一Championには認定しない。Fresh/OOS=0のDevelopment結果であり、性能PASSやCapital改善ではない。

## 1. C09/C10 final readback recovery

既存final HEADは指示書と一致。public59ファイル、private archive11 partsをactual GETし、アーカイブ内168メンバー（証拠167 + 内部manifest1）のpath/bytes/SHA256/blobを照合、mismatch0。private側の同名public59ファイルもblob/bytes metadata一致。REPORT/RESULTS/SUMMARY/AUDIT/NEXT_ACTIONの本文GETを含む。C09/C10再fit・preprocess・threshold・inference・feature build・RAW scanはすべて0。

復旧publication最終HEAD: public `d9d7526778963afc709175575006d82f7cc6b64d` / private `0981fd71d4c3400d31fad99f831700e7b336a8c1`。receipt/publication自身もactual GETした。既存V1/C03/C08/WB01/C09/C10/Pareto/失敗記録は親treeから継承し、変更していない。

## 2. C11 事前固定と実行量

C11_PRECOMMIT、固定segmentation仕様、107 field registry、source pins、予算amendmentをpublic/privateへ保存しactual GETしてから実装。PRECOMMIT HEAD public `60b2a124b57acbd172ae3ab8675d61635fe67dd4` / private `c8558bcdd8ffd6e3b828e001735e4204bbf3fd25`。

teacher-blindな完成済みprefixを、上昇/厳密な横ばい/下落の最大連続区間に分け、直近6区間を古い順で表現。107 native numeric fields +107 missing masksを追加。C06固定8区間との同義追加0、C10 alias追加0、既存C10列の値変更0。新しいpreprocessing fit0。State9のRISE/PULLBACK定義は変更0。native11:30処理は修復済みC10と同じ。

| 項目 | C11追加 | 累計 |
|---|---|---|
| cycle | 1 | 11 |
| model fit | S1 1 + S2 1 = 2 | 36 |
| preprocessing fit | 0 | 30 |
| aggressive threshold | 10 | 150 |
| CAL95 reference | 2 | C09/C10/C11で6 |
| CAL95込み全threshold arithmetic | 12 | 156 |
| REPORT501追加 | 0 | REPORT 6/6維持 |
| model retry | 0 | 0 |

HGB7はC10と完全同一：max_leaf_nodes7 / max_depth3 / max_iter200 / learning_rate0.05 / min_samples_leaf30 / L2=1 / random_state570107 / early_stopping false / class_weightなし / sample_weightなし。numpy2.3.5、sklearn1.8.0、1 thread。S1 FIT598/CAL159/DEV164、S2 FIT753/CAL164/DEV158。S1/S2 split・maturity・CAL・DEV_COMPARE・行順は固定。

decision seal public `b543edcb4bd14a3edbfd4146166cbcf9a9c80aa4` / private `801cda66fd85154c23e26ec156dc0c8d11a25ff7`。privateモデル/score/threshold/decision archive2 partsとpublic sealをactual GETし、25メンバーを照合してからCANONICAL_CAPITAL_R/Winner帯をjoin。

## 3. C11 全operating point：S1/S2/union

各セルは KEEP / N。DROP = N−KEEP。閾値はCAL sign+scoreだけから決定した。MxのxはCAL MINUS目標で、DEV MINUS率の保証ではない。

| point | S1 PLUS | S1 MINUS | S2 PLUS | S2 MINUS | union PLUS | union MINUS | union UNKNOWN |
|---|---|---|---|---|---|---|---|
| ALL_KEEP | 78/78 | 81/81 | 66/66 | 91/91 | 144/144 | 172/172 | 6/6 |
| CAL95 | 73/78 | 75/81 | 62/66 | 85/91 | 135/144 | 160/172 | 5/6 |
| M80 | 68/78 | 62/81 | 58/66 | 80/91 | 126/144 | 142/172 | 4/6 |
| M60 | 49/78 | 33/81 | 46/66 | 53/91 | 95/144 | 86/172 | 2/6 |
| M40 | 37/78 | 21/81 | 31/66 | 31/91 | 68/144 | 52/172 | 2/6 |
| M20 | 19/78 | 13/81 | 20/66 | 20/91 | 39/144 | 33/172 | 0/6 |
| M10 | 8/78 | 8/81 | 4/66 | 8/91 | 12/144 | 16/172 | 0/6 |

union CAL95 PLUS KEEP=135/144=93.75%、MINUS KEEP=160/172=93.02%。M20 PLUS KEEP=39/144=27.08%、MINUS KEEP=33/172=19.19%、MINUS DROP=139/172=80.81%。ZEROは全point N0。

## 4. Winner帯と累積KEEP

下表はunionのKEEP/DROP。排他的帯のNは順に54/34/26/6/4/20。3–4%はN6、4–5%はN4なので件数で確認する。S1/S2の全帯別N/KEEP/DROPはWINNER_BAND_KEEP_DROP.csvとRESULTS.jsonに保存。

| point | 0–1% (N54) | 1–2% (N34) | 2–3% (N26) | 3–4% (N6) | 4–5% (N4) | ≥5% (N20) |
|---|---|---|---|---|---|---|
| ALL_KEEP | 54/0 | 34/0 | 26/0 | 6/0 | 4/0 | 20/0 |
| CAL95 | 47/7 | 34/0 | 24/2 | 6/0 | 4/0 | 20/0 |
| M80 | 44/10 | 31/3 | 23/3 | 5/1 | 4/0 | 19/1 |
| M60 | 33/21 | 23/11 | 19/7 | 4/2 | 3/1 | 13/7 |
| M40 | 23/31 | 18/16 | 13/13 | 3/3 | 1/3 | 10/10 |
| M20 | 11/43 | 12/22 | 6/20 | 2/4 | 0/4 | 8/12 |
| M10 | 5/49 | 4/30 | 2/24 | 0/6 | 0/4 | 1/19 |

累積帯は重複する。以下もKEEP/DROP、Nは≥1:90 / ≥2:56 / ≥3:30 / ≥5:20。

| point | ≥1% (N90) | ≥2% (N56) | ≥3% (N30) | ≥5% (N20) |
|---|---|---|---|---|
| ALL_KEEP | 90/0 | 56/0 | 30/0 | 20/0 |
| CAL95 | 88/2 | 54/2 | 30/0 | 20/0 |
| M80 | 82/8 | 51/5 | 28/2 | 19/1 |
| M60 | 62/28 | 39/17 | 20/10 | 13/7 |
| M40 | 45/45 | 27/29 | 14/16 | 10/10 |
| M20 | 28/62 | 16/40 | 10/20 | 8/12 |
| M10 | 7/83 | 3/53 | 1/29 | 1/19 |

DROP compositionはDROP_COMPOSITION.csvへ、総DROP中の比率と各帯内DROP率を区別して保存した。

## 5. C08/C10/C11 全curve比較

各セルは PLUS KEEP / MINUS KEEP / ≥5% KEEP。共通N=144 / 172 / 20。各モデルの7固定pointを全保存し、結果後のthreshold変更や連続sweepは0。

| point | C08 P/M/≥5 | C10 P/M/≥5 | C11 P/M/≥5 |
|---|---|---|---|
| ALL_KEEP | 144 / 172 / 20 | 144 / 172 / 20 | 144 / 172 / 20 |
| CAL95 | 133 / 149 / 19 | 137 / 159 / 20 | 135 / 160 / 20 |
| M80 | 115 / 131 / 17 | 125 / 134 / 20 | 126 / 142 / 19 |
| M60 | 83 / 104 / 12 | 99 / 95 / 14 | 95 / 86 / 13 |
| M40 | 64 / 70 / 9 | 71 / 61 / 11 | 68 / 52 / 10 |
| M20 | 32 / 29 / 5 | 40 / 33 / 7 | 39 / 33 / 8 |
| M10 | 12 / 17 / 2 | 20 / 22 / 3 | 12 / 16 / 1 |

C11/M20はC10比：MINUS33→33、≥5 Winner7→8、累積≥1 Winner28→28、≥2 Winner16→16、≥3 Winner9→10、ALL PLUS40→39。全PLUS保持と大Winner保持のtrade-offを隠さない。M40はC10比MINUS61→52、ALL PLUS71→68、≥5 11→10。M60はMINUS95→86、ALL PLUS99→95、≥5 14→13。C11/CAL95とM80/M10にもtrade-offがあり、全curveで一律改善とは言えない。

同一ID paired change（C10→C11、union）。KD=KEEP→DROP、DK=DROP→KEEP。

| point | MINUS KD/DK | ≥5 Winner KD/DK |
|---|---|---|
| M60 | 28 / 19 | 2 / 1 |
| M40 | 19 / 10 | 2 / 1 |
| M20 | 8 / 8 | 0 / 1 |

## 6. Paretoとranking判定

C09を含む既存21候補 + C11の7候補 =28候補を全保持。元の全6排他的Winner帯によるstrict Pareto edgeは1件のまま：**C10_M60がC08_M60を支配**（PLUS99 vs83、MINUS95 vs104、≥5 Winner14 vs12）。C10の実改善Evidenceを維持する。C11にはこの強い定義で新たな支配edgeはなく、単一Champion未認定。

事前固定の「MINUS低い・ALL PLUSと累積≥1/2/3/5 Winner高い」Paretoは5 edges。この定義でC11_M60がC08_M60を支配し、C11_M80がC09_M80を支配する。これは全6排他的帯の支配とは別の判定であり、条件を後付けしていない。

C11でranking改善は**局所的に有り**：M20では同じMINUS KEEPで累積Winner KEEPが増えた。M40/M60ではMINUS削減とWinner損失のtrade-offで、C10全体の置換Evidenceには不足。

## 7. Causal QA / 独立監査

causal QA: 1600 Entry / 35,639 checks / mismatch0。future suffix delete/modify/reorder/duplicate、future payload不可読、Entry後H/L拒否、teacher/EXIT/MFE/MAE/R/Winner capability拒否、lunch/missing/early/flat/zero activity、phase ordering/partition/boundaries、C06/C10 aliasを確認。native11:30を含む422 Entryも保持。RAW prefix一致は同一hashのcacheと親C10の全1600 QAを継承し、新RAW scan0。

独立監査: 主集計/policy/builderをimportしない別実装で233,079 checks、最終mismatch0。全1600×107 new fields、ID/class/正確なFraction bucket、成熟CAL thresholdのorder statistic/nextafter、KEEP-DROP、paired IDs、累積、両Pareto、入力matrix、C11保存済みモデル645 CAL/DEV scoresのIEEE754完全一致を再構成。

失敗履歴は全保存。①fit前seal serializationのown-read whitelist漏れを保存処理だけ修正（feature rebuild0）。②post-seal集計で親C09 referenceが残ったため固定C08/C10/C11 paired一覧へ修正（model/score/threshold/field/bucket変更0）。③初回独立監査98 mismatchはPython3.12 compensated sumと逐次binary64加算順序の差だけ。検算側を順序通りの加算へ修正し、完全一致基準の緩和0。初回auditはprivate保存、公開digestはhashと件数のみ。fit retry0、モデル修正0。監査score replay累計1290 rows /8 units（2回×645、REPORT5010）。

## 8. Exposure / 範囲

全データはAdaptive Development。DEV_COMPARE322（known R316、UNKNOWN6）。teacher-blind prefix QA1600は既存58 sessions内で、REPORT501への新モデルscore・Winner評価0。Fresh0 / OOS0 / Protected0 / market provider0 / Capital0 / orders0 / production0 / main update0 / force push0 / Freeze変更0。第2・第3層へ進まない。残fit枠や別leaf/ensemble/seedは使用0。C12自動実行0。

## 9. 保存・readback

public: contract/spec/registry/QA/implementation/集計/hash/Pareto/report。private: 全1600 row features、native prefix cache、C11 input matrices、モデル、score、threshold、decision、exact return join、paired IDs、初回失敗記録。元C09/C10成果は変更せず親treeに残す。FINAL_EVIDENCE_MANIFEST記載のpublic本文とprivate archive partsをactual GETしてpath/bytes/SHA256/blobを照合する。最終成果保存HEADとreceipt publication HEADはREADBACK_RECEIPT.json / READBACK_RECEIPT_PUBLICATION.jsonで確認する。

## 10. 次の単一仮説

teacher-blind構造診断ではphase中央値45、最大213。6区間超は1556/1600=97.25%。直近6区間だけでは細かな価格反転によって前半区間が押し出される可能性がある。これは原因の確定ではない。

次の単一仮説：価格が極値から固定0.30%反転したときだけ新しい方向区間に切り替える、1つの事前固定ordered prefix表現なら、微小反転による直近6区間の押し出しを減らし、同一C10/HGB7でM40/M60の中・大Winner損失を抑えられるか。別途PRECOMMITと追加予算が必要。C12は起動しない。
