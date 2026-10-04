# 📝 last-traded-price MTM 最小案
Status: **PROPOSED_NOT_AUTHORIZED / DRAFT ONLY**  
作成JST: 2026-10-04T13:36:30.258+09:00  
Repo: Iam-2squared/ark-terminal  
Branch: capital-state9-vnext-20261004  
Basis HEAD: cf2f07986fa357fb45bb9e68cfd08bd0b73bc93e  
Source判定checkpoint: cf2f07986fa357fb45bb9e68cfd08bd0b73bc93e

## 🎯 最小変更範囲

現在の `CAPITAL_OBSERVED_CLOSED_5M_WINDOW_MTM_REFERENCE_V1` は変更しない。
以下はユーザー承認前の草案であり、実装・Capital replayとも0。
Frozen Entry/EXIT、Rank、MAX3/4/5、Liquidity、cutoff、EOD、execution friction、cash clocksは変更しない。

候補ID: `CAPITAL_VERIFIED_NO_TRADE_LAST_TRADED_MTM_V1`

## 📐 例外の発火条件

1. 現在のclosed5m window `[t-5,t)` に有効sourceがあれば、現行契約どおり最後の1m raw Closeを使う。
2. 0件なら、**成功した原providerの完全な同一symbol/session取得範囲とページング連続性から、そのwindow全体のTSE lit-session no-tradeを個別に証明できた場合だけ**、下記の条件付き例外を検討する。
3. 使用価格は、同じ営業日・同じ午前/午後regular sessionで、**直前の5分window `[t-10,t-5)` にある最後の実約定1m barのunadjusted Close**だけ。
4. そのbarのcompletion/既存research assumed availabilityは `t` 以前でなければならない。実際のhistorical arrivalはUNKNOWNを維持し、live known-atを新認証しない。
5. 複数の空windowを連続して無制限に跨がない。直前windowにもsourceがない、session境界、source欠損/ページング不完了、duplicate矛盾、鮮度不明なら従来どおりSTOP。
6. **この直前window限定も承認候補に過ぎない。performanceを見てage上限を延長しない。**

## 🧾 Valuationだけであり、fill/cashではない

- mark種別: `LAST_TRADED_REFERENCE_CONFIRMED_NO_TRADE`
- 無条件forward-fillではない。原source完全性・対象window no-trade証明・source時刻の3条件が必要。
- 新しい約定や現時点の売却可能価格を作らない。架空BUY/SELL、cash release、PnL=0処理は禁止。
- source CloseをMTMに1回使うだけ。execution frictionやcommissionをMTMに再適用しない。
- halt/板厚/SOR/PTS等のmarket qualityをno-tradeから推論しない。market statusがあるなら別列に保持する。
- window内Closeの代替として未来の次bar、High/Low、auction、翌日価格を使わない。

## 🔎 必須ledger

`valuation_timestamp`, `mark_kind`, `source_bar_start_timestamp`,
`source_bar_completion_assumption`, `actual_last_trade_timestamp=UNKNOWN`,
`age_seconds_from_bar_completion`, `source_response_sha256`,
`source_wrapper_sha256`, `no_trade_window_proof_sha256`,
`source_scope=TSE_LIT_SESSION`, `source_market_status_if_known`,
`cash_release=0_for_valuation`。

bar Timeはminute開始であり、正確な最後のtick時刻ではない。
ageはbar completion基準と明示し、tick時刻を捏造しない。

## 🧪 承認後だけ必要な有限検証

- 通常windowの既存挙動不変。
- 証明のない空window、古いsource、異sessionはSTOP。
- window後/翌日の価格変更で過去mark不変。
- 値の変化がMTM equity以外の架空fill/cash release/feeを発生させない。
- source selection、age、equity/cash、MAX3/4/5をPrimary/Independentで別計算してmismatch0。
- before-results precommit後、同じ現在LONG-only mechanics baseline MAX3/4/5のみ再開。
- 新State9 Capital、旧過去成績、threshold/deadline/liquidity sweepへ広げない。

## ⛔ 現在地

この案は未承認・未適用。既存MTMの空window STOPを維持。
今回の原source調査はno-tradeを確認したため、ユーザーの分岐指示に従って停止した。
