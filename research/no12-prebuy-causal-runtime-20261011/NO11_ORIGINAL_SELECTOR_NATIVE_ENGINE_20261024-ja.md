# Ark統合版No.1.1 — 元Frozen Selectorの実コード接続（2026-10-24）

対象PR #592。2026-10-26は新開発開始日ではなく、既に実装した接続をPCで検証する日。27日の実売買は26日の実機read-only検査と運用安全審査を本当に合格した場合にのみ可能。原本・Frozen重み・main・PR #591・注文Excelへの変更なし。

## 追加したネイティブ呼出し

`runtime/no11_frozen_selector_native_shadow.mjs` の `runOriginalFrozenSelectorShadow` は、原本の以下をそのままimportして用いる：

- `normalizeAndAggregateMinuteRows`：元の1分OHLCV+実Vaから5分バーへ
- `normalizeMinuteProvenance` および `measureCorrectedRow`：最新確定Minute参照、0–5分鮮度、75円超の判定
- `buildCausalL1Features` / `addCausalBreadthContext` / `assignCausalLiquidityBuckets`：正式15特徴量の前段
- `scoreL2Candidate`：元JSONのRidge Y30 **固定15特徴量・固定係数**を読んでrank、各時刻Top5、同一session|symbolのWatch初回と再選定refresh

元Frozen JSONをGit blob SHA1で固定し、推論アーティファクトのハッシュ契約、10時刻とTop5規則を検証する。入力は2026日付の348 PASS mask、同日取引所カレンダー、当日dated master（前日基準・市場・sector・企業行動）、各銘柄の観測時刻付き**元の正確なVa円**を持つ1分足、前回Watch state。

**Vaの欠損、丸め不明、未来観測・同日後刻の入力、master不足、間違った日足日付、原本モデルファイル変更は許可しない。** nullを0にしてスコアリングする原本側の危険を避けるため、必須数値を明示的に検査する。BUY・モデルfit・注文式は存在しない。

## ここで過大評価しない

ユーザー指定の348銘柄への前段限定で横断幅（market/sector breadthや流動性三分位）が変わる。これは『元の重みを使った別候補母集団でのShadow』であり、元の全市場モデルの予測成績/同値を保証しない。元Selectorのsame-day dailyが持つ未来情報も、そのままライブへ逆輸入しない。

**PCのRssMarket348銘柄probeは価格・日付・時刻しか得ない。これだけでnative Selectorへ入力できるVa/5M/dated masterが完成したことにはならない。** RSS Chartの上限50・1分Va・H235の2026適用規則・現金・発注約定実機証拠はまだ残る。未来データの妄想で26日/27日のGo判定を作らない。

この時点では `productionReady=false` / `orderTransmission=false`。次に最重要なのは実Va adapterと入力を受けた総合Shadow、元24モデルの2026配備規則を検証可能にすること。追加の710 UNKNOWN調査や新学習は禁止。
