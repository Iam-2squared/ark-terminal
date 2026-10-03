# 💾 C4_FIRST_PASSAGE_CENSUS

## 📌 saved_at_jst

"2026-10-03T10:14:11.119400+09:00"

## 📌 basis_head

"ef2e2429f784e05523251a984150e979f21524ea"

## 📌 previous_checkpoint_result_head

"ef2e2429f784e05523251a984150e979f21524ea"

## 📌 current_status

"C4_CENSUS_AND_INDEPENDENT_LABEL_INTEGRITY_PASS"

## 📌 completed_this_checkpoint

[
  "一回だけ15組first-passage label作成。149900候補行を保持",
  "現在2155 Opportunity/65312行/58session State/path/dwell/delay/TOD/未来bucket census保存",
  "全149900行を原本から独立Decimal経路でfill/Primary/firsttouch/delay照合し不一致0",
  "1,417,728 secondary-level整合チェックPASS",
  "図3点作成、manualStateRules0、Primary変更0",
  "公開checkpointは集計・hash・receipt・sourceに限定。fill価格を含む行単位labelは非公開保持し、拒否された全directory pushは再試行しない"
]

## 📌 key_evidence

{
  "current_rows": 65312,
  "evaluable_rows": 23457,
  "UP_FIRST": 5738,
  "DOWN_FIRST": 16212,
  "NEITHER": 1507,
  "ORDER_UNKNOWN": 73,
  "DATA_UNAVAILABLE": 41782,
  "unknown_rows": 41855,
  "evaluable_UP_FIRST_rate": 0.2446178113143198,
  "unique_fill_anchor_checks": 84776,
  "independent_label_mismatch": 0,
  "independent_delay_mismatch": 0,
  "label_passes": 1,
  "new_fits": 0
}

## 📌 blockers

[
  "OHLC intrabar順序不明/未観測slotは不明として保持。不明をnegative/0へ補完しない",
  "bar-end availability研究仮定",
  "行単位fill価格の公開GitHub保存は安全審査で保留。実験は公開を伴わない処理として継続し、private成果物とhashで復旧可能性を維持"
]

## 📌 current_direction

"記述State差から手作業ruleを作らず、凍結H0/H1/H2同条件60fitの比較へ"

## 📌 next_step

"C5固定LR finite experiment、train-side innerOOF threshold/family selection、NO_ENTRY許可"

## 📌 frozen_boundaries

[
  "Primary +2/-1固定",
  "新label作成pass1のみ",
  "旧Entry評価再計算0",
  "manualState rule0",
  "newprovider0",
  "train/test chronological/purge",
  "maxmodelFit72",
  "evaluator未来fielddecision禁止"
]

## 📌 exposure_and_budget

{
  "reads": {
    "independent_label_rows": 149900,
    "independent_fill_anchors": 84776,
    "secondary_integrity_checks": 1417728
  },
  "writes": {
    "checkpoint_commits_before_save": 7,
    "publication_scope": "explicit metadata/aggregate/source allowlist; no new row-level prices"
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
  "new_label_passes": 1,
  "new_label_rows": 149900,
  "orders": 0,
  "main_merge": 0
}

Result HEADは保存後のGitHub commitが正本。未来のSHAは本文に記録しない。
