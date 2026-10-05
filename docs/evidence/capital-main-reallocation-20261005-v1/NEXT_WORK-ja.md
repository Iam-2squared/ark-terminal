# ▶️ Capital Main — 次の有限作業仕様

文書ID: CAPITAL_MAIN_PREBUY_REALLOCATION_PRECHECK_V1  
作成実時計: 2026-10-05T23:50:25+09:00  
状態: READY_FOR_READ_ONLY_MONEY_PATH_PRECHECK / NO_RUNTIME_POLICY_SELECTED

## 🎯 目的

V5の保存原本を使い、**どの資金・枠を減らす操作が、どの合法な新Entryの実数量へ届くのか**を明らかにし、次のCapital変更機構を1つへ絞る。Selector・Entry・EXITは変更しない。

新たなmodel fit、AUC/元bootstrap/OFF Replay、旧closed route再実行は不要。既に存在する集計・coverage・certificationを読み取りでreuseする。以前の結果を確認するための大規模再計算をしない。

## 📚 入力

正本はhandoff commit 220e0d8863978f5d82d0d83189d473252efda146のINPUT_BINDING.json、今回のSOURCE_BINDING_CHECK.json、保存V5 result / trade / curve / native proposal、凍結Expert packet。

privateの取引単位情報は既存private artifactで保持する。公開GitHubにはコード、集約結果、schema、hash、根拠path、実時計、失敗理由を保存し、未公開の生データ・銘柄別台帳・秘密情報を追加しない。

## 1. Wealthの定義を先に結び付ける

WEALTH_OBJECTIVE_BINDING.jsonに以下を明記する。

| 項目 | 取扱い |
|---|---|
| 主目的 | 費用込みの20-session最終資産。目標100万円→約200万円 |
| 中心値 | 中央値を中心に比較。最良1窓だけで達成としない |
| 既存比較用 | 保存された19個の正規化20評価session窓をそのまま保持 |
| 厳密100万円開始 | 各窓の初期cash=100万円・保有0による数量再現は未実施 |
| 営業日 | 元calendar/session coverageのauthorityを確認。欠落日を0%としない |
| 終点 | 凍結EXIT/EODが全決済したending_cash |
| 未決済 | 正式wealth未評価。MTMや0 returnで代替しない |
| Exposure | Developmentの反復利用を明示。Fresh/OOSへ改称しない |

最新ユーザーのwealth-only指示を反映する。旧研究のU5件数floor、全窓非劣化、元slot1/2全ID保護等を新研究の永久成功条件へ自動コピーしない。ドローダウン、Winner/Weak/Loser、稼働率は変化の説明として併記する。

## 2. 不足する資金経路だけを作る

既存のfunded、potential、realized損益、slot別集計はreuseする。重複するAUCや品質表を新たな成果として作り直さない。

必要なのは、保存decision identityごとの以下の結合である。

- 判断時点に実際に利用可能だった候補・score・価格・cash・equity・exposure。
- 購入数量、初回quantity、追加lot、BUY debit、band cap、target budget。
- 固定EXIT/EODによる売却・cash releaseと、保存台帳の実現損益。
- 候補を外す場合と減額する場合の、枠に対する意味の違い。
- 同batchの購入候補と、後続の合法な新Entryの関係。

現在decisionの提案作成に未来outcomeを読ませない。後続の価格、High、将来arrival、将来決済可否は評価側へ隔離する。過去成績を参照する場合も、保存OOF predictionの由来と、そのoutcomeが当該時点以前に確定したことを証明する。training resubstitutionを過去OOF性能として使わない。

## 3. 資金が止まる制約を区別する

REALLOCATION_CHANNEL_AUDIT.jsonは、次の状態を別々に保存する。

| 状態 | 判定の意味 |
|---|---|
| 同batchで合法な受け手あり | 元Entryと現在のcash・MAX3で新数量を出せる可能性 |
| 後続Entryにしか受け手なし | 現時点で未来の受け手を既知にせず、閉ループ評価が必要 |
| 100株以上を残す縮小 | cashは空くがslotは空かない |
| cap拘束 | cashを増やすだけでは追加数量が出ない |
| target拘束 | 購入除外でtargetが下がり、資金が未配分になる場合がある |
| 初回lot未達 | V5の追加配分対象に入れずquantity0 |
| 保有中の買い増し | 今回の許可された経路に含めない |
| 過去Entryの復活 | 凍結Entry変更になるため使わない |
| source不足 | 新購入経路の正式資産を測定できない可能性。未来の除外条件にはしない |

保存EXECUTION_SOURCE_COVERAGEには、book identityが揃っていても将来EOD sourceが不足する候補がある。既存V5が完走したことを、新candidate全完走の証明へ流用しない。将来のexecution未完了を知って購入候補から落とすことは禁止。

固定台帳の負損益は、介入による回避利益ではない。資金の受け手を事後的なWinnerラベルで選んだ台帳を戦略の成績として出さない。

## 4. 次のCapital機構を1つへ絞る

目指すインターフェースは「現在の合法なEntry群と予算から、購入可否を含む100株単位の整数数量を返すCapital層」である。

維持するもの:

- Selector / Entry / EXITの入力、identity、時刻、ルール。
- LONG現物cash-only、MAX3、100株、cost、same-symbol、Entry cutoff。
- MTMは評価額のみでcashを解放しない。cash解放は正しいSELLだけ。
- 既存保有の早売り、部分売り、置換、後からの買い増し、古いEntry再開をしない。
- 凍結Expertのscore・model・feature・時点を保持。MRETは相対診断のみ。

Capital内部のcap/target/購入可否/数量のうち、どの機構を変えるかは資金経路の結果で絞る。固定値のgrid探索、AUCの良いheadの適当なweighted blend、閉鎖済みReserve条件の緩和はしない。新ルールの閾値や数量式をこの段階で捏造しない。

## 5. 新candidateを評価可能にするための完了条件

後続の新candidate Workには、実行前に次を必ず確定する。

1. なぜ旧I2/M1/M2/Reserve/S_ONLYと異なる機構なのか。
2. 判断時点ごとの入力、整数数量式、caps、同時刻の処理順、tie処理、cash計算。
3. 全入力・code・policyのhashと、過去基準の算出時点。
4. 正式評価窓、初期cash、終点、欠測・未決済時の扱い。
5. 同policyの検証と新policy探索を分けた実行数上限。候補は最大1つに固定。
6. 未来suffix・outcome・同batch未確定結果で現在判断が変わらないこと。
7. V5との差が実際の購入数量・会計で初めて現れる点。
8. 最終資産で比較し、不利な結果も保存して同cycleの閾値救済をしないこと。

証明済みの同一policy/OFFを再実行して待ち時間を増やさない。ただし新しいquantity/cash経路の会計と因果順序は、新経路に対して必要な確認をする。

この引き継ぎ時点のruntime candidateは未選定。今回作成した仕様は次の資金経路監査の仕様であり、実装・Replay済みの主張ではない。

## 💾 保存・再開

作業単位ごとに実時計JST、現在地、完了、未実行、blocker、次の方針、counts、hashをGitHubへappend-only保存する。commit後にactual GETでSHA/tree/本文を確認する。

Claudeは現時点では不要。既存資料と独立した読み取りで解決できない構造上の争点が残り、判断を改善すると見込める時点にだけ依頼を検討する。常設レビューや毎回の利用はしない。
