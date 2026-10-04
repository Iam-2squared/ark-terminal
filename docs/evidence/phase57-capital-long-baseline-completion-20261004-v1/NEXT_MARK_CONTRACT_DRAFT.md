# 📝 今回LONG-only baseline — MTM契約変更案

JST: 2026-10-04T12:40:13.534+09:00
Basis HEAD: `262e4da6f39c6f36dd1ac649c0be6121e11e0b93`
Status: **PROPOSED_NOT_AUTHORIZED / NOT EXECUTED**

## 🎯 対象

今回のFrozen FIRST ENTRY v2 P1_Q70、Frozen Structural EXIT v3、既存downstream EOD/cutoff/liquidityを維持したcurrent-input / legacy-mechanics baselineとFixed sanityだけ。新State9 Capital、旧SHORT時代の成績の代用、Integrated開始は対象外。

## 🔍 今回確認できた事実

最初の実funded MTM blockerはdistinct position1、session1、6arm共通。grid最後のexact1minute sourceは0件だが、同じ終了済み5分窓に保存されたtrade-minuteは4件ある。最後に保存されたminuteはgridの2分前。保存済みPrimary/Independent抽出sourceのこの窓の値比較mismatch0。

これはpriceが欠けたminuteを生成できる証明でも、真のno-tradeの証明でも、native provider5m source回収の証明でもない。

## 🔐 提案する明示許可

**CAPITAL_OBSERVED_CLOSED_5M_WINDOW_MTM_REFERENCE_V1**を別lineageで結果前precommitする。

- 正規sessionの各5分grid時刻tに、同一の閉じた窓[t−5,t)に存在する保存済みadmissible trade-minuteだけを参照する。
- その窓の最後の保存済みtrade-minute Closeをobserved-window reference markとする。exact final1m Closeやprovider-native5m Closeと同一だとは呼ばない。
- 各sourceの終了/assumed availabilityがt以下であること、source hash/lineage、raw価格、regular-session区分を確認する。
- 次の窓、次session、auction、High/Low、将来EXIT結果はmark選択へ使わない。
- 空の5分窓へ前の窓のCloseを持ち越さない。interpolation、架空bar、価格0、欠損PositionのPnL0扱いをしない。
- 窓が空、source lineage不明、source contradictionなら引き続きPOSITION_MEASUREMENT_BLOCKED。取得欠落とno-tradeを推測で同一視しない。
- Historical observed-source referenceであり、actual arrival UNKNOWN / live execution certification falseを維持する。
- これは既存exact-final1m契約のtechnical synonymではない。markの違いによりcurrent equity、以後の数量、DD/utilizationが変わり得るため明示承認が必要。

## 🧪 承認後に限る有限実行

Fixed sanity MAX3/4/5、CURRENT_CAUSAL_BASELINE MAX3/4/5の6armを各1回。新fit0、deadline/threshold/weight/liquidity sweep0。全1,600候補を保持。Adaptive MAX-Nはconcurrent capだけで1/N sizingへ置換しない。

まずsynthetic/future-suffix canaryと独立mark再構成を行い、その後同一契約/同一sourceで6armを実行。funded UNKNOWNは引き続きmeasurement blockerとして報告する。必要なら既に許可されたEOD-window execution source取得だけを最小funded subsetに限定する。新intraday MTM provider取得はこの提案には含めない。

## 📊 完了成果物

今回のLONG-only Final Equity / Return / geometric session mean / rolling20・22・24 / MaxDD / utilization / costs / accepted-rejected / liquidity skip / Winner captureを独立会計と照合し、実測できたものだけ表・グラフへ出す。未測定はnull。結果後の救済変更はしない。
