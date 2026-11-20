# 既存 No.1.1 Selector に追加する長・中・短期「上昇構造だけ通過」フィルター

発行: 2026-10-23 JST。対象: 統合作業 PR #592。**新Selectorの採用・新モデル作成ではない。**

ユーザー指示: 別の寄り前Selector設計から「長中短期が下降または横ばいの銘柄は候補から除外」だけを参考にする。一回だけ寄り前で銘柄選定する方式は持ち込まない。

## 採用する範囲（元V2提案のG1だけ）

計算の参照元: [V2_DESIGN-ja.md の §4 G1](https://github.com/Iam-2squared/ark-terminal/blob/37eb703065dc1698757dd320e40629dab2e40448/research/preopen-selector-v2-20261014/V2_DESIGN-ja.md)。

D当日の購入判断に、D-1（直前取引所営業日）までの比較可能な日足終値だけを利用する。日足SMAの期間は **5 / 15 / 25 / 75営業日**。任意のnについて `UP_n = (SMA_n(D-1)>SMA_n(D-2)) AND (Close(D-1)>SMA_n(D-1))` とする。これは同値をUPに入れない厳密な判定。SMA5>SMA15>SMA25>SMA75の完全並び順は要求しない。

- 長期 UP = UP75
- 中期 UP = UP25 AND UP15
- 短期 UP = UP5
- 3軸UPだけ**PASS**し、元Selectorに渡す候補identityとして残す。
- 1～2軸UPは**WAIT**、全軸非UPは**REJECT**。どちらも当日の候補から外す。
- 欠損、企業行動による価格basis未証明、実受信時刻が判断時点より後のデータは**UNKNOWN**。推測値で救済しない。

傾きは `SMA_n(t)-SMA_n(t-1)=(C_t-C_(t-n))/n` と等価。最長75日のSMAと前日差だけで比較可能な終値76セッションが必要。MA以外の元Selector入力（市場・業種・Va等）は引き続き必要。

これは将来の上昇を保証せず、レンジ上放れ・底打ちからの反発を捨てる可能性がある。モデルの再学習なしでも、候補母集団が変わることで元No.1.1の経済成績・キャリブレーションは変わり得るため、新しいゲートの効果を、事前に決めた日付で元Selectorと並走比較してから採否を決める。

## 元の統合版から変更しないこと

**元Selectorは各日10時刻でTop5を更新**する。上のG1はその前に「元Selectorへ渡してよい銘柄集合」を絞るだけ。一回だけの寄り前選定、寄り前Top15、別V1/V2学習モデル・順位・資金集中・順次回転は取り込まない。元のFrozenコード・係数・P1/Q70・State9・H235・Capital・EXITは変更しない。

実装入口は [runtime/no11_existing_selector_trend_prefilter.mjs](runtime/no11_existing_selector_trend_prefilter.mjs)。純粋関数が明示的な取引所calendar・日足閉値・knownAt・価格basis・企業行動確認を受け取り、PASS identityと各symbol理由を返す。実発注やRSS操作は持たない。読取専用のopt-inプロトタイプで、元Selector市場経路との連携は未完了。モデルfit・学習・注文送信は0。

## RSSのみでの展開方針と残る確認

- 日足はRSSの日足履歴（`RssChartPast`のDなど）を使う候補。75日履歴までを場中の判断前に取得・照合できるか測定する。朝の一度きりの**選出**ではなく、確定済みの長期構造入力を準備するだけ。
- フィルターでPASSになった集合に、今までの**10回の元Selector**を適用する。
- RSS市況情報は同時最大500銘柄、RssChartは50関数という容量上限。PASS候補が500銘柄以下になるかは未計測。501件以上でも上位500へ勝手にtruncateしない。UNKNOWN/不完全な市場を全市場の品質PASSと呼ばない。
- RSSの正確な分Va、銘柄master、企業行動、実受信時刻が未認証という既存の課題は消えない。
- 次は公式取引日calendarと原本の77日以上の日足を用い、日別のPASS/WAIT/REJECT/UNKNOWN件数、RSS容量、元Selector選出・H235・損益・機会損失の差を評価する。その上で実市場のread-only Shadowへ接続する。

`originalIntradaySelectionScheduleModified=false`、`productionReady=false`、`orderTransmission=false`。戦略変更候補の純粋フィルター実装であり、既存Frozenの経済的同一性や本番許可を主張しない。
