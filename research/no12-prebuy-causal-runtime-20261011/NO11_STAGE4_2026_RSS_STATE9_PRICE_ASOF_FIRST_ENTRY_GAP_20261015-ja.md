# Ark No.1.1 Stage 4: 2026年RSS State9 → First Entry 必須入力照合（研究・発注OFF）

## 入力の実測結果と固定条件

2026-10-15受領のPC非公開レポート `no11-2026-rc2-sparse-research-7e563a16a33064a3.json` は、原取得順の先頭950銘柄のうち、元Frozen State9 RC2の実データ技術リプレイ条件を満たす **244銘柄を全件実行**した証跡である。

- オリジナルRC2候補/独立2エンジン一致：79,788/79,788 tick、不一致0。
- 保存1Mデータ受理：46,571 tick、欠損に対して元エンジンへ `None` を渡した：33,217 tick。
- 当日Current Primaryが実際に観測された：25,330 tick。State9 Primaryが常に観測されたわけではない。
- リプレイ未完了：0/244銘柄。全327×2営業日完全ペアの追加再チェック：4銘柄。
- Original RSS 1M labelの区間開始時刻解釈、実際のMarketSpeed II到着時刻、元J-Quants情報源・価格decimal token一致はすべて未認証。

公開側には集計のみ `NO11_2026_RSS_STAGE3_ORIGINAL_RC2_FIRST950_ALL244_20261015.json` を記録。**価格原本、銘柄ごとのState9時系列、元研究モデルは公開しない。**

## 今回作ったStage 4ブリッジ

`tools/no11_2026_state9_first_entry_source_join.py` は、ユーザーPC内にすでに保存された以下の4件だけを検証・消費する。

1. 元State9技術リプレイの244銘柄集計レポート。SHA256ファイル名接頭16桁に一致・内容のサンプル数・フラグ・時系列分母を再確認。
2. 元RC2 2エンジン一致時系列のprivate `no11-2026-state9-asof-research-10e44a4bb66bef29.jsonl.gz` SHA256 `10e44a4bb66bef293637651dd19daefc711a460037e0ec05b994eae1a7be5723`。244×327=79,788行を再検証。銘柄は元4,327原リスト（SHA固定）の先頭950内、厳密に増加順。各銘柄が全327tickを持ち、未観測のRC2 Primaryを「観測済み」と数えない。
3. 価格の観測のみの元評価集計レポート SHA256 `380616e9c2d05eb481b5ed160e35b92365822d770e23f9ed80d7295ac883c5e4`。
4. 価格側のprivate `no11-2026-observed-asof-72422775d56f4502.jsonl.gz` SHA256 `72422775d56f450230a8c7c91d6e8ed62fac8e0d66b9aef57c6f16e696d5c851`。8営業日59,712行、10月13日の7,539行を元の時間順序・5M成約後の時刻・5分以内という研究用前提で検証。

一致対象は **2026-10-13の固定10判断時刻×244銘柄＝2,440スナップショット**。各時刻の直前1分ラベル（09:30なら09:29）のRC2ステータスから、元RC2のCurrent Stateが観測されたか検査。別途、閉じた研究用完全5本の5分足による基準価格があるか検査。価格値とState9 Primaryの行単位情報はprivate GZIPにのみ出力する。

元Frozenの新規Entry除外規則 `PULLBACK`, `SHARP_DROP` を個別に集計する。完全なsourceしかカウントせず、欠損/未観測を推測で埋めない。**First EntryのP1/Q70スコアや閾値、BUY_INTENT、H2/H3/H5の2026予測は生成しない。**

## 合格しても何が足りないか

元First Entry V2 (`research/persistent-watchlist-uptrend-first-entry-20261003-v2/first_entry.py`) は、Selectorで作られたウォッチキーと起動時刻、その時点のP1特徴量・モデル推論スコア・外側訓練foldの閾値を必要とする。State9 Primaryと価格が同じ時刻に観測されても、それだけではFirst Entryにはならない。

特に元Selectorのmaster（日足・普通株・市場区分）、前日調整済み価格・コーポレートアクション・分足売買代金Va・セクター情報は過去のRSS 1分足アーカイブだけでは復元できない。**欠測の市場区分/売買代金を0や推測値で置き換えて、Frozen Selectorを実行したと主張しない。**

このStage 4のレポートは `nativeFirstEntryExecuted=false`, `frozenSelectorWatchEventsAvailable=false`, `originalFirstEntryP1Q70FeatureInputsAvailable=false`, `productionReady=false`, `orderTransmission=false` を必ず保持する。

## 進行と昇格判定

- 2025 H2/H3/H5研究モデルは「仮完成」。新フィット・元24モデル置換・再採用は今回のスコープ外。
- まずStage 4をユーザーPC保存原本で実行し、価格とState9が同時に観測された件数を確定。
- 次に元SelectorとFirst Entryに不足する入力を元保存済み原本から**真正に**収集可能か、ファイル証明・時刻可用性まで照合。足りないならLive Shadow入力を新たに将来日付で記録する工程を別立てにする。
- native E2E/ブローカー受信時刻・注文約定整合・ライブ移行は未認証。注文実行OFF、Frozen No.1.1 / PR #591 / main 不変。

**Stage 4はFirst Entryの「時刻別入力カバレッジと不可用理由」の研究接続であって、First Entryモデルの完成・注文認証ではない。**
