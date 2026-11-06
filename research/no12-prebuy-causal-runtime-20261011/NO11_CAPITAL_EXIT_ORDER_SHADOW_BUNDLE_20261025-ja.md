# No.1.1：Capital・元EXIT・約定状態管理を常駐Shadowへ一括接続

2026-10-25 JST / PR #592 / `research/no12-prebuy-causal-runtime-20261011`。
新Selector、再学習、別branch変更、実口座への送信は行わない。

## この変更でつながる処理

既存RSS収集 → 定時Frozen Selector → State9/P1 → 元H235の受信時点R0 → **元Capital V5の配分計算 → Shadow BUY_INTENT → 別イベントの模擬BUY_FILL → 保有 → 元Structural EXIT v3＋SHARP_DROP＋15:20 → Shadow SELL_INTENT → 別イベントの模擬SELL_FILL → 当日新規BUY停止**。

これまでの常駐処理はH235順位保存までだった。本変更では同じ常駐consumerに任意のShadow口座設定を渡すことで、判断後の保有・決済状態まで更新する。独立した検査スクリプトを増やすだけの変更ではない。

## 元EXITの再利用

`tools/no11_original_exit_shadow.py`は以下の原本Git blobを検証して読み込む。

- `research/state9-structural-exit-v3-local-guard-20261003/frozen_v2_lifecycle.py`: `c3a5842bc444f682ce7aa74dc2aaafe3555bb485`
- 同 `local_guard.py`: `9fd6aa0b1fa28c4cc6b286aa2ace3e61c3ae4d2d`

原本クラスの数値判定は変更しない。依存importの名前衝突だけを隔離し、A＝`UP_STRUCTURE_REVERSED`、B＝`UP_STRUCTURE_RETIRED_BY_RANGE`、C＝`LOCAL_UP_STRUCTURE_GUARD_BROKEN`を元コードで計算する。現在バーで確認されたpivotを同じバーのC判定に使わず、欠損・segment切替時のguardリセットも元コードのまま。

元State9の受信済み履歴に、原本が要求する`slot.bar_end`を同じ論理バー時刻から付す。架空のStateを生成しない。実PC時刻に秒・ミリ秒がある模擬fillは、そのfillより前に閉じた足で売却判断しない。SHARP_DROPはfillより後の最初の有効観測を使い、同時刻の元structural判定を優先する。

15:20は価格ファイルの更新を待たず、常駐loopの時刻確認からSELL_INTENTを作る。**意図を出すだけで売れたことにしない。** 後続の観測がなく約定を模擬できなければ、保有と未完了注文が残る。

## 約定・資金・再起動

`tools/no11_shadow_portfolio.py`はSQLiteのWAL/FULL同期・トランザクション・イベントhash chainを使い、以下を一緒に保存する。

- Capitalが決めた数量・資金予約。BUY_INTENTだけでは保有を作らず現金も減らさない。
- 累積約定数量と累積金額。部分約定は増分だけ反映する。
- 取消要求と取消完了を区別する。要求だけで残余予約を戻さない。取消待ち中に到着したfillも捨てない。
- SELL_INTENTだけで現金を増やさず、枠も解放しない。全量売却完了でのみ保有が消える。
- 最初の正数量SELL_FILL（部分を含む）から、当日新規BUY禁止を永続化。残るBUYには取消要求状態を付ける。
- 同一イベント再受信は一度だけ反映。同じIDの内容変更、累積値逆転、別銘柄・売買区分の混入、予約超過、未保有売却は拒否する。
- 不明注文状態は照合待ちを維持。再起動だけで解除しない。
- 個人保有銘柄を除外し、MAX3・注文100株単位・資金上限を元Capitalと状態検査で維持する。

原本Capital V5のslot/allocationは、既存の`no11_h235_capital_v5_shadow.py`経由で実行する。Arrival Tableは既存のSHA256照合を通した原本が必要。現在の口座資金ではなく、明示した**仮想資金**だけを使う。

