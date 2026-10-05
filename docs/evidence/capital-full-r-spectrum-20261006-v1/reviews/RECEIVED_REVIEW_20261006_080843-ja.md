# 📊 全Entry R診断 — 結果受領・次方針
実時計JST: 2026-10-06T08:08:43+09:00
basis HEAD: a34d240347c65407fb99eea74bbc783eab903085
basis tree: 3b005bb51ba82775c43c54b1ee99145f09328f32
状態: SOURCE_REVIEW_COMPLETE / R_SPECTRUM_INCONCLUSIVE維持 / 新policy未選定

## 原本確認
受領PRIVATE ZIPのCRC不一致0、manifestの102/102ファイルでサイズ・SHA256一致。
ZIP SHA256: df706bb19675a24f2cd2494a2b30d65b2e2718c3dbb10003f3e58ba3fd290c1c
REPORTのGit blob SHA1 176824ba82de029027e8321bb4629897aa9307c2はGitHub actual GETと一致。
今回の作業は保存CSVの照合・表示用合算・報告の解釈。82100項目の元独立監査は再実行していない。

## 全Entryが主分析
U5/U10は補助。全1039 EntryのうちR known1016、unknown23を維持。
以下は排他的なreturn帯。上端は含まない。旧V5 38 selected-session chainの購入結果と結合した表であり、新RESET20成績ではない。
全候補のRは固定約定・費用契約の単体referenceであり、全候補を実口座で購入した意味ではない。

| R帯 | 全known | rank-pass | V5購入 | rank-pass内未購入 |
|---|---:|---:|---:|---:|
| R<0% | 554 | 273 | 82 | 191 |
| 0%<=R<1% | 191 | 83 | 21 | 62 |
| 1%<=R<2% | 113 | 51 | 11 | 40 |
| 2%<=R<3% | 49 | 27 | 7 | 20 |
| 3%<=R<4% | 38 | 19 | 6 | 13 |
| 4%<=R<5% | 16 | 5 | 4 | 1 |
| 5%<=R<10% | 30 | 18 | 8 | 10 |
| R>=10% | 25 | 16 | 11 | 5 |

+1%以上+5%未満は216件、rank-pass102件、購入28件、未購入188件。
未購入はrank/admission114、Reserve37、MAX3 34、cash/lot3。
購入分のPnLは+228910.25円。未購入は同時に回収可能な件数・数量・利益の上限ではない。

## 判断の修正
以前の会話で「R5 AUC約0.69があるため、主に数量変換を直せばよい」とした説明は強すぎた。
pP原向きAUROCはR1 0.559286、R3 0.582301、R5 0.691552に対し、RN3 0.677716、RN5 0.741748、RN10 0.822863。
高scoreは正負双方のtailを上位化する。高Rの順位情報と、損失を差し引いて増額する経済価値は同一ではない。
これは全てのcausal情報が無効という証明でもない。

## 追加lot上限の扱い
元REPORTの唯一の草案は「初回BUYの100株を超える追加lotへの集中上限」で、上限値・式は未固定、実装未承認。
草案を採用方針や成功見込みへ昇格しない。
実約定の100株超部分は正群+721721.30円、負群-441768.05円、差引+279953.25円。
追加部分の損失だけを見て削ると、同じ部分の利益を落とし得る。この差引は会計分解であって新capの最終資産ではない。
数量を減らして100株以上を残す操作はcashだけを空け、slotを空けない。
現行Rank/Reserveを維持する数量capで未購入188件をそのまま回収できるとは言わない。

## 次方針の提案（本レビューで未実行・別Work要）
全R分類やAUCをもう一度作らない。既存の固定score区分・R原値・資金台帳を使い、
「購入前の利用可能情報が、正側利益と負側損失を合算した費用後の純損益を区別できるか」を次の判断点とする。
既に同じ集計がある場合は再利用し、不足箇所だけを対象とする。
単体return平均、資金加重return、portfolio wealthは別の量として扱う。
将来の判断へ使う参照は、その時点以前に成熟したoutcomeと保存OOF lineageだけに限定する。
全期間の平均から新しいcutoffや上限を選ばない。
純損益の仮説と、現行制約下で実数量を出せるcashの受け手が具体化した場合だけ、別途1機構の有限実験を検討する。
根拠不足のまま一律上限や高pP集中のV5.2を急造しない。

## 現在地・禁止事項
V5 baseline維持、V5.1不採用維持、R_SPECTRUM_INCONCLUSIVE維持、V5.2なし。
21 RESET20予定窓のうち9完了・12 coverage不明を維持。7/11・7/14の調査や補完は今回なし。
Selector/Entry/EXIT変更0、新fit0、新Replay0、新candidate0、provider0、protected開封0、注文0、main merge0、force push0、Claude0。
公開するのは集約値・解釈・次方針のみ。private identity/銘柄別台帳は公開しない。
productionReady=false、transmitted=false。今回の受領確認は資産改善の主張ではない。

## 参照（すべてbasis HEAD）
- docs/evidence/capital-full-r-spectrum-20261006-v1/REPORT-ja.md
- 同 R_FULL_CENSUS.csv / V5_R_CAPITAL_FLOW.csv / V5_R_MISS_REASONS.csv
- 同 SCORE_R_SPECTRUM.csv / SCORE_R_FIXED_BUCKETS.csv
- 同 ACTUAL_LOT_TRANCHE_FLOW.json / NEXT_CAPITAL_DECISION.md / CURRENT_STATE.json
