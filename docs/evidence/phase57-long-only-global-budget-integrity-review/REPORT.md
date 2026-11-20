Phase57 LONG-only Independent Global Data Budget Integrity Review — 2026-09-16 JST

**PHASE57_LONG_ONLY_GLOBAL_DATA_BUDGET_FROZEN**

Integrity Verdict: **A — NON_MATERIAL_OUTCOME_DISPLAY_INCIDENT**。

前回のDevelopment class別件数表示は削除・隠蔽せず保存する。監査した予算計算経路には当該fieldの参照がなく、Outcome fieldを供給しない元builder replayで、前回contract全体がbyte単位で一致した。別実装でもsession/event予算、共有控除、buffer、取得量推定を再計算し、一致を確認した。したがって完成済み予算を一切変更せず正式Freezeする。

このreviewの「独立」は、別の計算実装・counterfactual input・出典照合を指す。同じassistantによる監査であり、外部の独立人間reviewerや心理的影響の観測を主張しない。非影響判定の対象は、証拠付きの数値由来と再現可能なbudget data flowである。

Frozen Contract SHA-256:
`b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f`

契約: `predict/research/phase57-long-only-global-data-budget-v1.json`。
SHAは改行を含むfile bytesに対するSHA-256で、自己参照を避けて [freeze-manifest.json](freeze-manifest.json) に保存。

Repo `Iam-2squared/ark-terminal`、branch `research/phase57-long-only-cash-equity`、PR #587。開始時remote head `b7e9e54350d1c008a11bace444ab6f6e14065b2a`、main `b7801ce2c13772cbc3f5b51506819c119fe868ea` を再確認。公開headとそのCIは最終応答・GitHub commit checksを参照。mainへmergeしない。

Candidate / final model / final scaler / Selector payload / Fit Contract / Development Evidence / Previous Global AuditのSHAを再確認した。Previous Global Auditは `7832848941d42fa5878591d5f4475ee3af296da25a7911c0cb51741d4082207f`。Ridge参照SHAも既存Frozen payloadで一致し、外部raw artifactの再取得はしない。元Frozen artifact・台帳・前回報告を変更しない。

Incidentのexact sourceは `predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json#/trainingIdentity/classCounts`。過去のcommandは `json.load` 後に `print(json.dumps(c['trainingIdentity'], indent=2))` として親objectを表示したもので、同object内のclass countsも表示した。過去tool output chunkは `ffa0b9`。前回 `audit-incident.json` と `REPORT.md` に記録済み。数値そのものは今回のinput/reportへ再掲しない。

表示commandはbudget inputを作成・変更していない。保存されていた元builderでは、Candidateへの実データ参照はsessionCount/sessionListSha256/trainingSessionsの3項目のみ。classCountsはincident説明のfield名として現れるだけで、計算式から参照されない。

| 影響先 | 判定 | 根拠 |
|---|---|---|
| session数・budget合計 | NOT_USED | 標準blockとsession identityから独立再導出 |
| reuse / freshness責務 | NOT_USED | 固定された規範的役割、元contract byte一致 |
| Development event200 | NOT_USED | 旧stage2 Checkpoint A targetの出典確認 |
| Evaluation event97 | NOT_USED | 固定assumptionによる最悪率0.5の計算 |
| buffer0 | NOT_USED | session欠損率根拠なし、拡張禁止という既定方針 |
| 取得量・request推定 | NOT_USED | planning universe、coverage pages、工学的assumptionのみ |

Counterfactual replayでは、元builder sourceをSHA `1f287bf621d7842030134f330082f38c0ee8231866302a41f4789e69e4e01702` で保存し、I/O adaptersだけを差し替えた。Candidate outcome fieldを0個にし、identity3項目以外への参照は失敗させる。budget式・責務定義は変更0。元contract SHAとreplayed SHAはともに `028855230bc39ae37fcfda1395bc5e7358b6e8416dc810fce20349b4ef1f2d63`。SHA確認はraw bytesのみで、Candidate outcome JSONを再decode/表示しない。Git source metadataは既存pin済recordを使用するため、replay/CIに外部通信や全branch checkoutは不要。