## 模擬fillの意味

`tools/no11_observed_execution_shadow.py`が、注文意図の生成後に受信した新しい確定足の終値を使う。これは`NEXT_FRESH_RECEIVED_CLOSE_SIMULATION`という**Shadow専用の約定仮定**。BUYは1.0005、SELLは0.9995の係数を適用する。価格が買付予約を超えると、安く約定したふりをせず模擬取消にする。

このfillは楽天の約定でも、原本バックテストの次足始値fillの再現でもない。板・約定可能数量・実手数料・滑りを検証したものではなく、利益や実注文成功を証明しない。模擬取消完了もローカルシミュレータの応答であり、楽天RSSの取消応答ではない。

保有銘柄（最大3）について、既存`ObservedStateStream`による元State9/Pathを増分計算し、EXITへ渡す。受信済み履歴が後から変わった場合は停止する。P1側の既存再生処理・モデル係数・選定時刻は変更しない。

## 同じ一括起動で有効にする

既存bootstrap設定に`shadowAccountConfig`を追加する。H235が必要なので`h235ModelRoot`も必須。設定なしなら従来どおり推論結果保存までで止まる。

以下は**構造の例**。実在するprivateファイルのパスを指定する。100万円はテスト用の例で、ユーザーの実残高ではない。

```json
{
  "schemaId": "ARK_NO11_OBSERVED_SHADOW_ACCOUNT_V1",
  "sessionDate": "2026-10-26",
  "initialCashJpy": "1000000",
  "externalSymbols": [],
  "originalArrivalTable": "C:\\PRIVATE\\original-ARRIVAL_TABLE.json",
  "fillPolicy": "NEXT_FRESH_RECEIVED_CLOSE_SIMULATION",
  "syntheticAccountOnly": true,
  "productionReady": false,
  "orderTransmission": false
}
```

このファイルへの絶対パスをbootstrap設定の`shadowAccountConfig`に書き、既存の`Run-No11ReceivedSessionReadOnly.ps1 -ConfigFile ...`で起動する。Python consumerを直接起動する場合は`--shadow-account-config`を使う。元Excel・RSS注文許可はOFFのまま。

保存先の`inference`に`portfolio-shadow-2026-10-26.sqlite`、`portfolio-latest-report.json`が追加され、`pipeline-latest-report.json`にも`shadowPortfolio`が入る。表示する件数はShadow BUY/SELL意図・保有数。`brokerTransmissions`は0。

同じconsumerのprivate-rootで再起動した場合、台帳の資金・未約定・部分約定・当日BUY停止は復元される。**bootstrapをもう一度新規起動すると従来どおり別の独立runになる。これを実口座の注文復旧と呼ばない。** 既存runを復帰するときは同一private-rootのconsumerを使用する。

## 検証範囲と残件

追加テストは、原本A/B/C・SHARP_DROP・EOD、同バーpivot禁止、segment/欠損、原本Capital→予約、部分BUY/SELL、取消競合、再起動、改変拒否、個人銘柄排除、MAX3、実serviceへのhook、および受信形状データからBUY→保有→EOD SELL→決済までを確認する。

**テストは合成価格・合成口座・テスト用モデルである。実RSSと非公開の元モデルを使った成功結果ではない。** 出荷CIの成否は該当commitのActionsを確認する。

26日の実機Shadowには、当日master・前日context・日足取得原本・元P1/H235モデル・元Arrival Tableの実在するprivate入力が引き続き必要。今回その市場データを取得済みとは扱わない。

27日の実売買については、**実口座残高/保有/注文との照合、楽天RSS発注・取消・部分約定の物理接続、通信断復旧、実機での安全なEXIT**が別途未完了。今回完成させるのは、実注文OFFの統合Shadowと注文状態処理であって、これだけで実発注を許可しない。
