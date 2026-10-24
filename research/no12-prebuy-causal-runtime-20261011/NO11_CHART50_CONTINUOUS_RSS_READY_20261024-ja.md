# No.1.1 — 10/26向けChart50連続RSS実機テスト前倒し (2026-10-24)

**目的**: 2026-10-26のRSS実機確認までに、Selectorに必要な「約47銘柄の1分足 + 累積RSS出来高/売買代金/VWAPの連続観測」と「観測Vaの代替変換」を実装済みにしておく。新学習や710 UNKNOWN調査はせず、元Frozen Ridge・10回Top5・P1/H235/Capital/EXIT・注文設定を変更しない。

## Windows PCで実行するもの

`windows/Probe-No11Chart50ContinuousReadOnly.ps1`は、保存済み2026-10-23日足4,328銘柄からG1 PASS348→Chart50 allocationをローカル生成し、既存のArk元2 Excel Workbookへ書かずに、無保存の一時WorkbookでRSSを読み取る。

- 実行日は現物営業日であることを検証。2026-10-26の前営業日は2026-10-23。2026-10-27以降、古い日足maskは拒否する。
- RSSアカウントUI2が停止し、Ark元2 Workbookと専用Excel windowの一意性を確認する。元ブックは公式式の数だけを閲覧し、口座のセル値にはアクセスしない。
- `RssChart(…,'1M',120)`（1銘柄1関数）をChart50計画の全監視銘柄分、外部の既存Chart使用関数数と合算し50以内に留める。保有・Watchなど計画で固定された銘柄のチャート枠は保護するが、これ自体はまだ保有/EXIT取引の実行ではない。
- Selectorへ渡すPASSサブセットの各銘柄に、RssMarket の当日日付・累積出来高・累積売買代金・VWAPを4フィールド読み取る。市況枠は銘柄単位（列数ではない）。
- 毎分の8秒付近で、Marketの一括読取→Chart50シートの1Mデータ取得を行う（初期4回）。終値確定前の1分足は除外。複数Workbookで50上限を回避したものとはみなさない。結果はPrivate hashed immutable `snapshot-<sha256>.json` のみ、標準出力は件数とprivateパスだけ。
- 追加の`--pins-file`（PowerShell側 `-PinsFile`）にはアクティブWatch/保有/発注待ち/既存Chartを含むprivate契約を指定可能。指定なしは**口座状態を確認していないREAD-ONLY容量試験**であり、自動売買可能状態へ昇格しない。

## Node側取り込み

`tools/no11_import_chart50_continuous_snapshot.mjs`は保存済みSnapshotだけをSHA256名一致で読み、旧Snapshotの閉じた1Mデータと、各SnapshotのRSS cumulative market観測を as-of で結ぶ。

`runtime/no11_rss_vendor_va_shadow_adapter.mjs`が重複・未来データ・時計ずれ・異なる出来高・累積カウンタ逆転を拒否した場合は、その1分足は生成しない。問題なく受信できた分についてのみ近似Vaをprivate JSONに保存。26日にJ-Quants Vaとの過去値一致を検証するためではなく、LIVE場中で必要な入力が安定供給できるかだけを観測する。

**絶対に本番許可と混同しないこと**: RSSから得た近似Vaは取引所の確定1分Vaではなく、元Frozenと入力の分布が異なる。得られた観測値が正しいか、データ欠損を正しく止めるかだけをまず確認する。またEntry P1/H235の2026モデル割当、Capital/EXITの連携、実RSS注文・部分約定・取消・残高照合も別の未完成要件で、27日売買開始を保証しない。`productionReady=false`, `orderTransmission=false`。

## 計画段階での注意

Excelを用いない合成テストはWindows/Ubuntuの既存CIに追加。実Workbookは実機がある10/26にしか確認できない。CI PASSをライブ実機の結果と混同しない。

素材/Privateアカウント情報はGitHubに保存しない。
