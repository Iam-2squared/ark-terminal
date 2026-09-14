# Phase57 LONG-only Cash Equity — Data Budget and Dataset Split

## 結論

状態は **🟢 設計固定 / 🔴 取得BLOCKED**。L0は日足OHLCV・調整情報・point-in-time Masterだけで成立し、minuteを取得しない。L1/L2では既存のJ-Quants取得・pagination・1m→5m・timestamp実装を再利用するが、既存LONG+SHORT仮説や閾値は流用しない。

全remote branchの再監査により、mainのTDnet providerとは別に、historical research branchへ`/v2/equities/bars/minute`、`/v2/equities/bars/daily`、`/v2/equities/master`の実装とexact metadata inventoryが残っていることを確認した。旧報告の「J-Quants実装 = TDnetのみ」はmain限定として訂正する。

新規J-Quants Historical requestは行っていない。契約の再確認、Claude独立レビュー、Fresh日付固定、明示的な取得承認が揃うまでGateは閉じる。

## 現在分かっていること

| 項目 | 状態 | 確認結果 |
|---|---|---|
| main | 🟢 PASS | 監査基準SHA `b1d7460f7f624b59a1d97d8591ebcec47ce26be3` |
| LONG-only branch / PR | 🟢 PASS | `research/phase57-long-only-cash-equity` / PR #587 |
| 日足endpoint | 🟢 PASS | `GET /v2/equities/bars/daily` |
| minute endpoint | 🟢 PASS | `GET /v2/equities/bars/minute`、TSEのみ、過去2年、無約定minuteはrowなし |
| Master endpoint | 🟢 PASS | `GET /v2/equities/master`、日付指定可能 |
| 認証 | 🟢 PASS | v2 `x-api-key`。秘密値は閲覧・出力・commitしていない |
| Pagination | 🟢 PASS | 同一queryへ返却された`pagination_key`を付け、keyが消えるまで継続 |
| L0粒度 | 🔒 FROZEN | 日足 + dated Masterのみ。minute禁止 |
| 既存取得コード | 🟢 REUSABLE | historical branchにminute/daily/master、pagination、PIT filter、1m→5m、hash、安全境界あり |
| 既存価格本体 | 🔴 NOT REUSABLE | raw永続保存0 session。短期Actions shardは期限切れ |
| 既存metadata | 🟢 REUSABLE | 487 session、うち205 sessionはmetadata-only・outcome未参照 |

公式のplan別historyはFree 2年（12週遅延）、Light 5年、Standard 10年、Premium 20年。rate limitは順に5/60/120/500 requests/minute。minuteはadd-onで過去2年、planning rateは60 requests/minute。

## まだ分からないこと

| 未確定事項 | なぜ推測不可か | 解消方法 |
|---|---|---|
| 現在のbase plan | public browserは未login、local環境にもplan/keyなし | ユーザーがAccount画面でplan名と終了日を再確認 |
| minute add-onの現在状態 | 2026-09-10のrepo記録はLight + add-on、2026-10-06終了予定だが現在状態を保証しない | add-on名・終了日・60 rpmを再確認 |
| 保存・解約後削除条件 | repoにはraw/再構成可能derivativeを解約後削除するuser-attested contractがある | 現在の利用規約/Account表示で再確認 |
| Fresh 25のexact sessions | 将来の営業日が未完了 | outcomeを見ずcalendar順で25日を固定 |
| raw JSON exact bytes | 過去取得はrawを残していない | 本取得時にpage単位bytes/hashを記録。新しいprobe sessionは消費しない |

## 既存J-Quants実装の再監査

| 区分 | 場所 | 判定 |
|---|---|---|
| main | `server/providers/jquants-tdnet-provider.js` | TDnetのみ。価格Historical pipelineなし |
| Selector系 | `research/phase57-selector-capacity-v2` | minute adapter、date-wide capacity、Fresh allocation、timestamp contractを再利用可能 |
| EXIT系 | `research/phase57-exit-v4-hybrid-msh-large-scale` | minute+daily+masterのsession監査、pagination、PIT、corporate-action flag、hashを再利用可能 |
| Entry/Allocation系 | 複数Phase57 research branch | 同じminute adapterを参照。別実装を新造する必要なし |
| Actions artifacts | run `34031214529` | raw shardは期限切れ。sanitized manifest/digestのみ再利用可能 |

