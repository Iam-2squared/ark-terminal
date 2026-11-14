# 💾 C3_FEATURE_FAMILY_FREEZE

## 📌 saved_at_jst

"2026-10-03T09:38:10.142222+09:00"

## 📌 basis_head

"1711070f60c089ed7b7296bcb2e080e0da0efed0"

## 📌 previous_checkpoint_result_head

"1711070f60c089ed7b7296bcb2e080e0da0efed0"

## 📌 current_status

"C3_H0_H1_H2_FEATURE_FREEZE_PASS"

## 📌 completed_this_checkpoint

[
  "H0 480 causal列を再利用join。legacy STATE/SIX 86列完全除外",
  "133 saved matricesをGit blob/凍結SHAと照合、149900行identity/cutoff一致",
  "H1 最終RC2 current numeric33/categorical11、H2有限8historyをfreeze",
  "train-only imputation/standardization/one-hot、固定LR、60fit予定/72hardcapをfreeze",
  "0byte local復元中断incidentを凍結hash一致原本で解決しreceipt保存"
]

## 📌 key_evidence

{
  "H0_features": 480,
  "H1_numeric_added": 33,
  "H1_categorical_added": 11,
  "H2_history_added": 8,
  "source_matrices": 133,
  "rows": 149900,
  "source_identity_checks": 149900,
  "legacy_columns_excluded": 86,
  "future_cutoff_violations": 0,
  "source_mismatches_remaining": 0,
  "H0_matrix_sha256": "3c0fa38d61da5848955c24f55abea7dc88f7040338713f6a8214f7ac5eefef7c",
  "new_labels": 0,
  "new_fits": 0
}

## 📌 blockers

[
  "bar-end available研究仮定と既存Selector metadataのsource caveatを保持",
  "source不足はmissing indicator、semantic formal-nullは別category"
]

## 📌 current_direction

"同じmodel/split/targetでState追加だけのincremental valueを測定"

## 📌 next_step

"一回だけfirst-passage labelsを作成、C4記述censusとlabel/cutoff integrity確認"

## 📌 frozen_boundaries

[
  "480+33/11+8以外feature追加0",
  "train-only前処理",
  "V6 scores/prob/rank使用0",
  "RC2意味変更0",
  "fixed LR L2 C1 liblinear maxiter1000",
  "fit72hardcap",
  "future/evaluator features禁止",
  "provider/protected/trades/main_merge0"
]

## 📌 exposure_and_budget

{
  "reads": {
    "saved_feature_matrices": 133,
    "feature_source_row_identity_checks": 149900
  },
  "writes": {
    "checkpoint_commits_before_save": 6
  },
  "fit": 0,
  "threshold_selections": 0,
  "provider_requests": 0,
  "protected_opens": 0,
  "holdout_opens": 0,
  "validation_new_opens": 0,
  "OOS_opens": 0,
  "prospective_opens": 0,
  "bootstrap": 0,
  "replay": 0,
  "new_labels": 0,
  "orders": 0,
  "main_merge": 0
}

Result HEADは保存後のGitHub commitが正本。未来のSHAは本文に記録しない。
