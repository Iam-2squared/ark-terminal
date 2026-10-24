# No.1.2 — 1分足だけから5分足を派生する容量削減案（2026-10-11）

当日1分足の確定5本を厳密に合成し、5分足OHLCVを再構成する**READ ONLY・synthetic source adapter**を追加。

- 楽天MarketSpeed II公式制約: `RssChart`最大50関数。1M/5Mを別関数で同時取得するなら1銘柄で2関数となり、他の使用が0でも最大25銘柄しか同時確保できない。
- 1Mだけを取得し5Mを計算できれば理論上1銘柄1チャート関数にできる。ただし**取引所セッション区間、ベンダー時刻ラベル、5本完全性、出来高合算、遅延とSource真正性の確認が必要**。
- モジュール `runtime/no12_1m_to_5m_causal.mjs` は、日付/分の等間隔連続5本が揃った場合に限り機械的にOHLCVを合成する。欠損、未確定足、昼休み、整合しないラベルをつないだ架空の足を作らない。
- 履歴が不完全、source不鮮明、同日latest足がない場合は`COMPLETE_CURRENT_5M_UNAVAILABLE`／入力契約エラーとして扱う。
- **正式なRssChart 5Mの値と合致した証明ではない**。現物市場で同一シンボル・同一時間帯の5M公式RSS足と、集計1M足の一致を検証してから候補にできる。会社発表・ギャップ・板寄せを勝手に補完しない。
- Marketwideスクリーナーの代替ではなく、上位候補のチャート枠を効率化する研究用。No.1.1のFrozen Selector/FirstEntry/State9/EXIT／モデル閾値に影響しない。
- TradingView scannerの自動取得・自動売買への転用は利用規約の制限により行わない。別途利用権限のある全市場データ源、または市場RSS巡回の実機スループット検証が必要。
- 実注文／取消／Excelへの注文関数書込／本番許可は0。 `productionReady=false`、`orderTransmission=false`。
