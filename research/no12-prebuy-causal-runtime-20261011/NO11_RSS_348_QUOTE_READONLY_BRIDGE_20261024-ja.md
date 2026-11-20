# No.1.1 の前段：348銘柄だけをRSS同時監視する実機read-only接続

2026-10-24 JST。ユーザー要求「新しいモデルを作らず、710件の詳細調査を止めて既存No.1.1を最速で動かす」を優先する。

## 入力

- 2026-10-23の private RSS日足保存4,328件（元保存のimmutable SHAとコードidentityを維持）から、既存`no11_export_observed_pass_watch_mask.mjs`が348件のPASS identityだけを書き出す。
- UNKNOWN710件（形式不備489/取得不可221）は再取得・再判定しない。除外をBUY直前に必ず再確認し、BUYを許可したことにはしない。
- 古いasOfの日足maskは拒否する。JPX現物営業日calendarで当日判断より前の最後の確定セッションを確認する。市場時間外・休日はread-only試験対象外。

## 追加した実機入力プローブ

`windows/Probe-No11ObservedPassRssMarketReadOnly.ps1` は、ユーザーPCでのみ動く一回の観測スクリプト。既存の可視 Ark Excel と元2冊が存在し、Ark UIが停止していることを確認してから、無保存の別Workbookの1枚のWorksheetへ以下だけを設定する。

- `=RssMarket("CODE.T","現在日付")`
- `=RssMarket("CODE.T","現在値")`
- `=RssMarket("CODE.T","現在値詳細時刻")`

350未満の銘柄は1銘柄につき3関数で観測、別のChart関数は消費しない。RSS市況上限500銘柄は既存Workbookの各`RssMarket`式を1銘柄として過大側に数えた予算と照合する。別WorkbookでRSS制限を迂回した扱いにしない。`WaitSeconds`後の単一bulk readだけで、同時配信品質やタイミングを自動認証しない。

共有できるのは集計件数とread-only出力状態。銘柄/価格の個別内容はPRIVATE保存。元Excel2冊へ書込・Save・Closeしない。実注文式/注文トリガー/UI変更は0。Excel COM拒否時は安全停止。コードの`OfflineSelfTest`とWindows CIで構文と式検査を行う。

## 次の本実装

348銘柄の`RssMarket`同時観測の実測が得られれば、10時刻のSelector入力に必要な1分OHLCVをChart最大50枠に切り分ける。しかし元Selectorの横断母集団で計算するbreadth/流動性三分位および真の分Vaは、このquote probeでは解決しない。上昇348銘柄だけに母集団を狭めると元Frozen全市場cross-sectionとは異なる戦略になるため、その差を未検証のまま『元モデルの成績を保持』とは主張しない。

このプローブは実RSSの一部入力接続であり、元Selectorの候補ランキング・P1・State9・H235・Capital・EXIT・RSS発注・終日Shadowを動かすものではない。`productionReady=false`、`orderTransmission=false`。

開場中に一度だけ実機試験すれば十分。大規模履歴の取り直しやP1モデルの再検証は要求しない。2026-10-23の日足maskを使える最初の現物営業日は10月26日（月）。以降は前営業日asOfを更新しない限りFail closed。
