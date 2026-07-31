# Ark Terminal スマホ対応パッチ

## 使い方

1. ZIPを展開します。
2. 展開した中身をArk Terminalプロジェクトの一番上のフォルダへコピーします。
3. 同名ファイルは「置き換える」を選びます。
4. VS Codeのターミナルでテストします。

```powershell
node --test tests/mobile-responsive.test.mjs predict/tests/*.test.mjs
```

5. ローカル確認を始めます。

```powershell
npx.cmd vercel dev
```

6. Chromeで以下を開き、開発者ツールのスマホ表示でも確認します。

```text
http://localhost:3000/
http://localhost:3000/tasks/
http://localhost:3000/stocks/
http://localhost:3000/stocks/detail/
http://localhost:3000/news/
http://localhost:3000/predict/
http://localhost:3000/predict/performance.html
http://localhost:3000/discovery/
```

## GitHubへ保存する場合

このパッチは`main`へ直接入れず、新しいブランチで確認してください。

```powershell
git switch -c agent/mobile-responsive
git add mobile.css tests/mobile-responsive.test.mjs MOBILE_RESPONSIVE_INSTALL.md index.html tasks/index.html stocks/index.html stocks/detail/index.html news/index.html predict/index.html predict/performance.html discovery/index.html service-worker.js
git commit -m "Make Ark Terminal responsive on mobile"
git push -u origin agent/mobile-responsive
```

その後、GitHubで`agent/mobile-responsive`から`main`へのPull Requestを作り、
Vercel Previewをスマホで確認してからマージします。

## 主な変更

- Home、Tasks、Stocks、Stock Detail、News、Prediction Lab、AI Performance、AI Stock Screenerへ共通スマホCSSを追加
- フォームを狭い画面で1列化
- ボタンやリンクのタップ領域を44px以上へ調整
- TradingViewチャートのスマホ向け高さを調整
- AI Performanceの大きな表を横スクロール対応
- Screenerランキングをスマホ用カード表示
- 画面横方向のはみ出しを防止
- Service Workerのキャッシュを`v6`へ更新
