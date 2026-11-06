# Phase57 LONG-only — Fresh Data Allocation Audit / Conservation Plan

2026-09-16 JST. Metadata / allocation only. No outcome access or allocation change.

**PHASE57_LONG_ONLY_DATA_ALLOCATION_AUDIT_COMPLETE**

推奨は **D. INSUFFICIENT_INFORMATION**。棚卸し・保全計画は完了したが、独立Validationに使える未予約・未使用の期間は確認できなかった。Validation Dataset FreezeのBLOCKは解消していない。Candidate、model、scalerを変更していない。

最も重要な追加発見は、既存候補30日のうち **25日が旧Selectorでoutcome使用済み、4日がsource-validation用途の恒久除外、1日がpurge** であること。EXIT予約の解除だけではfresh Validationにできない。

## 1–6. Repository / integrity

| Item | Evidence |
|---|---|
| Repo / Branch / PR | Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / #587 |
| Audited remote head | `649ff89fa8542819d14fa3c5a7337f6dd4fab4a8` |
| Latest main observed | `6b6c4d522cd1863132185463a0aed74bc819be01` |
| Candidate Contract | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` — PASS |
| Final model | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` — PASS |
| Final scaler | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` — PASS |
| Selector payload | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` — canonical payload再hash PASS |
| Selector freeze commit | `565d74b3dea823581fdb32380113aac5913a248d` — 参照維持 |
| Ridge artifact reference | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` — 参照維持、外部raw artifact再取得なし |
| Fit Contract | `64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938` — PASS |
| Development Evidence | `68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead` — PASS |

Github remote branch headsを直接確認。710 remote branchのローカルtreeを検索し、54種類のmetadata候補path/blobを記録した。重点対象はallocation、inventory、data plan、session list、closeout data-use manifest。選択した研究branchのheadはremoteと照合済み。4つの自動capture branchは更新があり、最新outcome payloadは開いていない。全branch全履歴の完全な非曝露証明ではない。

## 7–12. Master inventory

| 排他的分類 | Session identities |
|---|---:|
| EXPOSED | 375 |
| RESERVED | 5 |
| SEALED | 32 |
| FRESH_AVAILABLE | **0** |
| UNKNOWN | 101 |
| **合計** | **513** |

対象は既存historical inventoryの487識別子と、旧Entryの明示済みfuture予約26日。**412日付対応済み＋101 parent ordinalのみ**。今後のrule-only枠（LONG prospective25、Capital integrated20）は正確なsession listが未確定なので加算していない。513はRepo全歴史の総session数ではない。その他期間・P25のsymbol-session数・未確認capture datesを合算していない。

分類の優先順位は、肯定的なexposure記録→日付未対応UNKNOWN→SEALED→RESERVED→UNKNOWN。予約・封印は別flagとして保存するため、EXPOSEDでも既存予約を解除しない。RESERVED5は「予約が5日しかない」という意味ではない。

Parent reserveの1–179は、日付付き179件の時系列と既存ordinal/date対応58件・holdout29件を照合した。180と282は明示された境界日だけを使用。181–281の101件は営業日を生成して埋めていない。

375は日付／識別子で紐付けられた曝露確認の下限。Capital inventoryのEXIT Block CにはProtected期間と重なる曝露記録があるが、全Protected ordinal/date対応がないため残りを勝手に割り当てていない。UNKNOWN101は全て保護を維持する。SEALED32も世界全体での未使用を証明した数ではない。

`master-ledger.json` にsessionDate、source、availability metadata、複数allocation、purpose/status、exposure/reason、sealed/protected、各研究の使用・予約flag、reallocationAllowed、notesを保存。過去のscope限定「untouched」と他研究の使用済み記録を両方残している。

## Allocation matrix

下表は重複する**契約別ビュー**。行同士を合計しない。ローカル価格データは閲覧せず、Development保存artifact以外の現在の価格cache存在はUNKNOWN。旧metadataのrawPersisted=falseを現在の全cache不存在とは解釈しない。

| Dataset / period | Sessions | Cross-research exposure | Current allocation / reserved for | Reallocate? | Source / local data |
|---|---:|---|---|---|---|
| LONG Development 2024-09-10–2025-01-09 | 80 | 76確認、4未確定 | Selector/Entry/EXIT/Allocation/Portfolio共同Development | 今回不可 | J-Quants / 76の保存成果identity確認 |
| LONG Validation 2025-01-10–02-25 | 30 | 25曝露＋4source除外＋1purge | LONG ValidationとEXIT DEV_B/Validation競合 | 今回不可 | J-Quants / raw cache UNKNOWN |
| LONG Replication 2025-02-26–03-26 | 20 | 19曝露＋1purge | Locked Replication | 今回不可 | 同上 |
| LONG Primary OOS 2025-03-27–2026-07-06、不連続 | 30 | 30曝露記録 | OOS封印は維持 | 不可 | 同上 |
| LONG Contingency OOS 2026-07-07–08-19 | 30 | 30曝露記録 | OOS insurance、性能救済不可 | 不可 | 同上 |
| LONG Reserve 2026-08-20–09-09 | 15 | 15曝露記録 | Admission failure用 | 不可 | 同上 |
| EXIT DEV_A 2024-09-10–12-20 | 70 | 66曝露、4未確定 | EXIT Development | 今回不可 | 同上 |
| EXIT DEV_B 2024-12-23–2025-01-24 | 20 | 16曝露、4source除外 | EXIT Development | 今回不可 | 同上 |
| EXIT Validation 2025-01-27–03-11 | 30 | 28曝露、2purge | EXIT Validation | 今回不可 | 同上 |
| EXIT Holdout 2025-03-12–2026-06-15、不連続 | 25 | 25曝露記録 | Historical Holdout | 今回不可 | 同上 |
| EXIT OOS 2026-06-16–07-28 | 30 | 30曝露記録 | OOS封印維持 | 不可 | 同上 |
| EXIT Future Reserve 2026-07-29–09-09 | 30 | 30曝露記録 | Reserve封印維持 | 不可 | 同上 |
| 旧Selector/Entry parent1–179、2025-04-15–2026-01-07 | 179 | 過去研究曝露 | Diagnostic / 旧研究用途 | freshへ戻せない | J-Quants / UNKNOWN |
| Protected parent180–282、2026-01-08–06-11 | 103 | 一部EXIT曝露記録、全対応未確定 | Protected | 不可 | J-Quants / identifierのみ |
| 旧Entry Fresh 2026-09-10–10-21 | 26 | 未使用を全研究横断で証明していない | Validation15 / purge1 / OOS10 | 不可 | Calendar metadata / raw UNKNOWN |
| Legacy Capital integrated、2026-10-22以降 | 20適格日rule | 将来枠、実日付未列挙 | Integrated OOS | 不可 | J-Quants availability条件あり |
| LONG prospective、2026-09-15以降 | target25 rule | 実日付未固定 | Final comparison | 不可 | 他予約との重複UNRESOLVED |

現時点のpositive exposure記録は過去の研究での使用を示す。今回OOS/EXIT成果を開封して得た数ではない。Developmentの再利用自体と、独立Validation/OOSとしての再利用を区別する。

## 13–16. Existing30 conflict / authority

| Dates (JST, explicit sessions) | EXIT owner | Legacy exposure / exclusion |
|---|---|---|
| 01-10, 01-14, 01-15, 01-16, 01-17, 01-20, 01-21, 01-22, 01-23, 01-24 (2025) | EXIT stage2 DEV_B_LOCKED、10日 | Selector使用6、source恒久除外4 |
| 01-27, 01-28, 01-29, 01-30, 01-31, 02-03, 02-04, 02-05, 02-06, 02-07, 02-10, 02-12, 02-13, 02-14, 02-17, 02-18, 02-19, 02-20, 02-21, 02-25 (2025) | EXIT stage2 VALIDATION_LOCKED、20日 | Selector使用19、purge1 |

所有者は `research/phase57-exit-v4-hybrid-msh-large-scale`。2026-09-10のcontract v1.1.0、status `FROZEN_RESULT_BLIND`。

| Source | SHA-256 |
|---|---|
| EXIT data-allocation-contract-v1.json | `7e2792dfe35998716535bbbe0c9347adf87c9d6179f004b405bf0afd7240faec` |
| EXIT allocation-manifest-v1.json | `316d65a051ef62a0917446a910eabd9c46f2b577486fb5ead5743c446075a276` |

明示的な保護はprotected180–282再配分禁止、Fresh Validation/OOS再配分禁止、結果依存reshuffle禁止、Development未unlock。上記30日をEntryへ移すrelease/supersessionは確認できない。新しいLONG共同再利用方針だけを、旧契約の黙示解除とは扱わない。

今回新たに照合した `phase57-selector-closeout-data-use-manifest.json` は3評価roleを既に開封済みと明記している。旧Entry inventoryのSOURCE_VALIDATIONは研究splitへの恒久除外を明記。このため「別branchに予約されているだけ」という従来の理解より、独立性の問題が大きい。古いFrozen artifactは書換えず、本auditを追記した。

EXITで後工程に本当に十分かはLONG EXIT専用minimumが未定義なのでUNRESOLVED。旧予約の数を統計的必要量として発明しない。

## 17–24. Future requirements / alternative windows

| Stage | Required sessions | Existing allocation | Still missing |
|---|---|---|---|
| Entry Validation | 既存planで30 | 上記30、使用不可 | 独立・未予約の30日identity |
| Entry OOS | Entry専用数UNRESOLVED | LONG共有Primary30＋Contingency30、独立性問題 | Entry専用scopeとclean identity |
| LONG EXIT Development | LONG最低量UNRESOLVED | 旧EXIT70＋20、LONG共同Dev80/実使用76 | ownershipとLONG専用scope。既存Dev再利用を優先検討 |
| LONG EXIT Validation | LONG最低量UNRESOLVED | 旧EXIT30＋holdout25 | clean identityと専用budget |
| LONG EXIT OOS | LONG最低量UNRESOLVED | 旧EXIT30＋reserve30 | clean identityと専用scope |
| Integration | LONG別枠UNRESOLVED | 旧integrated future20 rule、LONG共有評価計画 | `INTEGRATION_DATA_NOT_YET_ALLOCATED` as distinct LONG dataset |
| Capital / Portfolio / Ark比較 | LONG別枠UNRESOLVED | 同じ旧future20、別の20ではない | LONG全体の独立評価scope・必要量 |

確認済みFRESH_AVAILABLEの代替historical windowは**0件**。2026-09-10–10-21は旧Entry予約済み。2026-10-22以降の最初の20適格sessionsはCapital integrated OOSに事前登録済み。その他期間はUNKNOWNであり、新しいValidation期間に選定しない。

## 25–30. Scenario comparison / conservation recommendation

| Axis | A: EXIT全維持＋別Fresh | B: EXIT一部再配分 | C: 限定新規取得 |
|---|---|---|---|
| Entry Validation | target30、確認済み代替0 | 使用可能subset未確認 | target30、独立identity未確定 |
| Entry OOS | 共有既存枠維持、専用数未決 | 同左 | 同左＋新規枠予算未決 |
| EXIT Development | 旧90維持 | 90−x、x未選定 | 旧90維持 |
| EXIT Validation | 30＋holdout25維持 | 30−y、y未選定 | 30＋holdout25維持 |
| EXIT OOS | 30＋reserve30維持 | 同左 | 同左 |
| Integration残 | 旧future20維持、LONG別枠未決 | 同左 | 同左 |
| Capital/Portfolio残 | 同じfuture20を1回だけ数える | 同左 | 同左 |
| New provider data | cache/window次第、UNRESOLVED | 同左 | 条件成立後のみ必要、量未確定 |
| 今回J-Quants消費 | 0 | 0 | 0 |
| Governance risk | 既存保全できるが実行可能windowなし | 解除しても曝露は消えず、EXIT必要量も不明 | 同じ日を再取得してもfreshにならない |

上表の「維持」は予約数の維持であり、独立検証に利用可能な日数の保証ではない。各scenarioでfreshと確認できた既存枠は0。具体的なsession再配分、取得、Validation選定は実行していない。

**推奨D**。Aを保全上の基本姿勢とするが、実在する代替Fresh windowが未確認なのでAを実行可能と結論しない。Bは独立性を修復できない。Cもwindow・entitlement・cache・後工程予算を確認する前に推奨しない。

保全計画：

1. Protected/OOS/既存予約は全て維持。矛盾が見つかっても勝手に開放しない。
2. 既存のoutcome-exposed Developmentを、明示contractの下でEXIT/Allocation等に共同利用する。新鮮なデータをDevelopmentへ追加消費する前提にしない。
3. Entry・EXIT・統合・Portfolioそれぞれの独立評価が必要なのか、全仕様を同時freezeして1つのstackを評価するのかを先に決める。同じsessionを独立データとして何度も数えない。
4. 全体予算とownership/exposureを整合後、正確なidentityをOutcome-Blindで固定し、private cache identityを調べる。必要な場合だけ別指示で最小取得。
5. 既存Repoの2026-09-15 entitlement記録はLight/Minuteの終了予定を2026-10-06としている。10-22以降のfuture枠を利用可能とは仮定しない。今回はアカウント照会も規約再確認もしていない。
6. 再配分が将来必要ならFROM/TO/session list/reason/impact/remaining data/authorizing contractを記録する。今回そのauthorizing contractは発行しない。

## 31–39. Access / safety / verification

| This audit action | Count |
|---|---:|
| Allocation changes | 0 |
| Candidate prediction / E[L] | 0 |
| Validation outcome access | 0 |
| OOS outcome access | 0 |
| EXIT outcome access | 0 |
| Model fit / scaler refit / OOF generation | 0 |
| Threshold change / comparison | 0 |
| SHORT evaluation | 0 |
| Yahoo requests | 0 |
| J-Quants requests | 0 |
| Other market-data provider requests | 0 |

Provider countは**本auditの操作についてCONFIRMED**。Github metadataアクセスはmarket-data provider要求ではない。他の自動jobが動いていないという主張はしていない。

全Safety flags false：executionAllowed、brokerWriteAllowed、excelOrderWriteAllowed、rssOrderFunctionAllowed、liveTradingAllowed、paperTradingAllowed、automaticPromotionAllowed、productionUpdateAllowed、transmitted。LONG-only / cash-equity保護を維持。

Metadata builderは既存seccomp offline guard下で正常終了。重複identity、分類合計、parent ordinal対応anchor、30日内訳、Frozen hashのassertion PASS。市場取得client・model・evaluatorをimportしていない。今回performance regressionやmodel synthetic fitを再実行していない。全npm test PASSを新たに主張しない。差分はaudit scriptと追加metadata/reportのみ。

## 40–41. Verdict / exact next action

**PHASE57_LONG_ONLY_DATA_ALLOCATION_AUDIT_COMPLETE**

COMPLETEは棚卸しと計画の完了。データ充足、予約解除、Validation Dataset Freeze、Candidate採用を意味しない。UNKNOWNは上記scopeのまま残している。

次の工程は、別の明示指示による**全研究のownership/exposure整合と後工程budgetのArchitecture Decision**。最初に、旧Selector closeout/Capital記録とLONG/EXITのuntouched記載の矛盾を扱い、Protected calendar対応・current cache/entitlementのmetadataを確認する。既存30日の移管だけで解決とはしない。新しい期間選定・取得・Validation predictionには進まずSTOP。

## Machine-readable evidence

- `master-ledger.json`: 513 disjoint identities、複数予約・曝露・UNKNOWNの保持。
- `conflict-30.json`: 30日の全行とsource SHA。
- `audit.json`: counts、契約別matrix、Frozen hash照合、source commit/blob/SHA。
- `conservation-plan.json`: requirement matrix、A/B/C、保全ルール、D推奨。
- `source-metadata-extracts.json`: outcome値を含まない予約・exposure・将来rule抽出。
- `discovery-catalog.json`: 710 branchのheadとmetadata候補、未読範囲。
- `manifest.json`: 本audit成果のSHA。Dataset Freeze manifestではない。
