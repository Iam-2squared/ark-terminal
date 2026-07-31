# AI Stock Screener 導入メモ

## ブランチ

`agent/ai-stock-screener-batches`

mainへ直接変更せず、このブランチからPull Requestを作成します。

## 確認URL

- Discovery: `http://localhost:3000/discovery/index.html`
- 個別分析: `http://localhost:3000/predict/index.html`
- AI成績: `http://localhost:3000/predict/performance.html`

Live Server（5500番）でも画面は開けますが、APIを含む確認にはVercel開発
サーバーを使います。

```powershell
npx.cmd vercel dev
```

## テスト

リポジトリ直下で実行します。

```powershell
node --test predict/tests/*.test.mjs discovery/tests/*.test.mjs
```

## 全市場データの初回作成

Pull Requestをmainへ反映したあと、GitHubの
`Actions > Update AI Stock Screener > Run workflow` を開きます。

1. 最初は `batch_size` を `30` にして動作確認する。
2. 作成された `automation/screener-data` のPull Requestを確認する。
3. 問題がなければ `batch_size` を `240` にして次のバッチを処理する。
4. 以降は平日に1日6回、自動で前回位置から再開する。
5. データ更新Pull Requestを確認してから反映する。

定期処理もmainへ直接pushせず、`automation/screener-data` ブランチへ
保存してPull Requestを作成します。

`reset_progress` はJPX一覧を先頭から再処理したい場合だけ有効にします。
通常はオフのままです。画面の「定期更新サイクル」で全銘柄中どこまで
更新したか確認できます。

## データ上の注意

- JPX公式一覧は前月末時点の月次更新。
- 標準設定の全銘柄1サイクルは約3営業日で、全銘柄同時のリアルタイム値ではない。
- 株価履歴取得先の制限により、一部銘柄は取得失敗する場合がある。
- データ品質ゲートで停止した銘柄にはAIスコアを付けない。
- 時価総額は履歴提供元に値がある場合だけ表示し、推測値は使わない。
- テーマ分類は `data/screener-theme-overrides.json` で追加できる。
- ブラウザ通知はページ表示・更新時の判定。常時通知には将来Web Push
  バックエンドが必要。
