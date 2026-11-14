# No.1.1：RSS受信足 → 元State9・P1特徴量 → 初回Entry候補

対象：PR #592 / research/no12-prebuy-causal-runtime-20261011。作業基準：2026-10-24。

## 今回つないだ処理

`tools/no11_rss_state9_p1_runner.py` は、既存のChart50取り込みが保存する近似Va付き分足、受信時刻付き元Selector結果、前営業日の価格基準を受け取り、次の順序で処理する。

1. JSTの実受信時刻順に、Selectorイベントと確定1分足を並べる。対象はChart50の選択集合のみ。
2. 元 `normalize80.generate` / `normalize120.regenerate` による前日基準の正規化を再利用する。
3. `load_feature_runtime` がハッシュ確認して読み込む元RC2 `Engine` と `StateFeatureStream` を実行する。State9ラベルを外から作って渡さない。受信済み分足の間に欠けた予定足があれば、元エンジンへ `None` を渡して欠測と区間切断を扱う。
4. 元の価格110数値特徴量とState9・履歴38数値・14カテゴリを結合し、実際のsource_statusを添えて148数値・15カテゴリにする。
5. 既存 `ForwardP1Session` と `FrozenP1Scorer` に渡す。CLIの実モデル経路では元F5の3モデル・前処理・訓練予測分布・保存済みQ70を利用する。初回Entry候補だけをSQLiteへ固定し、注文は送らない。

## 受信順・再起動への対応

- 元RC2の `t/known_at` は予定足の整数クロックであり、PC受信時刻ではない。外側で保持する `knownAtJst` / `receivedAtJst` により、まだ受信していない足・Selector結果を使用しない。カーネルの整数クロックを取引所の正確な到着時刻と説明しない。
- Selectorと同じ時刻に閉じた足が先に届いていても、Selectorを受けた後にその足で初回判定できる。次の1分まで不必要に遅らせない。
- 再起動時は受信済み全prefixを再生する。Watchのrefreshはその時点までに受信したものだけから組み立てる。DBに保存済みの後刻refreshを過去の特徴量へ混ぜない。
- 前日基準の変更、同じ1分足の内容・受信時刻の変更、未来足、二重足、遅れて過去へ差し込まれる足は拒否する。
- 前日OHLCがあるが前日Vaがない場合、State9の価格正規化は行い、前日出来高・代金比較用の入力は欠損のままにする。終値×出来高や0をVaとして作らない。source_statusは `RSS_PROXY_PREVIOUS_OHLC_ONLY_ACTIVITY_MISSING` と記録し、元の欠損処理・未知カテゴリ処理へ渡す。
- 前日基準自体を確認できない銘柄は、理由を集計してP1候補を生成しない。他銘柄の処理を続ける。新しい原本調査や救済学習は行わない。

## 入力と実行

`--minute-feed`：既存 `no11_import_chart50_continuous_snapshot.mjs` の `private-approx-va-*.json`。外側receiptとproxyReceipt、rowsを含む。

`--selector-events`：JSON配列。各要素は `kind=selector`, 実受信の `receivedAtJst`, 元Selector結果の `payload`。元結果のschemaId、Top5・Watch情報、注文OFFフラグは既存P1側で検査する。受信時刻を推測して書かない。

`--previous-context`：`schemaId=ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1`, `sessionDate`, `previousSession`, `orderTransmission=false`, `symbols`（銘柄ごとの前日分足と基準情報）。各銘柄に `previousSession`, `priceBasis=COMPARABLE_RAW`, `corporateActionsCleared`, 当日に基準を利用可能と確認した `knownAtJst`, `rows` を渡す。rowsは `Date, Code, Time, O,H,L,C,Vo` と、実際に保存されている場合のみ `Va`。基準確認フラグを処理を通すためにtrueへ変更しない。

前営業日は既存JPXカレンダーを呼び出して検証する。前日比較用の保存データのない状態を、接続完了と扱わない。

```text
python tools/no11_rss_state9_p1_runner.py \
  --session 2026-10-26 --through <実際の確認対象受信時刻JST> \
  --minute-feed <private-approx-va.json> \
  --selector-events <private-selector-events.json> \
  --previous-context <private-previous-context.json> \
  --runtime-root <既存の検証済みP1推論アセットroot> \
  --private-root <リポジトリ外の保存先>
```

銘柄別特徴量・スコア・候補はprivate SQLiteにのみ保存する。共有用の出力は件数・ハッシュ・未処理理由の集計で、元データや価格を公開しない。

## テストの意味と範囲

新規テストは `test_no11_frozen_p1_rss_state_stream.py`（13項目）と `test_no11_frozen_p1_rss_arrival_order.py`（5項目）。既存Windows/Linux CIのP1テスト探索に含まれる。

実行するのは**元の公開State9・Path・価格特徴量コード**。入力は合成RSS観測、スコアラーは明示したテスト用である。前日Va欠損、欠測足、受信遅延、同時刻Selectorの後着、再起動、遅れて届くrefresh、改変入力拒否、CLI入出力まで検査する。非公開F5モデルの今回の実行数や実RSS受信の成功を、これらのテストから主張しない。

## 未完了の境界

今回の成果は保存済み受信列から初回Entry候補までの実行経路。Excel収集から10時刻のSelector結果・受信時刻・前日基準を自動供給する常駐runnerと、その実機連続運転は別に必要。`Run-No11Chart50ReadOnlyE2E.ps1`を実行しただけでP1まで起動するようには、まだ変更していない。

H2/H3/H5の2026配備、Capital/EXIT、口座・約定・取消・注文管理も今回の完成範囲外。元Frozenのソース・重み、モデル再学習、main、別モデルブランチ、元Excel・注文許可には変更なし。`productionReady=false`、`orderTransmission=false`を維持する。
