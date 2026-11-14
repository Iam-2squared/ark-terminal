# ARK TERMINAL — 統合版 No.1.1 正式研究Freeze

**ユーザー指定により2026-10-08に新研究ベースラインとして固定。No.1原本は維持。**

## 統合版 No.1.1 = No.1 + Entry時2State除外 + 当日初回SELL約定後の新規BUY停止

1. 既存の凍結FIRST ENTRY/FIRST LAYER/State9/Capital V5 MAX3/Slot Reserve/R0/100株/費用/15:20 EOD/SHARP_DROP EXITを保持。
2. Entry時の**有効な正式State9 Primary**が`PULLBACK`または`SHARP_DROP`なら購入候補から除外。初回枠・初期空きSlot2/3・再利用枠・同時刻batchにも適用。除外済みEntry IDを復活させない。
3. **その日の最初の合法SELL fill**が発生したら、その売却fill以降、**当日中は新規BUYを一切行わない**。売却意図SELL_INTENTだけでは停止しない。翌営業日の開始で待機状態をリセットする。売却前の購入は元のV5、MAX3の範囲で通常通り。保有中の売却はその後も従来EXITを続ける。
4. 元No.1のSHAはpublic `fee1458ea7a526be3ee1c9819d3b1ade8f178c5a` / private `92763089a07ce0200cb63b887f1bede0e263ed47`。既存両State除外Freezeは `662042079c51788c0f2e6e6854bd4097dbc17851`。すべて原本不変。

## 20営業日・100万円開始・重複Development9窓の凍結成績

| 期間 | No.1.1最終資産 |
|---|---:|
| W13 | ¥1,199,976.00 |
| W14 | ¥1,208,521.45 |
| W15 | ¥1,186,195.35 |
| W16 | ¥1,237,207.65 |
| W17 | ¥1,254,606.35 |
| W18 | ¥1,272,885.70 |
| W19 | ¥1,273,762.20 |
| W20 | ¥1,251,120.20 |
| W21 | ¥1,260,811.35 |

最低¥1,186,195.35、中央値**¥1,251,120.20**、平均¥1,238,342.92、最高¥1,273,762.20。両State除外のみの旧研究基準より9窓中7改善・2悪化。200万円到達0/9。9窓は互いに重複し、独立9か月ではない。実受信時刻UNKNOWN、Fresh/OOS未実施。

## 独立検算と境界
研究用の旧基準9/9再現、Decimal/Fraction別経路27/27一致、11,213会計項目・18ペア差額検算一致。State9/Exit source planは共有で、完全独立な新State9検証ではない。No.1.1研究仕様の選定を明示したものであり、**本番稼働・自動売買・No.1原本の変更・main mergeを意味しない**。

## 次工程
No.1.1を変更せず、空き枠の利用、EntryとEXITの価格経路の相性、購入前情報に基づく新ランキングを別研究ブランチで比較する。最終採用基準は20営業日で100万円→200万円への資産接近のみ。分類精度の改善だけでは採用しない。

原本結果：[Vacancy STEP1/2](https://github.com/Iam-2squared/ark-terminal/blob/bb181f0c6e0bacd9fa64fbe7e5f065952c1a27df/research/vacancy-characterization-wait-after-sell-20261008/RESULTS_PUBLIC.json)
