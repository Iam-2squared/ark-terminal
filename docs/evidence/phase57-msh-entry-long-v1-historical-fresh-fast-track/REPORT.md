# Historical Fresh Validation Fast Track — INCONCLUSIVE before measurement

Verdict: `MSH_ENTRY_LONG_V1_VALIDATION_INCONCLUSIVE`

今回のFast Track指示を適用し、Entry Validation30だけを対象にした。残り165日のexact dates、未来G25、過去の195日一括取得Gateを停止理由にしていない。Global Budget/Candidate/model/scaler/Selector/Fit/Development SHAは一致し変更なし。

停止理由は **過去Fresh30営業日を、現在のJ-Quants分足API範囲と既存保護条件で合理的に確保できないこと**。Candidateの性能FAILではなく、測定前のINCONCLUSIVE。

## 取得可能範囲

公式分足APIは過去2年。Lightの日足5年とは異なる。TSEのみ、1分OHLCVを取得し既存のcompleted5m semanticsで集約する。分足アドオンは60requests/minute。認証APIへは未接続で、account-specific cutoffは未確認。今回の停止はAPI認証失敗ではない。

- https://jpx-jquants.com/en/spec/eq-bars-minute
- https://jpx-jquants.com/en/spec/data-spec
- https://jpx-jquants.com/ja/spec/rate-limits

## 日付だけで確認した結論

| Period | Existing metadata restriction |
|---|---|
| 2024-09-17〜2026-01-07 | 使用済み、恒久除外、purge |
| 2026-01-08〜2026-06-11 | Protected103の明示的な日付範囲 |
| 2026-06-12〜2026-09-09 | outcome-exposed |
| 2026-09-10〜2026-09-15 | 既存SEALED予約 |

通常の2年範囲2024-09-16〜2026-09-15で、すべての平日を営業日候補として過大に数えても、上記を除いた日付は27平日、最長連続4平日。祝日を除く前の上限なので30営業日は成立しない。

取得境界の不確実性に有利な感度確認として、2024-09-01〜2026-09-16まで広げても最長6平日。未登録日をFreshと認定したわけではない。UNKNOWN101を日付へ推測対応せず、追加のUNKNOWN解決監査も行っていない。Protected envelopeはimmutable GitHub metadataのfirst/lastだけで確認。

公式calendarの代用品として平日をallocationしていない。この計算は不可能性を確認する上限評価だけ。新30 sessionsを選定・Freezeしていない。

## 実行結果

- Offline metadata tests: 29 total / 29 PASS / 0 FAIL / 0 SKIP。
- 市場価格取得0、Candidate/Validation prediction0、model/scaler fit0。
- OOS/EXIT outcome/SHORT evaluation0。
- 新allocation、予約解除、SEALED開封、UNKNOWN昇格すべて0。
- Safety9項目すべてfalse。
- 新raw/normalized/Dataset SHAは未発行。性能項目はNOT_MEASUREDであり0ではない。
- 本turnの許可があってもFreshness条件自体は満たせない。追加承認不足や将来日付を理由に止めたのではない。

## 次の具体的判断

現在の条件をそのまま再実行してもFresh30は作れない。次は、特定のProtected historical予約を明示的に見直すか、現在の分足APIの2年範囲外を利用できるJ-Quantsのsource/cacheがあるか、データ確保方針を決める必要がある。どちらも今回は実行していない。既使用データは予約解除してもFreshへ戻らない。

モデル・threshold・対象sessionを勝手に変更せずSTOP。全63項目は`final-report-63-items.json`。