| Block / 役割 | sessions | 出典・責務 |
|---|---:|---|
| A Entry Validation | 30 | 既存LONG validation30を維持 |
| B Entry OOS | 30 | 既存outer OOS30標準をEntry専用に適用 |
| DEV EXIT/Capital/Portfolio Development | 既存76 | 実使用済identityと共有Development契約 |
| C EXIT Validation | 30 | 既存validation30標準 |
| D EXIT OOS | 30 | 既存outer OOS30標準 |
| E Integration＋Capital＋Portfolio共同Validation | 20 | 既存replication20標準。全rule開封前Freeze |
| F Existing Ark Final Comparison | 30 | System-fresh outer comparison |
| G Final Prospective OOS | 25 | 既存LONG prospective25目標 |
| **新規Fresh合計 A～G** | **195** | 30＋30＋30＋30＋20＋30＋25 |

session-role gross463からDEV共有152とE共有40を除いてnet unique271。既存Development76を差し引いた新規Freshは195。Eを3回分60日として数えず、旧future20を控除しない。Required stageのomission0、double count0。既存Fresh credit0、実event yieldによる日数補正0。

200は旧EXIT stage2の `developmentPolicy.devATargetIndependentFirstEnter`。旧200/500/1000/2000は段階的checkpointであり、200のみ前回設計で新LONG Developmentの最低適格性に採用した。今回変更しない。

97は `ceil(1.96²×0.5×(1−0.5)/0.10²)`。1.96、最悪率0.5、nominal half-width0.10は前回明示assumptionで、Development observed hit rate等のplug-inはない。first Entry / symbol-sessionは操作上のdistinct eventでありIIDではない。97件によるcluster-adjusted精度・P&L精度・多重比較powerを保証しない。固定session全体 AND event最低量。不足時INCONCLUSIVE、追加session・早期終了・threshold緩和は不可。

Component freshness: DEV76はEXIT/Capital/Portfolio開発で共有可能だが、いずれのValidation/OOS/Final ComparisonにもFresh扱いしない。A/B、C/D、DEVとすべての新規blockは分離。

Shared E20: Integration、Capital、Portfolioの全artifact/rule/metricを開封前に固定した1回の共同評価のみ。同一20日を独立3回の再現と呼ばず、評価後のtuningは禁止。

System freshness: F30/G25は、両比較armの上流全component・配分・Portfolioのtuning未使用を要求。Fは同一session/universe/cost/cadence/capital/execution仮定、LONG現物のみ。GはF後の無変更system確認であり、F/G結果後のcomponent変更は禁止。具体的日付のFresh証明は次のdataset/取得contractのgateであり、今回満たしたと偽らない。

Legacy future20は別枠保護。UNKNOWN101は利用可能量へ入れない。SEALED25（旧Entry15＋10）、RESERVED4の解除・控除なし。EXPOSED375/RESERVED4/SEALED25/PROTECTED1/PURGED3/EXCLUDED4/FRESH0/UNKNOWN101/TOTAL513という台帳は不変。

再発防止としてstrict metadata input schemaを追加。許可されないroot/nested field、別型への置換、missing field、identity重複/hash不一致、observed-rate差し替え、予算変更、stage欠落、future20控除、E二重計上をFAILとする。拒否時に禁止値をexceptionへ表示しない。allowlistはmetadata fixtureにのみ適用し、モデルや研究結果を変更しない。

Offline regression: 新規23 tests PASS、FAIL0、SKIP0（禁止field混入48 subcasesを含む）。前回metadata整合性50 checksもPASS。networkは既存kernel guardで無効化。Full model/performance regressionを再実行したという意味ではない。Research Foundation CIへ同じoffline testsを追加した。

今回のoutcome表示0、Candidate/Validation/OOS prediction0、OOS/EXIT outcome access0、model/scaler fit0、SHORT評価0、Yahoo/J-Quants/その他価格request0、provider metadata request0、実allocation変更0、reservation release0、sealed/protected開封0。Safety全false。過去incident1件は別に保持し、累積0と偽らない。

全58項目は [final-report-58-items.json](final-report-58-items.json)、Q1～Q20は [integrity-review.json](integrity-review.json)、数値とsourceの1対1対応は [numeric-provenance.json](numeric-provenance.json)。

次工程は **MINIMAL J-QUANTS FRESH DATA ACQUISITION CONTRACT**。exact date range、session list、universe、fields、cadence、request上限、storage、allocationを事前固定する。Global Budget Freezeは取得許可・Validation Dataset Freeze・Candidate測定許可を意味しない。今回はここでSTOP。
