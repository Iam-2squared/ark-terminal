# AI Stock Screener 自動反映

GitHub Actions は `automation/screener-data` ブランチへ最新の銘柄一覧・スナップショット・進捗を保存します。

本番の Discovery 画面は Vercel の `/api/screener-data` を経由して、このデータ専用ブランチを直接読み込みます。データ専用ブランチの取得に失敗した場合だけ `main` のデータへフォールバックします。

このため、定期更新ごとのデータ更新 Pull Request と手動マージは不要です。`main` へ自動 push は行いません。

## 定期実行

現在の cron は平日、日本時間のおおむね 9:15 / 11:15 / 13:15 / 15:15 / 17:15 / 19:15 です。GitHub Actions の都合で数分遅れる場合があります。

## 反映までの時間

Vercel Edge と GitHub Raw のキャッシュを考慮し、Actions 完了後おおむね 3〜5 分以内に本番表示へ反映されます。
