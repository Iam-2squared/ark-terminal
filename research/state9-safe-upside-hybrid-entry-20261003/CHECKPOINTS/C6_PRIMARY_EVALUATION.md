# 💾 C6_PRIMARY_EVALUATION

## 📌 saved_at_jst

"2026-10-03T10:23:03.789076+09:00"

## 📌 basis_head

"a584bfcede087940d2fadaea895eec9ac055abbc"

## 📌 previous_checkpoint_result_head

"a584bfcede087940d2fadaea895eec9ac055abbc"

## 📌 current_status

"SAFE_UPSIDE_ENTRY_NO_HIGH_PRECISION_CANDIDATE_C6_COMPLETE"

## 📌 completed_this_checkpoint

[
  "外側OOF65,312行/armを同一PrimaryでOpportunity-weighted PR/ROC/Brier/LogLoss評価",
  "IMMEDIATE/R1の3848fillをexact候補fill labelへjoinし新Primaryのみ評価。新baseline label作成0、旧Geometry/Capture集計再計算0",
  "各新arm2155Opportunity保持、全てNO_HIGH_CONFIDENCE_ENTRY、forced fallback0。空precision/MAEはUNKNOWN",
  "+1..5Winner固定分母・新armCapture・共通Opportunity paired比較・session/symbol集計を保存",
  "130249固定threshold点のtrain-side precision/coverage図、OOF識別図、safe-up fill図を作成"
]

## 📌 key_evidence

{
  "population_N": 2155,
  "sessions": 58,
  "symbols": 950,
  "OOF_rows": 65312,
  "evaluable_rows": 23457,
  "unknown_rows": 41855,
  "evaluable_opportunities": 1337,
  "H0_PR_AUC_AP": 0.2596316159037758,
  "H1_PR_AUC_AP": 0.258627306109666,
  "H2_PR_AUC_AP": 0.25913225870683954,
  "H0_ROC_AUC": 0.580380463668373,
  "H1_ROC_AUC": 0.5803821280884096,
  "H2_ROC_AUC": 0.5797498712103308,
  "feasible_operating_points": 0,
  "new_baseline_labels": 0,
  "baseline_fill_label_reuse": 3848,
  "new_fits_this_checkpoint": 0
}

## 📌 blockers

[
  "90/85/80 operating point全てsupport/safety未達。Fresh Validationへ自動進行しない",
  "unknown41,855/65,312行、研究bar-end availability仮定、live PIT受信時刻未証明",
  "価格を含むrow-levelEvidenceは非公開保持。GitHub公開は集計/hash/receipt/sourceのみ"
]

## 📌 current_direction

"成立しなかったEntryを成立扱いしない。Stateの微小AUC差を有効signal/確率として昇格しない。Independent audit後に最終結論を確定"

## 📌 next_step

"C7 原本・OOF・独立算術によるcutoff/State identity/fill/barrier/split/weight/threshold/Entry/Capture/feature separation監査"

## 📌 frozen_boundaries

[
  "Primary+2/-1、secondary15組選択0",
  "model/feature/split/threshold条件変更0",
  "model fit追加0、bootstrap0、provider0",
  "未知→0/negative補完禁止",
  "no forced fallback",
  "State9/V6結論維持",
  "LONG-only cash-equity / safety flags false"
]

## 📌 exposure_and_budget

{
  "reads": {
    "baseline_saved_fill_label_joins": 3848,
    "OOF_rows_per_family": 65312
  },
  "writes": {
    "public_scope": "aggregate/hash/receipt/source only"
  },
  "fit": 60,
  "new_fit_this_checkpoint": 0,
  "threshold_selections": 15,
  "new_threshold_selections_this_checkpoint": 0,
  "provider_requests": 0,
  "protected_opens": 0,
  "holdout_opens": 0,
  "validation_new_opens": 0,
  "OOS_opens": 0,
  "prospective_opens": 0,
  "bootstrap": 0,
  "replay": 0,
  "new_candidate_label_passes": 1,
  "new_baseline_label_passes": 0,
  "orders": 0,
  "main_merge": 0
}

Result HEADは保存後のGitHub commitが正本。未来のSHAは本文に記録しない。
