# Phase21 Part1 — Vercel Cloud Persistence

## Goal

Ark Terminalの予測履歴をブラウザ内だけでなく、Vercel API経由のクラウド保存先にも永続化する。

既存のlocalStorage / IndexedDB保存は残し、クラウド未設定・未接続・障害時もPrediction Labを停止しない。

## Data path

```text
Prediction Lab localStorage / IndexedDB
  -> /api/cloud-session
  -> HttpOnly session cookie
  -> /api/cloud-state
  -> REST-compatible KV / Redis
```

## Required Vercel environment variables

Vercel projectにREST対応KV / Redisを接続し、以下を設定する。

```text
ARK_CLOUD_SYNC_SECRET=<16文字以上の十分に長いランダム値>
ARK_KV_REST_API_URL=<REST KV endpoint>
ARK_KV_REST_API_TOKEN=<server-side token>
```

互換用として、次の一般的な環境変数名も読み取れる。

```text
KV_REST_API_URL
KV_REST_API_TOKEN
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
```

Ark Terminal側では`ARK_*`名を推奨する。

環境変数の値はGitHubへコミットしない。

## Activation

1. Vercel projectへREST対応KV / Redisを接続する。
2. 上記3環境変数をProductionへ設定する。
3. Vercelを再デプロイする。
4. 次のページを開く。

```text
https://ark-terminal.vercel.app/predict/cloud-sync.html
```

5. `ARK_CLOUD_SYNC_SECRET`へ設定した同期パスフレーズを入力する。
6. 「接続して同期」を押す。
7. `接続済み`および同期件数が表示されることを確認する。

## Authentication

- 同期パスフレーズはPOST時だけVercelへ送信する。
- localStorage / IndexedDBへ保存しない。
- 認証成功後は署名済みHttpOnly Cookieを使用する。
- Cookieは`SameSite=Strict`。
- Production HTTPSでは`Secure`属性を付ける。
- 有効期限は12時間。
- 15分間に5回失敗すると一時的に接続を拒否する。
- 更新APIは同一オリジンだけ許可する。

## Allowed collections

```text
predictions
prediction_outcomes
paper_orders
paper_positions
paper_account_snapshots
learning_reports
candidate_models
model_versions
forward_test_results
```

Phase21 Part1の画面では、まず`predictions`と`prediction_outcomes`を同期する。

## Explicitly excluded

次の情報はクラウドへ保存しない。

- 楽天証券ログイン情報
- 証券口座番号
- MARKETSPEED II認証情報
- OpenAI API key
- 市場データAPI key
- アクセストークン / リフレッシュトークン
- Cookie / Authorization header
- ブローカー認証情報
- 実口座スナップショット
- 実注文・取消情報

APIはAllow List外のcollectionを拒否し、JSON内の機密項目名も再帰的に検査する。

## Current behavior

- Cloud Syncページを開いて接続すると、同一オリジンのPrediction Labローカル履歴を読み込む。
- `source: live`の予測だけをクラウド同期対象にする。
- 大量のwalk-forwardバックテスト行は同期しない。
- 判定済みレコードは`prediction_outcomes`にも保存する。
- クラウドと端末のレコードをIDでマージする。
- クラウド障害時も端末保存は残る。

## Current limitation

- REST KV自体の作成とVercel環境変数設定は、Vercel管理画面で行う必要がある。
- ブラウザを閉じた状態での定期実行はまだPhase21 Part2以降。
- Prediction Lab実行直後の自動クラウドミラーはPart2で統合する。
- 現時点ではCloud Syncページから初回同期・再同期を行う。

## Safety invariants

```text
brokerWriteAllowed = false
realAccountUploadAllowed = false
liveTradingAllowed = false
```

Cloud Persistenceは学習データの保存機能であり、実口座注文経路ではない。
