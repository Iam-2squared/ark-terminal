# OpenAI AI Analysis setup

Prediction Labの通常分析はブラウザ内の決定論的ロジックで計算し、OpenAIには計算済み結果だけを送ります。APIキーはブラウザへ配信されません。

## Vercel environment variables

- `OPENAI_API_KEY`（必須）
- `OPENAI_MODEL`（任意、未設定時は `gpt-5-mini`）

VercelのProject Settings → Environment Variablesへ登録し、再デプロイしてください。

## Endpoint

`POST /api/ai-analysis`

同一IPからの連続実行は20秒間隔に制限します。入力は60KBまで、OpenAIへの通信は30秒でタイムアウトします。

## Output

- 総合評価
- 強気・中立・弱気のスタンス
- 買い要因
- 売り要因
- リスク
- 注目ポイント
- 市場全体との関係
- 信頼度の説明

AIは数値の計算元ではありません。RSI、MACD、ADX、ATR、VWAPなどは既存ロジックで計算し、AIはその結果を整理・説明します。
