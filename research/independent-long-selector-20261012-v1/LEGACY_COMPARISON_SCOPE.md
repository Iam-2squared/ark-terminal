# 正式Frozen比較 — 2026-10-14実測完了

LEGACY_COMPARISON_COMPLETE=true。旧weights/spec/feature順序・price gate・選出identity・時刻は不変更。新の全7watchlistを固定した後、許可済みReport7日だけを数値評価した。原本は保存byte/hash、CSV/JSONの文字列通過と、許可後の数値化を分けて記録。

| 固定identity | SHA256／値 |
| --- | --- |
| active Selector | FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75 |
| active spec | e75a49adb2a35497b6ac4d1afdd2942f87d9e139f04ae98e2478ca564ee874d8 |
| min-price75 payload | d782bd93761db2fe524b040479c7b3fc3f28331cc21c5f97fd2ad3f2b6058fb4 |
| parent commit | 565d74b3dea823581fdb32380113aac5913a248d |
| parent payload | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| parent model | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |
| selected-and-excluded-identities.csv | 0db332537661c1dece6becdfac538e5eeb641fb52754ee9f5c607208abb92a23 |
| new-paths.json.gz | eeb15545a278a7058a0b40042169df8ad7560077289c7bef3412977decc524d2 |

2原本は5,086,203／1,953,620bytes、計7,039,823bytes。CSV `arm=new` が正式min-price75選出。`arm=old` はその前の親選出。7日×10時刻×Top5=350 events、重複除去268 symbol-days、重複event82。

旧本来の決定価格→後続continuous5m High：負11／0〜<1%101／1〜<2%85／2〜<3%54／3〜<4%29／4〜<5%20／≥5%48／UNKNOWN2。known348、exact0=18は0〜<1%内数。負を0へclipしない。分母はlatest causally available close（age0〜5分、price>75）、未来はstart>=decisionTimestamp、5分足、終端auction High除外。

原本futureのo/h/l/cは価格ではなく `100*(rawPrice/decisionPrice-1)` という％。保存projectionコードを確認し、原本分足の34,144 fieldと観測分数を照合した後、元raw価格＋Fractionで境界を再計数した。future観測slot8,536、missing3,014、観測分数<5のslot5,178。親evaluator同様に観測futureを使い、完全session pathの認証ではない。

旧選出集合の日通しOpen→High事後記述（重複除去268）：98／33／26／11／24／76、UNKNOWN0。350 repeated eventsへの同じ日足付与は別集計。事後表は選出前のHighも含み、旧の寄り前能力・実現利益・A/B/Cの同条件比較ではない。全て同一session・同一調整前OHLC。Low/Closeも別集計、個別価格/候補/event行はprivateのみ。

親の実FITはC20日（2024-11-11〜12-06）＋D20日（12-09〜2025-01-09）、1,077,111rows。正式payloadのfitPartitionsとsessionIdentitiesを照合。新Report7日全てが親FIT内（6日C、1日D）。A21/B15日はCD FIT外だが既閲覧Development。76日全部がFITまたは独立検証だったとは書かない。Fresh/OOS credit0。

A/B/Cは同じ寄り前eligible集合・日・K15。Dは日中K5×10時刻・情報・集合・親FIT露出が異なる。旧の朝への戻し、前日値/0代入、再学習、原本/weights改変、Entry/EXIT/Capital replayは0。
