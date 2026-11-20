# No.1.1 統合Shadow：Capital境界・時刻・不明注文の修正

2026-10-25 JST。対象は既存 PR #592 / `research/no12-prebuy-causal-runtime-20261011`。
Frozen原本・モデル係数・main・別モデルbranchは変更しない。実注文送信は追加しない。

## 前回停止した箇所

`832b4dbad49cabec6c27f2c206605b85120228db`の統合CIで、受信データ形状からCapitalへ進む6テストが`NO11_H235_CAPITAL_FROZEN_V5_REJECTED`になっていた。
原本`allocation.py`は価格を`Decimal(raw_reference)`として扱い、原本bridgeは`Decimal(str(raw_reference))`でdebitを照合する。101.7等のfloatでは両者が一致しない。

修正は`no11_h235_capital_v5_shadow.py`の境界で、検証済み数値を`str(p)`として渡すことだけ。原本配分式は変更せず、推定tickへの丸めも行わない。入力R0そのものは書き換えない。元のfloatを直接渡した場合の失敗も回帰テストで再現する。

## まとめて修正した実行境界

1. **15:20の未約定BUY**：時刻確認から取消要求へ移す。要求だけで残余予約は解放しない。15:20後の新しい価格で過去のBUYを新規約定させない。
2. **遅延受信**：模擬fillに使う足は、受信時刻だけでなく足の確定時刻も注文意図より後でなければならない。遅れて届いた注文前の終値を使わない。
3. **改変入力の処理順**：H235 private結果のSHA256と、すでに消費した保有銘柄の履歴をfill・markより前に照合する。履歴削除も拒否する。これは全tickの単一トランザクション化を意味しない。
4. **UNKNOWNの保持**：EXIT時・最初のSELL fill時のBUY取消要求でUNKNOWNを上書きしない。取消要求後にUNKNOWNが届いた場合もUNKNOWNを優先する。ローカルの取消要求だけでは解消できない。
5. **部分約定＋UNKNOWN**：確定済み100株のEXITと、不明な残注文を別々に保持する。確定済み数量が売れても、不明なBUY残注文の予約・照合待ちは残す。再起動でも解除しない。

## 検証

追加テストは次の2ファイル。価格・資金・モデルファイルはすべて合成である。

- `tests/test_no11_frozen_p1_execution_regressions.py`：11テスト。小数価格、元エラー再現、EOD、遅延足、改変・削除の更新前拒否。
- `tests/test_no11_frozen_p1_execution_unknown.py`：5テスト。取消競合、部分UNKNOWN、確定済み数量の売却、再起動、照合停止の保持。

実行対象は既存CIの以下のコマンドに自動で含まれる。

```text
python -B -m unittest discover -s research/no12-prebuy-causal-runtime-20261011/tests -p 'test_no11_frozen_p1_*.py' -v
node --test research/no12-prebuy-causal-runtime-20261011/tests/*.test.mjs
```

小数・EOD・受信境界の修正commit `cbf49ea79d72448ad2c40de3dd9516596a518576`については、Actions run `40160838035`のWindows・Ubuntu両jobがsuccessになったことを確認した。UNKNOWN修正を含む最終commitの結果は、そのcommitに紐づくActionsとPRコメントを参照する。過去commitの成功を最終commitの成功へ流用しない。

## 到達範囲を混同しない

現在の約定は`NEXT_FRESH_RECEIVED_CLOSE_SIMULATION`であり、証券会社の実約定ではない。実口座照合、楽天RSS発注・取消・約定応答、通信断復旧、実機でのEXIT成立は今回のCIでは確認していない。

同じconsumer private-rootのSQLiteは再利用するが、bootstrapの新規起動は別runを作る既存仕様である。新しい空台帳を実口座復旧の代わりにしてはいけない。保有履歴のこの層でのチェックは同一processの消費済みprefixを対象とし、service側のP1受信原本チェックとは別である。

`productionReady=false`、`orderTransmission=false`、実broker送信0を維持する。テスト成功や予定日だけでは実売買を有効にしない。