Canonical候補はminute adapter blob `c09556460f729b6091c2de4ba5849b9021288f84`、exact metadata inventory blob `2217ffee6b9607f5610d5484bffea884f65b7422`。LONG-only branchへ移植する場合は、fetch/normalize/cache基盤だけを取り込み、Frozen Minimal Hybrid、SHORT、既存thresholdは取り込まない。

## L0は日足だけで成立するか

**🟢 成立する。** +3/+5/+10%の日次Opportunity Censusは、当日と前営業日のadjusted close、日次volume/turnover、corporate-action audit fields、当日point-in-time Masterがあれば計算できる。1分/5分情報は検出時刻やRemaining Upsideを扱うL1まで不要。

L0は銘柄数だけでなくeligible universe比率も併記する。IPO初日、前日値なし、null OHLC、売買停止、0 volume、limit-up、ExRT/AdjFactor変化は黙って除外せず、別stratumまたはblocked reasonとして数える。Regimeは後付けbinを禁止し、前日までのTOPIX/volatilityだけで定義してから追加する。

## 252営業日 Data Budget

約3,700銘柄、過去205-sessionの実績（日足1 page/session、Master 1 page/session）を使うplanning値。

| 項目 | 252営業日案 |
|---|---:|
| 対象営業日 | 252 |
| 想定eligible銘柄/日 | 3,700 |
| joined L0 symbol-session | 932,400 |
| 日足response rows概算 | 932,400 |
| Master response rows概算 | 932,400 |
| 日足pages/requests | 252 |
| Master pages/requests | 252 |
| 合計requests | 504 |
| uncompressed JSON計画幅 | 0.34–0.75 GB |
| gzip転送/保存計画幅 | 0.07–0.26 GB |
| normalized Parquet計画幅 | 0.05–0.15 GB |
| Light 60 rpm理論下限 | 8.4分 |
| retry/hash/manifest込み計画 | 12–20分 |

再取得を許すのは、endpoint/API version/query/session/symbol-set/contract snapshot/hashのいずれかが不一致、provider correctionが新versionとして確認された、またはcacheが破損した場合だけ。同じidentityとhashなら再取得禁止。

252日すべてをDevelopmentとして開く案は棄却する。既存のoutcome-blind allocationを利用すると、clean 205日をDevelopment 90 / Validation 30 / Validation Confirmation 25 / OOS 30 / Final 30に分離でき、さらにFresh 25を将来温存できる。

## Dataset Split

| Block | Session | 開封タイミング | 主用途 | Model選択 | Threshold選択 | 最終評価 |
|---|---:|---|---|---|---|---|
| Development A | 30 | 契約・Claude・取得Gate後 | L0定義、初回Census | 不可 | 不可 | 不可 |
| Development B | 20 | AのL0 contract固定後 | L0再現、L1 label feasibility | 不可 | 不可 | 不可 |
| Development C | 20 | L1 label contract固定後 | feature family ablation、L2 fit | 可 | 不可 | 不可 |
| Development D | 20 | candidate family固定後 | inner temporal選択、threshold freeze | 可 | 可 | 不可 |
| Validation | 30 | model/feature/threshold freeze後 | 1回のfrozen評価 | 不可 | 不可 | 不可 |
| Validation Confirmation | 25 | Validation判定と再freeze後 | 2段目frozen確認 | 不可 | 不可 | 不可 |
| Untouched OOS | 30 | Claude OOS前review + 全freeze後 | 1回のouter OOS | 不可 | 不可 | 可 |
| Final Confirmation | 30 | OOS解釈を固定後 | 最終historical確認 | 不可 | 不可 | 可 |
| Fresh prospective | 25 | 未来25日が完成後 | prospective確認 | 不可 | 不可 | 可 |
| Prior-exposed diagnostic | 179 | source/parity検査のみ | performance以外 | 不可 | 不可 | 不可 |

Developmentは合計90日。日付境界とhigher-level classは既存metadata-only/outcome-unseen allocationを維持し、A/B/C/Dだけをoutcome未参照で時系列分割した。Validation失敗後に同じValidationを調整へ使った場合、そのblockは以後Development扱いとなり、新しい未参照Validationがなければ次candidateの強いclaimは禁止する。

