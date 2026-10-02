# 🧩 NEXT HYBRID ENTRY SPEC — 草案

**status: PROPOSED_NOT_AUTHORIZED**  
Document ID: WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1  
generated_at_jst: 2026-10-02T23:59:48.213981+09:00  
basis_head: 5495e0e6f67eca9e533127ae7f567607ebedb407  
prerequisite: ENTRY_GEOMETRY_BASELINE_AUDIT_PASS（2,155 Opportunities / 58 sessions / 950 symbols / mismatch=0）

## 🎯 研究対象と根拠

目的はLowとの完全一致ではなく、causal情報から、Entry後のupsideを数%残しながらdownsideとのバランスを取ること。R1の残存upside中央値1.672%、MAE中央値−1.606%、+5% Capture70.098%。共通known1,868件ではIMMEDIATE比でremaining平均−0.255 pp、MAE平均+0.223 pp。時間を使ってdownsideだけ浅く見せる候補を自動採用しない。

global Low≤Entry cohortでLow距離とupsideの単調減少を確認できない。未来global Lowを待つ設計へ戻らない。future Winner帯ならR1の残存upsideは3–5%帯中央値3.134%、5–10%帯5.576%あるが、Winner membershipをdecision featureとして使えない。

## 🧊 引き継ぐ凍結境界

IMMEDIATE / R1、canonical Opportunity identity、Selector PIT price、saved next-open+5bps価格basis、session calendar、State9 RC2 / Path / 既存target定義を維持。V6は終了しSTATE_R2_SIGNAL_NOT_REPLICATED / calibration FAILのまま。R2 probabilityまたは未検証rankをEntry thresholdに利用しない。State9はcausal categorical feature family候補であり、今回State-only判断や新fitはない。

今回の2,155母集団はoutcome-exposed Development。ここを新OOSとして扱わない。元の76 session splitとは別lineageなので38/19/19を流用しない。新しいpartition・学習/選択/評価の境界は別Precommitで固定する。

## 📏 評価target / metric案

| 役割 | 草案 | 次Precommitで固定する条件 |
| --- | --- | --- |
| primary upside | Entryよりstrictに後のbarのsession-end maximum High return（clipなし） | 観測window・bar timestamp・full-session admissionをbaselineと照合 |
| primary downside | canonical saved session-end MAE（signed） | late Entryの短い露出時間をtime-of-day / remaining active timeで分離 |
| joint target候補 | remaining upside≥u かつ MAE≥−d | uは既存1/2/3/5%の有限候補。数%という目的には2%をprimary候補とするが**未承認**。dは未選択で、業務許容値を結果閲覧前に固定 |
| secondary upside | upside retention、Selector Winner 1/2/3/5%のcanonical Capture / strict-later sensitivity | 正のSelector MFEのみratio。小分母と100超/負値を保持 |
| secondary downside | 既存30/60m MAEとstatus / missingness | 元のhorizon clock・COMPLETE/PARTIAL/CENSORED semanticsを監査し、未認証なら使用しない |
| missed analysis | NO_ENTRY / entered below / OUTCOME_UNKNOWN、global High≤Entryのchronology proxy | UNKNOWNをmissにしない。時刻proxyを因果理由へ昇格しない |
| timing | active delay、Entry後Highまでのactive残り時間、JST time-of-day | 昼休みを除外。将来High時刻は評価専用 |
| descriptive controls | 共通Opportunity / 共通known比較、固定bucket、session/symbol concentration | fill率・unknown率・母集団の変化も評価 |

今のend-of-session Geometryと、将来の固定horizon比較は同一ではない。固定horizonが必要なら、別Precommitでclockとlabel sourceを定めてから実装可否を判断し、現在のState / Path / targetを上書きしない。許容downside d、fit数、モデルclass、選択回数、split、promotion Gateは本草案では未承認。

## 🧬 最低限のcausal featureと有限な追加順序

| 段階 | family | 必要性 / 可用性 |
| --- | --- | --- |
| A | price structure / turning point | decision cutoffまでの価格変化、当時までのrunning High/Lowからの距離、少数の固定recent return / higher-low確認。global future Low/Highはfeature禁止 |
| A | Selector information | exact PIT Selector price、当時保存のscore/rank等。未来Selector MFE / Winnerはfeature禁止。score/rankを確率扱いしない |
| A | active delay / time-of-day | upsideとdownsideに露出時間差があるため最低限のcontrol。時計由来で新provider不要 |
| B | State9 RC2 | 正確なsymbol/session/as-of/sourceHash/価格basisの認証後に1family追加。旧State-v3置換は禁止。未認証ならAだけを評価する契約を別途承認 |
| C | volume / liquidity | saved causal sourceのcoverage、staleness、spread/turnover proxy、fill retryの欠測を先に固定。その後1family追加で価値を比較 |
| 後続 | relative strength / market・sector context / volatility | sourceと時間契約を認証し、A/B/CのEvidenceから必要性を決める。一度に全部fitしない |

過去running Lowを使う場合も、それがsessionのglobal Lowになるかは不明。decision featureは当時の履歴だけ、teacher/evaluatorのfuture Geometryは別schemaとする。as-of以後のbar OHLC、global extrema時刻、Selector Winner、capture label、Entry MAE/MFE、現在報告のbucketはdecision inputへ流さない。

## 🧪 次の有限Precommitに必要な項目

1. source/identity/price/horizon/clockの契約と各feature cutoffをhash固定し、State9 RC2の正確なsaved joinを可用性監査する。
2. primary target、downside許容値、training/selection/evaluation split、finite fit budgetと候補順序を、次の結果閲覧前に固定する。
3. 既存armと同じ全Opportunity分母を保持し、fill / no-entry / unknown・時間帯・Winner帯・paired Geometryを併記する。
4. Aから開始し、追加familyは1つずつ。State9-only probability/rank thresholdや全family一括fitを行わない。
5. 新decision候補のcausal auditと独立算術監査、session/symbol依存、missingness、capture/downside tradeoffを確認する。新OOS/Protected openやprovider取得の必要性が出たら、そのPrecommitの範囲外へ進まない。

## 🛑 Authorization / 実績

**HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY**。これはmodel完成・fit承認・自動promotionではない。今回の新fit / threshold search / Replay / provider / bootstrap / Protected・Holdout・Validation新open・OOS・Prospective open / orders / paper / live / main mergeはすべて0。全Safety flag=false、LONG-only / cash-equity-only。別の有限Precommitで初めてfit可否を判断する。
