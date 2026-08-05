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

## 実保有銘柄シート（公式RSS関数）

`ArkPositions`という名前のシートを作ります。

1. `マーケットスピード II`タブを開く
2. `注文約定`を選ぶ
3. 関数指定で`保有銘柄一覧（RssPositionList）`を選ぶ
4. 銘柄コードは空欄にする（全保有銘柄）
5. 口座区分は`全て`を選ぶ
6. 表示開始セルを`A1`にして登録する

MARKETSPEED II RSSは次の形式で展開します。

```text
1行目: RssPositionList関数
2行目: 取得項目ヘッダー
3行目以降: 実保有銘柄
```

Bridgeは公式の戻り値から次を読み取ります。

- 銘柄コード
- 銘柄名称
- 口座区分
- 保有数量
- 発注数量
- 平均取得価額
- 時価
- 時価評価額
- 評価損益額
- 評価損益率

`RssMarket`は市況情報用であり、実口座の保有数量や平均取得価額は返しません。

## 現物買付可能額シート（公式RSS関数）

`ArkAccount`という名前のシートを作ります。

1. `マーケットスピード II`タブを開く
2. `注文約定`を選ぶ
3. 関数指定で`余力・保証金率（RssCapacityList）`を選ぶ
4. 表示開始セルを`A1`にして登録する

Bridgeは`現物買付可能額`を読み取ります。

公式RSS関数では、現金残高と総資産そのものは返されません。そのためHomeでは次の扱いになります。

- 現物買付可能額: `RssCapacityList`から表示
- 保有時価: `RssPositionList`の時価評価額を合計
- 評価損益: `RssPositionList`の評価損益額を合計
- 総資産: 公式データがないため`--`
- 現金残高: 公式データがないため表示対象外

買付可能額と現金残高は同じとは限らないため、Bridgeは両者を同一値として偽装しません。

## 旧シート形式との互換性

以前の正規化済みレイアウトも互換用として残しています。ただし、新規設定では公式の`RssPositionList`と`RssCapacityList`を使用してください。

## 起動

リポジトリのルートで実行します。

```powershell
py -m uvicorn tools.rss_bridge:app --host 127.0.0.1 --port 8000 --reload
```

## 確認URL

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/price/4755.T
- http://127.0.0.1:8000/broker/connection
- http://127.0.0.1:8000/broker/account
- http://127.0.0.1:8000/broker/positions
- http://127.0.0.1:8000/broker/snapshot

`/broker/connection`が`connected: true`かつ`authenticated: true`になり、`/broker/snapshot`の`sourceMode`が`marketspeed-native-rss`なら、公式RSS関数の出力を読み取れています。

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

- 注文関数は使用しません
- `RssStockOrder`、`RssModifyOrder`、`RssCancelOrder`などはBridgeから呼びません
- `発注不可`のままで問題ありません
- Bridgeは存在しない値を推測したり、`0`で偽装したりしません
