# No.1.1 — SelectorのVaを最短でつなぐ (2026-10-24)

元Frozen Selectorは1分毎の実売買代金Vaを5分足へ足し、累積売買代金・VWAP・VWAP傾斜・相対流動性を15特徴量のうち5項目で使う。`close * volume`をVaだと主張すると重み付きVWAPを変えてしまう。

楽天RSS公式 `RssMarket` の『出来高』『売買代金』『出来高加重平均』を、既存の348銘柄一時読取ワークブックの同じ銘柄単位で追加する。quote 500-symbol枠は増えず、`RssChart` 50枠も使わない。式は6フィールド×348銘柄だがRSS市況の『銘柄数』は各コード/市場で計上する。公式 https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html および https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_08.html 

追加観測で各銘柄のvendor累積代金・累積株数・VWAPの比率を比較し、通貨単位が円か千円かの近似一致を数える。全個票はPC private receiptのみ。ユーザーへの標準出力は集計件数と受領経路のみ。

`runtime/no11_rss_cumulative_va_observability.mjs` は保存された連続RSS観測に対して、(1) ベンダー代金と株数とVWAPの比率から単位候補を検査し、(2) 連続観測の累積代金差分と1分RssChart出来高の差分が矛盾しないかを検査する。判定は『観測した累積カウンタの増分』のみ。

**重要:** RssMarketの売買代金フィールドには専用の取引所更新時刻が保証されず、同時セルのExcel読み取りは非原子的。累積差分=正確な取引所の1分境界のVaとは認定できない。更新ずれ、丸め、単位変換、欠損、複数約定フレームの欠落を実機で確認するまで、元Selectorの`minuteVaSourceCertified`はfalseのまま。確認なしに0補完や単純な価格×数量で埋めない。JPXの元1分Va仕様: https://jpx-jquants.com/ja/spec/eq-bars-minute

**作業優先順位:** 10月26日の348銘柄quote probeは今回の6項目版を一度だけ取得 → chart50の実1M＋継続累積市場情報を同じJSTセッションで観測 → 1M出来高と累積差分を照合してVa供給の可否を判定。以前のUNKNOWN710件の新たな取得・モデルfitは不要。約定・Capital・EXITの実証がないまま27日の本番発注はしない。

PR #592限定。main/Frozen原本/PR #591/現行account Excelは不変。`productionReady=false`; `orderTransmission=false`。
