# MARKETSPEED II RSS Bridge

Windows上でMARKETSPEED IIとExcelのRSSアドインを起動・接続した状態で使用する、Ark Terminal向けの読み取り専用ローカルAPIです。

## 安全方針

- 実口座への注文作成なし
- 実口座への注文送信なし
- 実注文の取消なし
- 口座番号をブラウザへ送信しない
- ログインID・パスワード・APIキーをExcelへ保存しない
- 実口座APIはGETのみ
- ローカルBridgeは`127.0.0.1`だけで待ち受ける

## データ経路

```text
MARKETSPEED II
  -> Excel RSS
  -> tools/rss_bridge.py
  -> http://127.0.0.1:8000
  -> Ark Terminal Home 実口座カード
```

## セットアップ

```powershell
py -m pip install -r tools/requirements-rss.txt
```

MARKETSPEED II、Excel、RSSアドインを起動し、対象ブックをExcelのアクティブブックにしてください。

## 市場データシート

既存の`Sheet1`に次の順で株価セルを配置します。

- A1: 4755.T
- A2: 9432.T
- A3: 7203.T
- A4: 9984.T

## 実口座サマリーシート

`ArkAccount`という名前のシートを作り、既存のRSS出力または参照式を次のセルへ配置します。

| セル | 内容 | 必須 |
|---|---|---|
| B2 | 現金残高 | いずれか1つ以上 |
| B3 | 買付可能額 | 任意 |
| B4 | 保有時価 | いずれか1つ以上 |
| B5 | 総資産 | いずれか1つ以上 |
| B6 | 実現損益 | 任意 |
| B7 | 評価損益 | 任意 |
| B8 | 通貨（通常`JPY`） | 任意 |
| B9 | 更新日時 | 任意 |
| B10 | 口座種別 | 任意 |

口座番号、ログインID、パスワードはこのシートへ入れません。

## 実保有銘柄シート

`ArkPositions`という名前のシートを作り、1行目を見出し、2行目以降へ保有銘柄を連続して配置します。

| 列 | 内容 |
|---|---|
| A | 銘柄コード（例: `4755`または`4755.T`） |
| B | 銘柄名 |
| C | 保有数量 |
| D | 売却可能数量 |
| E | 平均取得価額 |
| F | 現在値 |
| G | 保有時価 |
| H | 評価損益 |
| I | 評価損益率 |
| J | 通貨 |
| K | 口座種別 |
| L | 更新日時 |

A列が空になった行で読み取りを終了します。数量が0の行は無視されます。

## 起動

リポジトリのルートで実行します。

```powershell
py -m uvicorn tools.rss_bridge:app --host 127.0.0.1 --port 8000
```

## 確認URL

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/price/4755.T
- http://127.0.0.1:8000/broker/connection
- http://127.0.0.1:8000/broker/account
- http://127.0.0.1:8000/broker/positions
- http://127.0.0.1:8000/broker/snapshot

`/broker/connection`が`connected: true`かつ`authenticated: true`になれば、Homeの実口座カードがローカルBridgeを優先して読み取ります。

## Ark Terminalの接続先

標準接続先は次です。

```text
http://127.0.0.1:8000/broker
```

ポートを変更した場合は、ブラウザの開発者コンソールで次を一度実行します。

```javascript
localStorage.setItem(
  "arkRealAccountBridgeUrl",
  "http://127.0.0.1:任意のポート/broker",
);
```

元に戻す場合は次を実行します。

```javascript
localStorage.removeItem("arkRealAccountBridgeUrl");
```

## CORS

標準で次のArk Terminal originだけを許可します。

- http://localhost:5500
- http://127.0.0.1:5500
- https://ark-terminal.vercel.app

別の開発originを追加する場合だけ、起動前に環境変数を指定します。

```powershell
$env:ARK_RSS_ALLOWED_ORIGINS="http://localhost:3000"
```

ワイルドカード`*`は使用しません。

## 注意

このコードはExcelに既に表示されている値を読み取ります。楽天証券側の実口座情報をExcelへ出すRSS関数や既存シート構成そのものは、使用中のMARKETSPEED II RSSブックで確認が必要です。Bridgeは存在しない値を推測したり、`0`で偽装したりしません。
