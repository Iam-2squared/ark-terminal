# Phase57 Milestone Guard-first EXIT — Controlling Handoff

保存日時：2026-09-29 JST  
Repo：`Iam-2squared/ark-terminal`  
Branch：`research/phase57-long-only-cash-equity`  
PR：#587 Open / Draft / unmerged

## 🧭 結論

今回のGuard-first cycleは **`GUARD_FEASIBILITY_UNMEASURABLE / NO_SELECTION`** で正式Close。`selected=null`、`productionReady=false`。研究の失敗を隠さず、Guardのfloor・ladder・2-checkpoint確認数を変更しない。

| 独立した判定 | 結果 |
|---|---|
| Guard | ≥5 Winnerのexact順序57/301=18.9%、≥10 Winnerは30/126=23.8%。事前固定80%に未達 |
| 既知例のfloor先行 | ≥5は49/57、≥10は30/30。未知例への外挿を禁止 |
| Potential | ≥5/≥10のPowerは99.6%/95.4%でPASS。共通の凍結Entry時点feature schemaが一意でなく、skill未測定、fit 0 |
| Survival | exact 30 active-minute endpoint 891/1,646=54.1%。必要70%に未達、fit 0 |
| Guard候補・Replay | Guard Gateで停止。candidate 0、Integrated Replay 0/22 |
| R54 / WPSD | 従来の訂正済みCLOSED / PHASE0_NO_GOを維持。救済・再探索なし |

## 📌 固定Upstream / lineage

Selector Frozen、Entry IMMEDIATE / ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF（Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`）、Capital saved v3 B、Control R50_A_LIFECYCLE。¥1,000,000・100株単位・MAX3・現物LONG-only。R45 source artifact `10909618948`、R54 replay `10964100200`、R34 audit `10964250835` とraw pathはPrecommit pinに一致。

Precommit `CYCLE_PRECOMMIT.json` SHA-256：`1b7bc9d41333958e3bb1cc5845d044427f107ebf6824f6a8975ab37eaa58293d`。結果を見た後にGateや閾値を変更していない。

## 🧪 Evidence / 検証

- `START_AUDIT.json` → `CYCLE_PRECOMMIT.json` → `PHASE0_A.json` → `PHASE0_B.json` / per-Entry compressed rows → `GUARD_FEASIBILITY.json` → `POTENTIAL_RESULT.json` / `SURVIVAL_RESULT.json` → `INDEPENDENT_AUDIT.json` → `FINAL_CLOSURE.json` のappend-only順。
- 独立再計算：milestone reach 8,070件、遷移8,070件、ALERT 1,646件一致。focused unit tests 5/5 PASS。
- 6図と数値表は [`REPORT-ja.md`](REPORT-ja.md)。図7–10は候補・OOF・equityがないため作成しない。
- 専用再生成CI：`Phase57 Milestone Guard Phase 0`。結果は `FINAL_CLOSURE.json` のrun/statusを確認。

## 🔒 Exposure / Safety

| 項目 | このcycle |
|---|---:|
| 新規estimator fits / Integrated Replay | 0 / 0 |
| 新規provider requests / Protected・Fresh・Validation・OOS・Prospective opens | 0 / 0 |
| Orders / main merges | 0 / 0 |

Safety9は全false。R54のauction/mark不足2 Entryは従来の記録であり、新Guard候補のCapital測定ではない。新候補のFinal Equity / MaxDD / 月間¥2M gapは未測定・unmeasurable。

## 🚧 次の境界

このcycleのGuard-only、Guard+Survival、Potential classifierは未実装・未fit。Phase 0 NO-GOのあとに+4/+7.5%等のladder、別floor、1/3/5確認回数を試さない。新しいEXIT研究は別の結果閲覧前Precommitから開始し、既存Developmentの欠測・Control保有区間・同一bar順序の可観測性を先に評価する。Selector / Entry / Capitalは固定し、Protected/Fresh/OOSを開けず、provider・売買・main mergeを行わない。
