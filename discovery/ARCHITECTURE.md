# AI Stock Screener

## 役割

- `index.html` / `style.css`: 独立したDiscovery画面
- `script.js`: 画面状態とイベントの調整
- `data.js`: スナップショット読込と少数銘柄のライブ更新
- `engine.js`: Prediction Lab共通ロジックを使った1銘柄の採点
- `filtering.js`: 価格・予算・市場・テーマなどの純粋な絞り込み
- `storage.js`: ウォッチリストと通知条件のローカル保存
- `alerts.js`: 通知条件判定とブラウザ通知
- `ui.js`: ランキング描画

## データフロー

1. `scripts/fetch_jpx_universe.py` がJPX公式の月次一覧を取得する。
2. `scripts/screener-progress.mjs` が銘柄一覧を小さなバッチへ分割し、
   `data/screener-progress.json` に次の開始位置を保存する。
3. `scripts/update_screener.mjs` が今回のバッチだけ各銘柄の2年履歴を取得する。
4. Prediction Labと同じデータ品質検証を通過した銘柄だけを採点する。
5. `data/screener-snapshot.json` を静的配信し、画面を高速表示する。
6. 画面からのライブ更新は最大24銘柄に限定し、サーバーレス制限を避ける。
7. 定期更新は前回バッチの続きから再開し、全銘柄到達後に次サイクルへ移る。
8. 更新結果は `automation/screener-data` ブランチへ保存し、mainへ直接
   pushせずPull Requestで反映する。

## 拡張点

- 時価総額は `marketCap` を返す企業情報プロバイダーへ差し替え可能。
- テーマ分類は `screener-theme-overrides.json` または将来の企業説明AIで拡張可能。
- 常時通知は `alerts.js` の判定結果をWeb Push送信アダプターへ渡せる。
- Yahoo Finance以外の正規データ契約へは、履歴プロバイダー部分だけを差し替える。
- `SCREENER_BATCH_SIZE` で1回の処理件数を調整できる。標準は240銘柄。

## 更新の性質

- ライブボタンは表示中の候補を少数だけ再計算する。
- 全銘柄更新はGitHub Actionsが分割して行い、途中停止しても次回再開する。
- 標準スケジュールでは1営業日6バッチのため、約3,800銘柄の1サイクルは
  およそ3営業日。これはリアルタイム全市場分析ではない。

## 重要

スコア、信頼度、期待変動幅は利益や上昇確率を保証しない。取得不能・異常・
調整後終値不備のデータはランキングから除外する。