## L1 / L2までの段階取得

| 段階 | Target / Feature | 取得粒度 | 取得範囲 |
|---|---|---|---|
| L0 | daily +3/+5/+10 census | Daily + dated Master | released Developmentのみ。minute 0 |
| L1 feasibility | winner、remaining upside、MFE/MAE、detection time | raw 1mをcausal 5mへ | Development B、case-control併用可 |
| L1 cross-section | Recall、precision、late rate、breadth | JPX date-wide 1m→5m | released Developmentのfull market |
| L2 | ablatable causal feature family | 同上 | Development C/Dのみ |
| Validation以降 | frozen selector metrics | full cross-section必須 | blockごとのrelease後に一度だけ |

過去実測でDevelopment 90日はminute 1,188 page、37,903,800 rows、5分足13,827,576 bars。daily/masterを含め1,368 requests、逐次約5.46時間、6 bounded shardsで0.9–1.4時間がplanning値。ただしL0時点では取得しない。

clean 205日の全minuteを先に取る案は、2,899 minute pages・92,131,136 rowsになるため禁止する。partition releaseごとに一度だけ取得する。

## Intraday節約とSelection Bias

Case-controlはall winner、near winner、high-volume non-winner、sector/segment/ADV matched control、seeded random liquid controlを含める。sampling probabilityとweightをmanifestへ残す。この集合で許されるのはfeature feasibility、mechanism ablation、error analysisだけ。

次はfull cross-sectionを必須とする。

- Early Winner Recall / precision / prevalence
- cross-sectional rank、market/sector breadth
- threshold calibration
- missed opportunity、portfolio opportunity cost
- Validation、OOS、Final/Fresh

Winner-only samplingで最終Selector性能を主張しない。同日Opportunity densityでsessionを選ばない。full-market date-wide取得はrowsが多いが、symbol別取得よりrequest数が少なく、全市場denominatorとbreadthを保つため、released sessionの正式評価では合理的。

## 保存・Manifest・Hash

rawはGit外のprivate encrypted user-only storageへ、page単位でimmutable保存する。最低限、provider、API version、endpoint、正規化query、sessionDate、fetchedAt、page count、row count、page SHA-256、aggregate SHA-256、symbol-set SHA-256、contract snapshot SHA-256を保存する。

derived 5mにはparent raw hash、transform version、timestamp contract、corporate-action policy、output hashを持たせる。provider correctionは上書きせず別version。現在repoに記録された解約後削除条件が再確認されるまでは永続保持可能と推定しない。

## J-Quants取得開始Gate

| Gate | 状態 |
|---|---|
| 公式endpoint / pagination contract | 🟢 PASS |
| 全branchコード再監査 | 🟢 PASS |
| artifact inventory | 🟢 PASS |
| L0必要データ | 🟢 FROZEN |
| L1/L2将来必要データ | 🟢 FROZEN |
| Dataset Split | 🟢 FROZEN |
| request/page/row budget | 🟢 PASS |
| storage/manifest/hash contract | 🟢 FROZEN |
| 現契約・終了日の再attestation | 🔴 BLOCKED |
| 保存/解約後削除条件の再attestation | 🔴 BLOCKED |
| Fresh 25 exact dates | 🔴 BLOCKED |
| Claude independent review受領 | 🔴 BLOCKED |
| Claude critical blocker解消 | 🔴 BLOCKED |
| operator明示取得承認 | 🔴 BLOCKED |

Gate moduleは、全項目が揃ってもcommitted planから自動取得を許可しない。最後にGit外の明示的runtime authorizationが必要で、sealed partitionはrelease SHA-256なしにmountできない。

## 次の1手

1. `docs/phase57-long-only-claude-data-budget-review-request.md`をClaudeへそのまま送る。
2. ユーザー側でJ-Quants Accountのbase plan、minute add-on、終了日、保存/削除条件を確認する。API key自体は共有しない。
3. Claude指摘をArk測定と分離して分類し、critical blockerだけcontractへ反映する。
4. Fresh日付をoutcome blindで固定し、全Gateがgreenになった時点でDevelopment Aの日足+dated Master取得案を再提示する。
5. 明示承認後も、最初の取得はL0 daily/masterだけ。minuteはL1 Gateまで0 requestを維持する。
