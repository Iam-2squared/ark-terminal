# FINAL HANDOFF — FIRST ENTRY ONLY

Actual saved_at_jst: 2026-10-03T12:47:38.973111+09:00

Actual basis_head: `340f7f1aa30cf9a2c55f8bd401cbb461b24714f0`

Status: BLOCKED_SPLIT_OR_LINEAGE_MISMATCH

teacher calendarの実装ミスを修正したが、20 head fitsのtraining eligibilityが一致しない。所定designの修復は合計50 fitsでhard cap36を超えるため、追加fit0でintegrity STOP。品質確定・candidate Freeze・State正式採用・EXIT研究への移行は行わず、生成済みFIRST ENTRYと修正Evaluatorを診断用に保持する。

QUALITY: **P0_Q80** / BALANCED: **P1_Q70** / same: False

全4 policyのFIRST_ENTRY filesは各2,155 watch×P0/P1を含む。no-entryも残している。row-level/private artifactsは別deliverableのPrivate Evidence packageへ保存し、GitHubにはaggregate、contract、再現code、hash receiptを保存する。

candidate名はoriginal modelのOOF recordsを修正Evaluatorで測った診断rankingだけ。20 head fitsはcorrected teacherとtraining eligibilityが一致せず、candidate Freeze・promotion・State正式採用は不可。productionReady=false。Fresh Validation unopened。前SAFE_UPSIDE WorkはFAILのまま閉じて保持。

再現は保存sourceと固定contractから行える。完了済みFIT_LEDGERとmodelsを使えばaudit fit=0。closed 1mの実際のarrival時刻はUNKNOWNでbar-end assumption。欠測Pathはunknown。

今回の停止点はFIRST ENTRYの生成・修正Evaluatorによる診断評価とintegrity STOP。EXIT・R50・Re-entry・Capital・Portfolioを実行していない。このWorkからEXIT研究へは渡さない。corrected teacherで所定designを修復するには20追加fits、通算50 fitsが必要でhard cap36を超えるため、追加fit0で終了した。

Exposure: provider0 / Protected0 / Fresh0 / Validation0 / OOS0 / Prospective0 / EXIT Replay0 / Re-entry0 / Capital0 / orders0 / main merge0 / fits30 of cap36 / searches0 / audit fits0。

CHECKPOINTS/FINAL.jsonのbasis_headはcommit前の実在HEAD。commit後のactual GET result HEADはLOCAL_GET_RECEIPTS/FINAL.jsonとuser-facing final receiptへ保存する。未来commit SHAは記載しない。
