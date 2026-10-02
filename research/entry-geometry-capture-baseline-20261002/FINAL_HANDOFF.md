# 📐 Ark Terminal — Entry Geometry / Capture Baseline

- **現在status:** ENTRY_GEOMETRY_BASELINE_AUDIT_PASS + HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY
- **latest HEAD（C6作業開始時のGitHub GET）:** `5495e0e6f67eca9e533127ae7f567607ebedb407`
- **JST（この報告生成時の実時刻）:** 2026-10-02T23:59:48.213981+09:00
- **完了範囲:** C1 source freeze、C2 metric freeze、C3 saved join、C4 13表枠・7図、C5 独立監査、C6 解釈・次仕様草案。
- **次の方針:** 別の有限PrecommitでHybrid Entryのfit可否を判断する。草案statusは **PROPOSED_NOT_AUTHORIZED**。今回のfitは0。

Document ID: `WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1`

C6保存結果のHEADはGitHub commit自体が正本であり、本文で未来のSHAを予測しない。納品receiptと最終応答に保存後GETで確認したresult HEADを記録する。

## 📦 正本と再開地点

SOURCE_MANIFEST.json / POPULATION_FREEZE.json / JOIN_KEY_CONTRACT.json / METRIC_CONTRACT.jsonがC1/C2 authority。GEOMETRY_ROWS.jsonl.gzとJOINED_GEOMETRY_ROWS.jsonl.gzは同一内容のalias。JOIN_AUDIT.json / MISSINGNESS.json / C3_RECEIPT.jsonがjoin証拠。GEOMETRY_SUMMARY.json / MISS_WINNER_ANALYSIS.json / TIME_GEOMETRY.json / CONCENTRATION.json / FIGURE_INDEX.json / FIGURES/が集計証拠。STATE9_GEOMETRY_NOT_AVAILABLE.jsonがRC2不使用receipt。INDEPENDENT_AUDIT.jsonが原本別経路監査。

REPORT-ja.mdとREPORT-ja.html、CONTINUOUS_STATISTICS.csvで結果を確認できる。NEXT_HYBRID_ENTRY_SPEC_DRAFT.mdはPROPOSED_NOT_AUTHORIZED。MANIFEST.jsonは各成果物のSHA-256とGit blob identityを記録する。Git commit自身をresult HEAD正本とし、commit前にSHAを捏造しない。

## 🔄 再実行してよいもの

CODE/aggregate_geometry.pyは保存join rowsだけを読むdeterministic集計・plot。CODE/independent_audit.pyは保存原本から別経路で算術検証する。旧Entry/Selector/Stateのrunner・models.pkl・provider・Replayを実行しない。原本hash検証に必要な保存ZIP authorityのpathはSOURCE_MANIFEST.jsonにある。納品bundleのdocs/evidence/（PRIMARY_SOURCES_INDEX.jsonで列挙）にはcanonical Opportunity / IMMEDIATE / saved raw / legacy State / manifestsのexact bytesがあり、FROZEN_ARTIFACT_MEMBERS/にはR1 Entry原本とscorecard原本のlossless wrapperがある。artifact ZIP全体の再hashにはC1で認証した元の保存ZIPが必要。modelは納品bundleに含めない。保存sourceのabsolute pathは元work時点のreceiptであり、別workspaceで全監査を再実行する際は原本archiveの配置対応を確認する。

## 🧭 残る課題

State9最終RC2 exact join未認証、future-end exposure時間差のcontrol、downside許容値、次の有限fit budget/splitは別Precommit課題。現在のbaselineに未解決の算術・join blockerはない。State9欠測を旧State-v3で埋めない。V6を再開せず、R2 probability/rankをEntryに昇格しない。

## 🛡️ 実行境界

new_entry_model_fits=state_model_fits=exit_model_fits=threshold_searches=new_policy_replays=provider_requests=bootstrap=0。Protected/Holdout/Validation_new/OOS/Prospective open=0、orders/paper/live/main merge=0。全Safety flag=false。LONG-only / cash-equity-only。force pushなし。

## 💾 保存済みcheckpoint

| checkpoint | saved_at_jst | basis HEAD | result HEAD |
| --- | --- | --- | --- |
| C1 | 2026-10-02T23:26:45.272585+09:00 | df5737a93345a46850d4b5a52b373d0bc5f233d6 | 08c914a65f5938bd87c407ecd431062ebcc43a78 |
| C2 | 2026-10-02T23:29:32.007394+09:00 | 08c914a65f5938bd87c407ecd431062ebcc43a78 | 08b99052f37db12a7ee0ac956967a5b3e5899a9e |
| C3 | 2026-10-02T23:37:34.617637+09:00 | 08b99052f37db12a7ee0ac956967a5b3e5899a9e | 987c0be273eb41a2a52b36d7ede627427921d2fd |
| C4 | 2026-10-02T23:42:50.240460+09:00 | 987c0be273eb41a2a52b36d7ede627427921d2fd | 895b7553fe24bb1e241ed217b78ba0c2439379ef |
| C5 | 2026-10-02T23:48:49.222400+09:00 | 895b7553fe24bb1e241ed217b78ba0c2439379ef | 5495e0e6f67eca9e533127ae7f567607ebedb407 |

C6 result HEADは保存後GitHub GETで確認する。FINAL_SAVED_RECEIPT.json（納品bundle）と最終応答がその実際のcommitを参照する。次の作業もbranch latestをread-only GETしてから始める。
